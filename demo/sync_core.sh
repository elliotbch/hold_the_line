#!/usr/bin/env sh
# Copy the Python port (holdtheline/) into demo/_core/ so that demo/ is a
# self-contained Docker build context (e.g. the Hugging Face Space).
# _core/ is git-ignored: the source of truth stays holdtheline/ at the root.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
rm -rf "$HERE/_core"
mkdir -p "$HERE/_core"
cp -R "$ROOT/holdtheline" "$HERE/_core/"
find "$HERE/_core" -name "__pycache__" -type d -prune -exec rm -rf {} +
echo "Copied holdtheline/ into $HERE/_core"
