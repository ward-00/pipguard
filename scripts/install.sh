#!/usr/bin/env bash
# Installs pipguard as a pip/pip3 shim (layer 2) plus shell functions (layer 1).
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

case "$(basename "${SHELL:-bash}")" in
  zsh)  RC="$HOME/.zshrc"  ;;
  bash) RC="$HOME/.bashrc" ;;
  *)    echo "pipguard: unsupported shell ($SHELL)" >&2; exit 1 ;;
esac

# python() and python3() catch `python -m pip`, which the shim cannot see. The
# functions call the pip/pip3 links so that the shim knows which pip to find.
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

if grep -q "BEGIN pipguard" "$RC" 2>/dev/null; then
  sed -i.bak '/# >>> BEGIN pipguard >>>/,/# <<< END pipguard <<</d' "$RC"
  rm -f "$RC.bak"
  echo "pipguard: replaced the old configuration block in $RC"
fi
printf '\n%s\n' "$BLOCK" >> "$RC"
echo "pipguard: added the configuration block to $RC"

echo "Installed. Run: source $RC"
