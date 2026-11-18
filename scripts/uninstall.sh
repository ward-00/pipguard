#!/usr/bin/env bash
# Removes the pipguard shim, its shell block and its cache.
set -euo pipefail

BIN_DIR="$HOME/.local/bin"
rm -f "$BIN_DIR/pipguard" "$BIN_DIR/pip" "$BIN_DIR/pip3"

for RC in "$HOME/.bashrc" "$HOME/.zshrc"; do
  if [ -f "$RC" ] && grep -q "BEGIN pipguard" "$RC"; then
    # -i.bak: macOS sed rejects -i without a suffix
    sed -i.bak '/# >>> BEGIN pipguard >>>/,/# <<< END pipguard <<</d' "$RC"
    rm -f "$RC.bak"
    echo "pipguard: removed the configuration block from $RC"
  fi
done

rm -rf "${XDG_CACHE_HOME:-$HOME/.cache}/pipguard"

echo "Removed. Open a new terminal so that the shell functions are gone."
