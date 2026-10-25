#!/usr/bin/env bash
# Rebuilds every number, table and figure of the paper from the frozen inputs
# in testdata/frozen/, without network access, except for the optional steps.
#
#   scripts/eval/run_all.sh            # offline: unit tests, evaluation, tables and figures
#   scripts/eval/run_all.sh --refit    # also re-fits the iteration-2 weights (must equal the code)
#   scripts/eval/run_all.sh --live     # also the interception test and latency benchmark (network)
#
# Output: paper/data/ (per-package CSVs, calibration), paper/tables/,
# paper/figures/, paper/numbers_v3.json. How the frozen inputs were fetched is
# described in scripts/eval/README.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

REFIT=0; LIVE=0
for a in "$@"; do
  case "$a" in
    --refit) REFIT=1 ;;
    --live)  LIVE=1 ;;
    *) echo "unknown argument: $a" >&2; exit 2 ;;
  esac
done

F=testdata/frozen
D=paper/data
mkdir -p "$D" paper/tables paper/figures

VENV="${PIPGUARD_ANALYSIS_VENV:-$HOME/.cache/pipguard-analysis-venv}"
if [ ! -x "$VENV/bin/python" ]; then
  echo "== creating the analysis venv in $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r scripts/eval/requirements.txt
fi
PY="$VENV/bin/python"

echo "== unit tests"
go vet ./...
go test ./... 2>&1 | tee "$D/go_test.txt"
(cd scripts/eval && python3 -m unittest -q test_pypi_history 2>&1) | tee -a "$D/go_test.txt"

echo "== build"
go build -ldflags="-s -w" -o build/pipguard .
go build -o build/evalset ./cmd/evalset

echo "== frozen inputs -> metadata per scenario"
python3 scripts/eval/build_sets.py meta | tee "$D/build_meta.txt"

HALL="$F/meta_hallucinated_live.jsonl"
POS_HALL=""
if [ -f "$HALL" ]; then
  POS_HALL="$HALL,"
else
  echo "   (note: $HALL is missing; the hallucinated-name group is skipped; this file is deliberately not shared)"
fi
EST="$F/meta_established.jsonl"
EV=(./build/evalset -popular-v1 assets/popular.txt -popular-v2 assets/popular_v2.txt -redact positive_reproduced)

echo "== scenario first (primary) + I-05 grid"
"${EV[@]}" -positive-meta "${POS_HALL}$F/meta_malicious_first.jsonl" \
  -negative-meta "$EST,$F/meta_benign_new_first.jsonl" \
  -out "$D/results_first.csv" -sim-grid "$D/sim_grid.csv" > "$D/evalset_first.txt"
echo "== scenario last"
"${EV[@]}" -positive-meta "$F/meta_malicious_last.jsonl" \
  -negative-meta "$EST,$F/meta_benign_new_last.jsonl" \
  -out "$D/results_last.csv" > "$D/evalset_last.txt"
echo "== scenario reported"
"${EV[@]}" -positive-meta "$F/meta_malicious_reported.jsonl" \
  -negative-meta "$EST" \
  -out "$D/results_reported.csv" > "$D/evalset_reported.txt"
if [ -f "$F/meta_prospective_first.jsonl" ]; then
  echo "== prospective hold-out (reported after the design freeze)"
  "${EV[@]}" -positive-meta "$F/meta_prospective_first.jsonl" \
    -out "$D/results_prospective.csv" > "$D/evalset_prospective.txt"
fi

if [ "$REFIT" = 1 ]; then
  echo "== re-fit: iteration 2-early (dev, rejected) and iteration 2 (val)"
  "$PY" scripts/eval/fit_weights.py --method initial --results "$D/results_first.csv" --grid "$D/sim_grid.csv" \
    --out "$D/calibration_initial.json"
  "$PY" scripts/eval/fit_weights.py --method final --results "$D/results_first.csv" --grid "$D/sim_grid.csv" \
    --out "$D/calibration.json"
fi

echo "== check: scorer.V2 == calibration output"
./build/evalset -popular-v2 assets/popular_v2.txt -print-model > "$D/model_v2.json"
"$PY" - "$D/model_v2.json" "$D/calibration.json" <<'EOF'
import json, sys
m = json.load(open(sys.argv[1])); c = json.load(open(sys.argv[2]))
want_points = {k: v for k, v in c["points"].items() if v}
want_points["I-01"] = m["points"]["I-01"]
s = c["similarity"]
size = 331 if s["list"] == "curated-v1" else int(s["list"].split("-")[1])
problems = []
if m["points"] != want_points: problems.append(f"points {m['points']} != {want_points}")
if (m["warn"], m["danger"]) != (c["warn"], c["danger"]): problems.append("thresholds differ")
if m["points"]["I-01"] < c["danger"]: problems.append("I-01 must reach the DANGER threshold")
ms = m["similarity"]
if (ms["list_size"], ms["min_len"], ms["max_dist"], ms["transpositions"]) != (size, s["min_len"], s["max_dist"], s["transpositions"]):
    problems.append(f"I-05 {ms} != {s}")
if problems:
    sys.exit("scorer.V2 does not match the calibration: " + "; ".join(problems))
print("   match:", m["points"], "thresholds", m["warn"], m["danger"])
EOF

if [ "$LIVE" = 1 ]; then
  echo "== interception test (network)"
  scripts/test_interception.sh test-results/interception
  echo "== latency benchmark (network)"
  scripts/bench_latency.sh bench-results-final 100
fi

echo "== tables and figures"
"$PY" scripts/eval/analyze_v3.py
"$PY" scripts/eval/figures_static.py
if [ -f reproduction/Tests/multimodel/lookup.json ]; then
  echo "== hallucination study (aggregates; uses the frozen name lookup)"
  python3 scripts/eval/analyze_hallucination.py > /dev/null
else
  echo "   (note: reproduction/Tests/multimodel is missing; the hallucination table is not rebuilt; it is not shared)"
fi
echo "== check: V3DormancyDays == dormancy choice"
"$PY" - <<'EOF'
import json, re
want = json.load(open("paper/data/dormancy_choice.json"))["chosen"]
have = int(re.search(r"V3DormancyDays = (\d+)", open("internal/scorer/scorer.go").read()).group(1))
if want != have:
    raise SystemExit(f"internal/scorer V3DormancyDays = {have}, but the dormancy choice is {want}")
print("   match: I-10 dormancy", have, "days")
EOF
echo "done: paper/"
