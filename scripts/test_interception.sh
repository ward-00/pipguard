#!/usr/bin/env bash
# Automated coverage test of pipguard's interception (invocation contexts)
# and safety behaviour (fail-open, CI, agents, overrides, index options).
#
# Isolated: pipguard is installed into a temporary HOME (scripts/install.sh
# only edits that HOME's .bashrc/.zshrc and .local/bin). No package is ever
# installed: every command uses --no-index, so the real pip fails without
# downloading anything if a command reaches it.
#
# Evidence of interception: a new line in pipguard's activity.log for the test
# package, plus the exit status and messages. Output: <outdir>/results.md,
# <outdir>/results.csv and <outdir>/logs/<id>.txt (raw output per case).
#
# Usage: scripts/test_interception.sh [outdir]
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$(mkdir -p "${1:-$REPO/test-results/interception}" && cd "${1:-$REPO/test-results/interception}" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$OUT/logs"
rm -f "$OUT"/logs/*.txt

# A deliberately unregistered, made-up test name (not an LLM hallucination).
# Checked first so that the test does not rest on an assumption.
BAD="zzz-pipguard-selftest-unregistered"
if curl -fsS -o /dev/null "https://pypi.org/pypi/$BAD/json" 2>/dev/null; then
  echo "test_interception: $BAD is registered on PyPI; choose another test name" >&2
  exit 2
fi

(cd "$REPO" && go build -ldflags="-s -w" -o build/pipguard .) || exit 1
REAL_PIP="$(PATH="$(echo "$PATH" | tr ':' '\n' | grep -v '/.local/bin' | paste -sd:)" command -v pip)"
python3 -m venv "$WORK/venv" >/dev/null || { echo "test_interception: python3 -m venv failed" >&2; exit 1; }
"$WORK/venv/bin/pip" install -q uv >/dev/null 2>&1 || echo "test_interception: uv not available; uv case skipped" >&2

setup_home() { # $1 = shell
  local h="$WORK/home-$1"
  mkdir -p "$h"
  HOME="$h" SHELL="/bin/$1" bash "$REPO/scripts/install.sh" >/dev/null
  echo "$h"
}
HOME_BASH="$(setup_home bash)"
HOME_ZSH="$(SHELL=/usr/bin/zsh; setup_home zsh)"
# A user who allows the environment overrides in the configuration file.
HOME_OVR="$(setup_home bash)-ovr"
cp -r "$HOME_BASH" "$HOME_OVR"
sed -i "s#$HOME_BASH#$HOME_OVR#g" "$HOME_OVR/.bashrc"
mkdir -p "$HOME_OVR/.config/pipguard"
echo '{"allow_env_override": true}' > "$HOME_OVR/.config/pipguard/config.json"

# Base PATH without the real user's own pipguard installation.
BASE_PATH="$(echo "$PATH" | tr ':' '\n' | grep -v "^$HOME/.local/bin$" | paste -sd:)"

printf 'id,shell,scenario,command,expected,observed,exit_code,log_entries,pass\n' > "$OUT/results.csv"
{
  echo "# pipguard interception test results"
  echo
  echo "Generated $(date -u +%Y-%m-%dT%H:%M:%SZ) by \`scripts/test_interception.sh\`"
  echo "System: $(uname -srm); bash ${BASH_VERSION}; $(zsh --version 2>/dev/null); $("$REAL_PIP" --version | cut -d' ' -f1-2)"
  echo
  echo "Test package: \`$BAD\` (deliberately unregistered). \`intercepted\` = pipguard assessed the package"
  echo "(new line in activity.log); \`blocked\` = cancelled before the real pip ran; \`forwarded\` = passed to the"
  echo "real pip; \`not checked\` = pipguard ran but deliberately skipped the check; \`bypass\` = pipguard not involved."
  echo
  echo "| ID | Shell | Scenario | Expected | Observed | Exit | Pass |"
  echo "|---|---|---|---|---|---:|:---:|"
} > "$OUT/results.md"

FAILS=0
# run <id> <shell> <home> <scenario> <expected> <stdin> <command...>
# expected: blocked | prompt-no | prompt-yes | forwarded | failopen | safe | skipped | bypass
run() {
  local id="$1" sh="$2" home="$3" scenario="$4" expected="$5" stdin="$6"; shift 6
  local cache="$WORK/cache-$id" log out code observed pass
  mkdir -p "$cache"
  log="$cache/pipguard/activity.log"
  out="$OUT/logs/$id.txt"
  code=0
  ( cd "$WORK" && env -i HOME="$home" PATH="${RUN_PATH:-$BASE_PATH}" TERM=dumb LANG=C.UTF-8 XDG_CACHE_HOME="$cache" \
      VENV="$WORK/venv" BAD="$BAD" "${EXTRA_ENV[@]}" "$@" ) < "$stdin" > "$out" 2>&1 || code=$?
  local n
  n=$(cat "$log" 2>/dev/null | grep -c "\"package\":\"$BAD\"")

  if grep -q "Continue installation" "$out" && grep -q "Installation cancelled" "$out"; then
    observed="intercepted, prompt, blocked"
  elif grep -q "\[non-interactive\] Installation cancelled" "$out"; then
    observed="intercepted, blocked"
  elif grep -q "could not check" "$out"; then
    observed="check failed, forwarded (fail-open)"
  elif grep -q "non-PyPI source" "$out"; then
    observed="not checked (non-PyPI index), forwarded"
  elif [ "$n" -gt 0 ] && grep -qi "could not find a version\|no matching distribution" "$out"; then
    observed="intercepted, forwarded"
  elif [ "$n" -gt 0 ]; then
    observed="intercepted"
  elif grep -q '"level":"SAFE"' "$log" 2>/dev/null; then
    observed="intercepted, safe, forwarded"
  else
    observed="bypass"
  fi

  case "$expected" in
    blocked)    [[ "$observed" == "intercepted, blocked" && $code -eq 3 ]] && grep -q '^pipguard: {"tool":"pipguard","decision":"blocked"' "$out" ;;
    prompt-no)  [[ "$observed" == "intercepted, prompt, blocked" && $code -eq 3 ]] ;;
    prompt-yes) grep -q "Continue installation" "$out" && [[ "$observed" == *"forwarded"* ]] ;;
    forwarded)  [[ "$observed" == "intercepted, forwarded" ]] ;;
    failopen)   [[ "$observed" == "check failed, forwarded (fail-open)" ]] && grep -qi "could not find a version\|no matching distribution" "$out" ;;
    safe)       [[ "$observed" == "intercepted, safe, forwarded" ]] && ! grep -q "PACKAGE SECURITY WARNING" "$out" ;;
    skipped)    [[ "$observed" == "not checked (non-PyPI index), forwarded" ]] ;;
    bypass)     [[ "$observed" == "bypass" ]] ;;
  esac && pass=yes || { pass=NO; FAILS=$((FAILS + 1)); }

  local cmd="${*: -1}"
  printf '%s,%s,"%s","%s",%s,"%s",%s,%s,%s\n' "$id" "$sh" "$scenario" "${cmd//\"/\"\"}" "$expected" "$observed" "$code" "$n" "$pass" >> "$OUT/results.csv"
  printf '| %s | %s | %s | %s | %s | %s | %s |\n' "$id" "$sh" "$scenario" "$expected" "$observed" "$code" "$pass" >> "$OUT/results.md"
  printf '%-4s %-5s %-58s %-10s -> %-40s %s\n' "$id" "$sh" "$scenario" "$expected" "$observed" "$pass"
}

N=/dev/null
printf 'n\n' > "$WORK/answer-n"
printf 'y\n' > "$WORK/answer-y"
printf 'pip install --no-index %s\n' "$BAD" > "$WORK/t.sh"
printf 'requests\n%s>=1.0  # test package\n' "$BAD" > "$WORK/requirements.txt"
printf 'requests<3\n' > "$WORK/constraints.txt"
SUBPROC="import subprocess,sys; sys.exit(subprocess.run(['pip','install','--no-index','$BAD']).returncode)"
# An AI coding agent typically runs commands in a subprocess without a terminal
# and captures their output.
AGENT="import subprocess,sys; p=subprocess.run('pip install --no-index $BAD', shell=True, capture_output=True, text=True, stdin=subprocess.DEVNULL); sys.stderr.write(p.stderr); sys.exit(p.returncode)"
EXTRA_ENV=()
RUN_PATH=""

for sh in bash zsh; do
  if [ "$sh" = bash ]; then H="$HOME_BASH"; I="bash -i -c"; else H="$HOME_ZSH"; I="zsh -i -c"; fi
  p="${sh:0:1}"
  # A real interactive shell needs a TTY: `script` provides a pty.
  run "${p}1"  "$sh" "$H" "1 Interactive shell (TTY), answer N"            prompt-no  "$WORK/answer-n" script -qec "$I 'pip install --no-index \$BAD'" /dev/null
  run "${p}1y" "$sh" "$H" "1 Interactive shell (TTY), answer Y"            prompt-yes "$WORK/answer-y" script -qec "$I 'pip install --no-index \$BAD'" /dev/null
  run "${p}2"  "$sh" "$H" "2 Active virtual environment"                   blocked    "$N" $I 'source $VENV/bin/activate && pip install --no-index $BAD'
  run "${p}3"  "$sh" "$H" "3 pip3"                                         blocked    "$N" $I 'pip3 install --no-index $BAD'
  run "${p}4"  "$sh" "$H" "4 python -m pip (active venv)"                  blocked    "$N" $I 'source $VENV/bin/activate && python -m pip install --no-index $BAD'
  run "${p}5"  "$sh" "$H" "5 python3 -m pip"                               blocked    "$N" $I 'python3 -m pip install --no-index $BAD'
  run "${p}6"  "$sh" "$H" "6 Non-interactive script (bash t.sh)"           blocked    "$N" $I 'bash $VENV/../t.sh'
  run "${p}7"  "$sh" "$H" "7 Python subprocess"                            blocked    "$N" $I "python3 -c \"$SUBPROC\""
  run "${p}8"  "$sh" "$H" "8 pip install -r requirements.txt"              blocked    "$N" $I 'pip install --no-index -r $VENV/../requirements.txt'
  run "${p}9"  "$sh" "$H" "9 Absolute path to the real pip (limitation)"   bypass     "$N" $I "$REAL_PIP install --no-index \$BAD"
done

# Further contexts and behaviour (bash; the binary, not the shell, decides).
H="$HOME_BASH"; I="bash -i -c"
run "x1"  bash "$H" "Script that activates its own venv (limitation)"     bypass    "$N" $I 'bash -c "source $VENV/bin/activate; pip install --no-index $BAD"'
run "x2"  bash "$H" "Absolute interpreter path, as IDEs run pip (limitation)" bypass "$N" $I '$VENV/bin/python -m pip install --no-index $BAD'
run "x3"  bash "$H" "CI job, stdin not a TTY (/dev/null)"                 blocked   "$N" $I 'pip install --no-index $BAD'
run "x4"  bash "$H" "AI agent: subprocess, no TTY, output captured"       blocked   "$N" $I "python3 -c \"$AGENT\""
run "x5"  bash "$H" "pip download (builds sdists)"                        blocked   "$N" $I 'pip download --no-index -d $VENV/../dl $BAD'
run "x6"  bash "$H" "pip wheel (builds sdists)"                           blocked   "$N" $I 'pip wheel --no-index -w $VENV/../wh $BAD'
run "x7"  bash "$H" "pip install -c constraints.txt"                      blocked   "$N" $I 'pip install --no-index -c $VENV/../constraints.txt $BAD'
run "x8"  bash "$H" "--extra-index-url (warning notes dependency confusion)" blocked "$N" $I 'pip install --no-index --extra-index-url https://example.invalid/simple $BAD'
run "x9"  bash "$H" "Custom primary index -i (not checked by design)"     skipped   "$N" $I 'pip install --no-index -i https://example.invalid/simple $BAD'
run "x10" bash "$H" "Direct URL/VCS requirement (not on PyPI; not checked)" bypass  "$N" $I 'pip install --no-index "git+https://example.invalid/x.git"'
run "x11" bash "$H" "Safe package (requests) passes without a warning"   safe      "$N" $I 'pip install --no-index requests'
if [ -x "$WORK/venv/bin/uv" ]; then
  run "x12" bash "$H" "uv pip install (other installer; limitation)"      bypass    "$N" $I '$VENV/bin/uv pip install --offline --python $VENV/bin/python $BAD'
fi
RUN_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
run "x13" bash "$H" "sudo-style secure_path without ~/.local/bin (limitation)" bypass "$N" bash -c 'pip install --no-index $BAD'
run "x14" bash "$H" "CI runner or container image without pipguard on PATH" bypass "$N" sh -c 'pip install --no-index $BAD'
RUN_PATH="$HOME_BASH/.local/bin:$BASE_PATH"
run "x15" bash "$H" "CI runner or container image with pipguard on PATH"  blocked   "$N" sh -c 'pip install --no-index $BAD'
# Round 2: callers that do not read shell configuration (CI steps, agent tool
# sandboxes) with pipguard's shim on PATH. Only `pip`/`pip3` are shimmed, so the
# `python -m pip` forms are expected to bypass pipguard (documented limitation).
AGENT_M="import subprocess,sys; p=subprocess.run('python3 -m pip install --no-index $BAD', shell=True, capture_output=True, text=True, stdin=subprocess.DEVNULL); sys.stderr.write(p.stderr); sys.exit(p.returncode)"
SUBPROC_M="import subprocess,sys; sys.exit(subprocess.run([sys.executable,'-m','pip','install','--no-index','$BAD'], stdin=subprocess.DEVNULL).returncode)"
run "x20" bash "$H" "Non-interactive shell (CI step): pip"                blocked   "$N" sh -c "python3 -c \"$AGENT\""
run "x21" bash "$H" "Non-interactive shell (CI step): python3 -m pip (limitation)" bypass "$N" sh -c 'python3 -m pip install --no-index $BAD'
run "x22" bash "$H" "Agent subprocess from a non-interactive shell: python3 -m pip (limitation)" bypass "$N" sh -c "python3 -c \"$AGENT_M\""
run "x23" bash "$H" "Python subprocess [sys.executable, -m, pip] (limitation)" bypass "$N" sh -c "python3 -c \"$SUBPROC_M\""
RUN_PATH=""
EXTRA_ENV=(PIPGUARD_ASSUME_YES=1)
run "x16" bash "$H" "PIPGUARD_ASSUME_YES=1 ignored by default (agent-resistant)" blocked "$N" $I 'pip install --no-index $BAD'
run "x17" bash "$HOME_OVR" "PIPGUARD_ASSUME_YES=1 with allow_env_override"  forwarded "$N" bash -i -c 'pip install --no-index $BAD'
EXTRA_ENV=(PIPGUARD_DISABLE=1)
run "x18" bash "$H" "PIPGUARD_DISABLE=1 ignored by default (agent-resistant)" blocked "$N" $I 'pip install --no-index $BAD'
EXTRA_ENV=(HTTPS_PROXY=http://127.0.0.1:9)
run "x19" bash "$H" "Fail-open: PyPI unreachable"                        failopen  "$N" $I 'pip install --no-index $BAD'
EXTRA_ENV=()

{
  echo
  if [ "$FAILS" -eq 0 ]; then echo "**All cases behaved as expected.**"; else echo "**$FAILS case(s) did NOT behave as expected.**"; fi
  echo
  echo "Raw output of every case: \`logs/<ID>.txt\`."
} >> "$OUT/results.md"
echo
echo "results: $OUT/results.md ($FAILS failed)"
exit $((FAILS > 0))
