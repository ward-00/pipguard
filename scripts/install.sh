#!/usr/bin/env bash
# Installs pipguard as a `pip`/`pip3` shim plus shell functions.
# See build_guide.md §5 for the two-layer architecture.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$BIN_DIR"

if [ ! -f "$REPO_DIR/build/pipguard" ]; then
  echo "pipguard: build/pipguard not found. Run 'make build' first." >&2
  exit 1
fi

install -m 0755 "$REPO_DIR/build/pipguard" "$BIN_DIR/pipguard"
ln -sf "$BIN_DIR/pipguard" "$BIN_DIR/pip"
ln -sf "$BIN_DIR/pipguard" "$BIN_DIR/pip3"

# Pick the rc file of the user's login shell.
case "$(basename "${SHELL:-bash}")" in
  zsh)  RC="$HOME/.zshrc"  ;;
  bash) RC="$HOME/.bashrc" ;;
  *)    echo "pipguard: unsupported shell ($SHELL)" >&2; exit 1 ;;
esac

# A marked block, so that uninstall.sh can remove it completely.
# It defines pip(), pip3(), python() and python3(); the last two handle
# `python[3] -m pip install ...`, which the binary shim cannot see.
#
# The functions call the pip/pip3 symlinks (not the pipguard binary) so that
# the shim knows which real pip to look up on PATH.
BLOCK=$(cat <<'EOF'
# >>> BEGIN pipguard >>>
export PATH="$HOME/.local/bin:$PATH"
pip()  { command "$HOME/.local/bin/pip" "$@"; }
pip3() { command "$HOME/.local/bin/pip3" "$@"; }
python() {
  if [ "$1" = "-m" ] && [ "$2" = "pip" ]; then
    shift 2
    command "$HOME/.local/bin/pip" "$@"
  else
    command python "$@"
  fi
}
python3() {
  if [ "$1" = "-m" ] && [ "$2" = "pip" ]; then
    shift 2
    command "$HOME/.local/bin/pip3" "$@"
  else
    command python3 "$@"
  fi
}
# <<< END pipguard <<<
EOF
)

# Replace the block of a previous version so that fixes take effect.
if grep -q "BEGIN pipguard" "$RC" 2>/dev/null; then
  sed -i.bak '/# >>> BEGIN pipguard >>>/,/# <<< END pipguard <<</d' "$RC"
  rm -f "$RC.bak"
  echo "pipguard: replaced the old configuration block in $RC"
fi
printf '\n%s\n' "$BLOCK" >> "$RC"
echo "pipguard: added the configuration block to $RC"

echo "Installed. Run: source $RC"
