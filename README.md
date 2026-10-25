# pipguard

A client-side interceptor for `pip` that checks every requested package against PyPI **before** pip runs, and asks
for confirmation when the package is not registered (a possible hallucinated name, i.e. slopsquatting) or when the
project was first published less than 30 days ago (a project-level dependency cooldown). Metadata indicators grade
the warning (WARNING or DANGER) but never decide on their own. This repository also contains the time-aware
evaluation behind the paper *Cooldowns before classifiers: A time-aware evaluation of install-time defenses against
new malicious PyPI packages*.

- **Platforms:** Linux and macOS (amd64, arm64), bash and zsh
- **Language:** Go 1.22+ (developed with go1.26), standard library only
- **Runtime dependencies:** none (single static binary)

## Quick start

```bash
make build              # -> build/pipguard
make test               # unit tests of all packages
make install            # shim + shell functions in ~/.local/bin and your shell rc file
source ~/.bashrc        # or ~/.zshrc
pip install <package>   # now checked by pipguard
```

Remove with `make uninstall`.

## Behaviour

| Situation | What pipguard does |
|---|---|
| Established package | Nothing visible; pip runs (about 11 ms overhead with a warm cache) |
| Unregistered name | DANGER prompt explaining slopsquatting (pip would fail anyway) |
| Project younger than 30 days | WARNING prompt; DANGER if its metadata looks like known malware |
| No terminal (CI, scripts, AI agents) | Cancels, prints one JSON line `pipguard: {"decision":"blocked",...}`, exits with status **3** |
| Network or internal error | Forwards to pip with a notice (fail-open) |
| Custom primary index (`-i`, `PIP_INDEX_URL`) | Not checked (PyPI metadata does not apply); notice |
| `--extra-index-url` | Checked; the warning notes the dependency-confusion risk |

Subcommands `install`, `download` and `wheel` are checked (the latter two build sdists, which runs package code);
everything else is forwarded unchanged. Packages listed in `-r` requirements files are checked too.

## Configuration

`~/.config/pipguard/config.json` (per user) and `/etc/pipguard/config.json` (system; `"locked": true` makes it
override the user file and the environment):

```json
{
  "allow": ["corp-internal-lib"],
  "allow_env_override": false,
  "release_dormancy_days": 0,
  "check_custom_index": false
}
```

| Setting / variable | Effect |
|---|---|
| `allow` | Names that are never prompted for (e.g. private packages) |
| `PIPGUARD_ASSUME_YES=1`, `PIPGUARD_DISABLE=1` | Honoured **only** if `allow_env_override` is true, so an agent that only controls the environment cannot switch pipguard off |
| `release_dormancy_days` | Enables rule I-10: also prompt for a release younger than 30 days that follows at least this many days without releases (compromised or re-activated projects). Off by default because it prompts far more often; see the paper, Tables 12–13 |
| `XDG_CACHE_HOME`, `XDG_CONFIG_HOME` | Cache/log and configuration locations |

## Layout

```
main.go                       flow: find the real pip -> parse (+ -r files, index options) -> check -> exec pip
internal/parser/              package names (PEP 503), requirements files, index options, subcommands
internal/registry/            PyPI JSON API client (incl. latest/previous release times)
internal/cache/               ~/.cache/pipguard/cache.json, 24 h TTL
internal/scorer/              indicators I-01..I-10; models v1 (initial), v2 (calibrated), v3 (shipped: v2 + opt-in I-10)
internal/ui/                  warning, Y/N prompt, JSON decision record, TTY detection
internal/config/              configuration files, locking, environment overrides
cmd/evalset/                  evaluation tool (detectors, baselines, ablation, per-package CSV)
scripts/install.sh, uninstall.sh
scripts/test_interception.sh  43 automated interception cases (bash and zsh)
scripts/bench_latency.sh      latency benchmark
scripts/eval/                 evaluation pipeline (see scripts/eval/README.md)
testdata/frozen/              frozen evaluation inputs (reproducible offline)
paper/                        tables, figures (black and white), numbers_v3.json
```

## Reproducing the paper

```bash
scripts/eval/run_all.sh            # offline: unit tests, evaluation, tables and figures (about 2 minutes)
scripts/eval/run_all.sh --live     # also the interception test and the latency benchmark (network)
python3 scripts/eval/compare_tools.py            # live comparison with pip --uploaded-prior-to and uv (network)
```

Hallucinated package names that are not registered are never published (they would enable slopsquatting); the
files that contain them are git-ignored (`reproduction/Tests/`, `testdata/positive_*.txt`,
`testdata/frozen/meta_hallucinated_live.jsonl`).
