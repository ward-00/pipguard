# Evaluation pipeline

Everything in the paper is rebuilt from the frozen inputs in `testdata/frozen/`:

```bash
scripts/eval/run_all.sh            # offline, about 2 minutes: unit tests, three scenarios, tables, figures
scripts/eval/run_all.sh --refit    # also re-fits the iteration-2 weights (must equal the code)
scripts/eval/run_all.sh --live     # also the interception test and latency benchmark (network)
```

Outputs: `paper/numbers_v3.json`, `paper/tables/t_*.{csv,md}`, `paper/figures/fig_*.{pdf,png}`,
`paper/data/results_*.csv` (per package; hallucinated names redacted).

## Data

| Group | n | Source |
|---|---:|---|
| Malicious packages that were installable | 8,588 | OSV `MAL-*` reports for PyPI (11,800 names, export of 2026-10-14) × per-version history from the public ClickPy mirror (`pypi.projects`) |
| New legitimate packages | 4,850 | Random PyPI projects first uploaded 2023-01 … 2026-06, alive in October 2026, not in OSV; history from the PyPI JSON API |
| Established packages | 5,000 | hugovk top-pypi-packages: ranks 1,001–15,000 (dev/test halves) and the top 1,000 |
| Prospective hold-out | 97 | OSV reports published after the design freeze (2026-10-19 … 24) |
| Download logs | – | ClickPy `pypi_downloads_per_day_by_version_by_installer_by_type`; only project-filtered or chunked queries, each verified complete (see below) |
| Hallucination probe | 2,000 prompts | Four open models, `reproduction/multimodel.py` (raw output git-ignored) |

Temporal split by the first (malicious) upload: **dev** < 2025, **val** 2025, **test** 2026. Every malicious
package is assessed as pipguard's registry client would have seen it one minute after the first malicious upload
(primary), one minute after the last version, and at the OSV report.

## Scripts

| File | Purpose |
|---|---|
| `pypi_history.py` | ClickHouse client (shared `demo` quota, query splitting) and point-in-time reconstruction `snapshot()` |
| `build_sets.py` | Online steps that built the frozen inputs, and the offline `meta` step (per-scenario JSONL) |
| `fetch_v3.py` | Online steps of the journal revision: exposure, uploaders (campaigns), cooldown and dormancy costs, prospective hold-out, download-log presence, release timelines |
| `fit_weights.py` | Calibration of the iteration-2 weights (`--method final`, val) and the rejected early model (`--method initial`, dev) |
| `analyze_v3.py` | All tables, figures and `paper/numbers_v3.json` (campaign bootstrap, exposure, cost, drift, re-calibration, I-10 choice) |
| `analyze_hallucination.py` | Hallucination study (aggregates only) |
| `figures_static.py` | Architecture figure and the recorded warning |
| `compare_tools.py` | Live comparison of pip `--uploaded-prior-to`, uv `--exclude-newer` and pipguard |
| `run_all.sh` | Runs everything offline |

`analyze.py` and `figures_id.py` belong to the second iteration (kept for history; their old outputs are in
`paper/legacy_v2/`).

## Refreshing the frozen inputs (numbers will change)

```bash
python3 scripts/malicious/build_malicious_set.py names        # OSV -> testdata/malicious_osv.csv
python3 scripts/eval/build_sets.py malicious-fetch            # ClickPy per-version metadata (shared quota)
python3 scripts/eval/build_sets.py benign-sample && python3 scripts/eval/build_sets.py benign-fetch
python3 scripts/eval/build_sets.py established
python3 scripts/eval/fetch_v3.py exposure        # downloads of malicious releases by age
python3 scripts/eval/fetch_v3.py campaign        # uploader fields for campaign clustering
python3 scripts/eval/fetch_v3.py presence        # download-log footprint of every OSV name
python3 scripts/eval/fetch_v3.py release-times   # release timelines of legitimate packages
python3 scripts/eval/fetch_v3.py cost --start 2026-06-01 --end 2026-06-30
python3 scripts/eval/fetch_v3.py dormancy-cost --start 2026-06-01 --end 2026-06-30
python3 scripts/eval/fetch_v3.py prospective
# round 2 (peer review, 2026-10-25)
python3 scripts/eval/fetch_v3.py cost-complete   # 24 monthly costs, 23 project-name chunks, completeness-checked
python3 scripts/eval/fetch_v3.py background      # download profile of the new legitimate packages (control)
python3 scripts/eval/fetch_v3.py filetype        # sdist vs built downloads of every OSV name (survivorship test)
python3 scripts/eval/fetch_v3.py dependents      # projects declaring a malicious package in requires_dist
python3 scripts/eval/fetch_v3.py cases           # six high-impact incidents (timelines, downloads)
python3 scripts/eval/fetch_v3.py dep-additions   # dependency additions in releases and the added project's age
```

**Silent truncation.** The `demo` user has `max_rows_to_read = 1e9` with `read_overflow_mode = 'break'`:
a query that would read more rows returns *partial sums without an error*. The download tables are ordered by
project, so a query filtered only by date (the round-1 `cost` and `dormancy-cost` steps) reads an arbitrary,
project-clustered fragment (this is what had looked like a "stable 13% subset"). Use
`pypi_history.query_complete()`, which raises unless `read_rows == total_rows_to_read`; `cost-complete` splits
the table into name ranges using the primary index (`mergeTreeIndex`). The round-1 cost files are kept for
the record but no longer used for decisions. The demo user is also limited to 20 queries of the same shape
per hour; `query_complete()` waits when a quota is exhausted.

The ClickPy `demo` user's quota (about 60,000 result rows per hour) is shared with everyone; fetches wait
automatically when it is exhausted. No step downloads or executes a package file; only metadata and aggregated
download counts are read.
