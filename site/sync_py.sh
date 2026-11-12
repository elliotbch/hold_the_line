#!/usr/bin/env sh
# Copy what the static site runs in the browser (Pyodide) and shows:
#   holdtheline/                    -> site/py/holdtheline/ (unchanged copy)
#   demo/static/examples/*          -> site/assets/examples/
#   demo/eval_metrics.json          -> site/assets/eval_metrics.json
# site/py/web_detect.py (glue code of the site) is not touched.
# The source of truth stays holdtheline/ at the repository root: run this
# script after changing it (the Pages workflow runs it too).
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
rm -rf "$HERE/py/holdtheline" "$HERE/assets/examples"
mkdir -p "$HERE/py" "$HERE/assets/examples"
cp -R "$ROOT/holdtheline" "$HERE/py/"
find "$HERE/py" -name "__pycache__" -type d -prune -exec rm -rf {} +
cp "$ROOT"/demo/static/examples/* "$HERE/assets/examples/"
cp "$ROOT/demo/eval_metrics.json" "$HERE/assets/eval_metrics.json"
python3 - "$HERE" <<'PY'
import json, sys
from pathlib import Path
site = Path(sys.argv[1])
files = sorted(str(p.relative_to(site / "py")) for p in (site / "py").rglob("*.py"))
(site / "py" / "manifest.json").write_text(json.dumps(files, indent=1) + "\n")
PY
echo "Copied holdtheline/ into $HERE/py, examples and metrics into $HERE/assets"
