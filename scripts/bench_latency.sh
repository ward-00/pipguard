#!/usr/bin/env bash
# Latency benchmark of pipguard (design goal G4).
#
# Two groups of measurements:
#   Set 1 (passthrough overhead): `pip index versions requests` run directly
#     and through the pipguard shim (which execs pip at once for subcommands
#     it does not check). Pure process and PATH-lookup overhead, mixed with
#     real network noise to PyPI.
#
#   Set 2 (overhead of the install check): `pip install ...` is forwarded to a
#     stub "pip" that exits immediately, so that pip's own download and
#     dependency resolution are NOT measured, only pipguard itself:
#     parse -> cache/fetch -> score -> forward. Conditions:
#       cold        empty cache in every iteration (real PyPI request)
#       warm        cache holding one entry (goal G4)
#       warm-1000   cache holding 1,000 fresh entries (realistic upper bound)
#       req-20-warm `-r requirements.txt` with 20 packages, all cached
#     plus a reference point: a Python interpreter that only starts and reads
#     the same cache file (the minimum an equivalent Python tool would pay).
#
# Each execution is timed with microsecond resolution (date +%s%N). Output:
# raw files (one value in milliseconds per line) in $OUTDIR, a summary in
# $OUTDIR/summary.md and the environment in $OUTDIR/env.txt.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTDIR="${1:?usage: bench_latency.sh <output-dir> [iterations]}"
N="${2:-100}"

mkdir -p "$OUTDIR"
# Work in a directory on the local file system (mktemp), not inside the
# repository: when the repository lives on a Windows drive mounted into WSL
# (9p/drvfs), executing a binary from it adds tens of milliseconds per
# process, an artefact absent from a real installation (install.sh copies
# the binary to ~/.local/bin).
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/shimbin" "$WORK/stubbin" "$WORK/cache" "$WORK/bin"

if [ ! -x "$REPO_DIR/build/pipguard" ]; then
  echo "bench: build/pipguard is missing; run 'make build' first" >&2
  exit 1
fi
install -m 0755 "$REPO_DIR/build/pipguard" "$WORK/bin/pipguard"

# The real pip: skip a pipguard shim that may already be installed on PATH.
REAL_PIP=""
IFS=: read -ra dirs <<< "$PATH"
for d in "${dirs[@]}"; do
  c="$d/pip"
  if [ -x "$c" ] && [ "$(basename "$(readlink -f "$c")")" != "pipguard" ]; then
    REAL_PIP="$c"
    break
  fi
done
if [ -z "$REAL_PIP" ]; then
  echo "bench: the real pip was not found on PATH" >&2
  exit 1
fi

# Shim: symlink pip -> pipguard, placed before the real PATH (so that
# findRealPip finds the next real pip on PATH, not the shim itself).
ln -sf "$WORK/bin/pipguard" "$WORK/shimbin/pip"
ln -sf "$WORK/bin/pipguard" "$WORK/shimbin/pip3"

# Stub: a fake "pip" that exits at once, isolating pipguard's own overhead
# from the installation time of the real pip.
cat > "$WORK/stubbin/pip" <<'EOF'
#!/bin/sh
exit 0
EOF
chmod +x "$WORK/stubbin/pip"

{
  echo "date_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "kernel: $(uname -srm)"
  echo "cpu: $(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2- | sed 's/^ //' || sysctl -n machdep.cpu.brand_string 2>/dev/null)"
  echo "cpus: $(getconf _NPROCESSORS_ONLN)"
  echo "wsl: $(grep -qi microsoft /proc/version 2>/dev/null && echo yes || echo no)"
  echo "go: $(go version 2>/dev/null || echo n/a)"
  echo "pipguard_sha256: $(sha256sum "$WORK/bin/pipguard" | cut -d' ' -f1)"
  echo "binary_fs: $(df -T "$WORK/bin" | awk 'NR==2 {print $2}') ($WORK/bin; repo: $(df -T "$REPO_DIR" | awk 'NR==2 {print $2}'))"
  echo "real_pip: $REAL_PIP ($("$REAL_PIP" --version 2>/dev/null))"
  echo "iterations: $N"
} > "$OUTDIR/env.txt"

us_now() { date +%s%N | cut -c1-16; }  # microseconds since the epoch

record() { # $1=file, $2=t0, $3=t1 (microseconds) -> milliseconds, 3 decimals
  awk -v a="$2" -v b="$3" 'BEGIN { printf "%.3f\n", (b - a) / 1000 }' >> "$1"
}

run_n() {
  local outfile="$1"; shift
  local n="$1"; shift
  : > "$outfile"
  for _ in $(seq "$n"); do
    local t0 t1
    t0=$(us_now)
    "$@" < /dev/null >/dev/null 2>&1 || true
    t1=$(us_now)
    record "$outfile" "$t0" "$t1"
  done
}

stats() {
  # print "mean median p95 p99 max" (milliseconds) of a one-value-per-line file
  sort -g "$1" | awk '
    function q(p,  i) { i = int(p*n + 0.999999); if (i < 1) i = 1; if (i > n) i = n; return a[i] }
    { a[NR]=$1; sum+=$1 }
    END {
      n=NR
      mean=sum/n
      if (n % 2 == 1) med=a[(n+1)/2]; else med=(a[n/2]+a[n/2+1])/2
      printf "%.1f %.1f %.1f %.1f %.1f", mean, med, q(0.95), q(0.99), a[n]
    }'
}

