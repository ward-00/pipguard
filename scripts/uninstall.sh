#!/usr/bin/env bash
# Removes pipguard: the binary shim and the shell configuration block.
# `sed -i.bak` (with a suffix) keeps this portable to macOS BSD sed, which
# rejects `-i` without an argument. See build_guide.md §5.3.
set -euo pipefail

BIN_DIR="$HOME/.local/bin"
rm -f "$BIN_DIR/pipguard" "$BIN_DIR/pip" "$BIN_DIR/pip3"

for RC in "$HOME/.bashrc" "$HOME/.zshrc"; do
  if [ -f "$RC" ] && grep -q "BEGIN pipguard" "$RC"; then
    sed -i.bak '/# >>> BEGIN pipguard >>>/,/# <<< END pipguard <<</d' "$RC"
    rm -f "$RC.bak"
    echo "pipguard: removed the configuration block from $RC"
  fi
done

rm -rf "$HOME/.cache/pipguard"

echo "Removed. Open a new terminal so that the shell functions are gone."