SHIM_ENV=(env PATH="$WORK/shimbin:$WORK/stubbin:$PATH" XDG_CACHE_HOME="$WORK/cache")

# A cache with 1,000 fresh entries: copies of the real "requests" entry under
# other names (the content does not affect parsing time).
make_big_cache() {
  python3 - "$WORK/cache/pipguard/cache.json" <<'EOF'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
e = d["requests"]
for i in range(999):
    d[f"bench-filler-{i:04d}"] = e
json.dump(d, open(p, "w"))
EOF
}

echo "=== Set 1: passthrough overhead (pip index versions requests), N=$N ==="
echo "-> baseline (real pip directly)"
run_n "$OUTDIR/set1_baseline.txt" "$N" "$REAL_PIP" index versions requests
echo "-> through the pipguard shim (unchecked subcommand -> forwarded at once)"
run_n "$OUTDIR/set1_shim.txt" "$N" env PATH="$WORK/shimbin:$(dirname "$REAL_PIP"):$PATH" pip index versions requests

echo
echo "=== Set 2: install check path (forwarded to a stub), N=$N ==="
echo "-> stub baseline (no pipguard)"
run_n "$OUTDIR/set2_stub_baseline.txt" "$N" "$WORK/stubbin/pip" install requests

echo "-> empty cache in every iteration (PyPI request each time)"
: > "$OUTDIR/set2_cold.txt"
for _ in $(seq "$N"); do
  rm -rf "$WORK/cache/pipguard"
  t0=$(us_now)
  "${SHIM_ENV[@]}" pip install requests < /dev/null >/dev/null 2>&1 || true
  t1=$(us_now)
  record "$OUTDIR/set2_cold.txt" "$t0" "$t1"
done

echo "-> warm cache, 1 entry (G4)"
rm -rf "$WORK/cache/pipguard"
"${SHIM_ENV[@]}" pip install requests < /dev/null >/dev/null 2>&1 || true   # warm-up
run_n "$OUTDIR/set2_warm.txt" "$N" "${SHIM_ENV[@]}" pip install requests

echo "-> warm cache, 1,000 entries"
make_big_cache
run_n "$OUTDIR/set2_warm_1000.txt" "$N" "${SHIM_ENV[@]}" pip install requests

echo "-> -r requirements.txt, 20 packages, all cached"
REQ="$WORK/requirements.txt"
printf '%s\n' requests numpy pandas boto3 urllib3 setuptools certifi idna packaging six \
  pyyaml typing-extensions python-dateutil click jinja2 attrs pydantic cryptography rich pytest > "$REQ"
rm -rf "$WORK/cache/pipguard"
# Repeat the warm-up until all 20 packages are cached: the metadata of large
# projects (e.g. pandas, about 2 MB) sometimes exceeds the shim's 3-second
# timeout and then fails open without being cached.
for _ in 1 2 3 4 5; do
  "${SHIM_ENV[@]}" pip install -r "$REQ" < /dev/null >/dev/null 2>&1 || true
  cached=$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$WORK/cache/pipguard/cache.json" 2>/dev/null || echo 0)
  [ "$cached" -ge 20 ] && break
done
echo "   (cached: $cached/20 packages)"

echo "-> reference: Python interpreter that only reads the same cache file"
run_n "$OUTDIR/set2_python_ref.txt" "$N" python3 -S -c "import json,sys; json.load(open(sys.argv[1]))" "$WORK/cache/pipguard/cache.json"
run_n "$OUTDIR/set2_req20_warm.txt" "$N" "${SHIM_ENV[@]}" pip install -r "$REQ"

{
  echo "# pipguard latency benchmark (N=$N per condition)"
  echo
  echo "Generated $(date -u +%Y-%m-%dT%H:%M:%SZ). Environment: \`env.txt\`."
  echo
  echo "| Condition | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | Max (ms) |"
  echo "|---|---:|---:|---:|---:|---:|"
  for pair in \
    "set1_baseline.txt|Set 1: real pip, index versions" \
    "set1_shim.txt|Set 1: through the pipguard shim (passthrough)" \
    "set2_stub_baseline.txt|Set 2: stub pip, no pipguard" \
    "set2_cold.txt|Set 2: pipguard, empty cache (PyPI request)" \
    "set2_warm.txt|Set 2: pipguard, warm cache (1 entry)" \
    "set2_warm_1000.txt|Set 2: pipguard, warm cache (1,000 entries)" \
    "set2_req20_warm.txt|Set 2: pipguard, -r file with 20 cached packages" \
    "set2_python_ref.txt|Reference: Python start-up + reading the cache"
  do
    file="${pair%%|*}"; label="${pair##*|}"
    read -r mean med p95 p99 max <<< "$(stats "$OUTDIR/$file")"
    echo "| $label | $mean | $med | $p95 | $p99 | $max |"
  done
} | tee "$OUTDIR/summary.md"
