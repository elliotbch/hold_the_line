"""Parity check, step 1: reference answers of the FastAPI demo (demo/app.py).

Calls POST /api/detect_example of a running FastAPI demo for every example
image and every method, and writes the results (angle, stereo volumes,
samples, line colour, Radon peak...) to site/tests/expected_api.json.
Step 2 is site/tests/parity.html: it runs the same images through the static
site's Web Worker (Pyodide) and compares.

Tolerance: found / not found must match; middle_edge and radon:
|angle_site - angle_api| <= 0.05 deg and stereo volumes within 0.002;
quantization: <= 0.5 deg and 0.01 (Pyodide 0.27.7 ships OpenCV 4.10 whereas
the server runs OpenCV 5.0, and their k-means can end in slightly different
clusters: natively, OpenCV 4.10 gives the same -5.15 deg as the site on
team_floor_tape.jpg, where OpenCV 5.0 gives -5.4 deg). JPEG files are decoded
by the browser (libjpeg-turbo, like the server's OpenCV), see
site/assets/detect-worker.js.

    uvicorn demo.app:app --port 8189      # from the repository root
    python3 site/tests/parity.py http://127.0.0.1:8189
    python3 -m http.server 8161 -d site   # then open /tests/parity.html
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
API = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8189"
METHODS = ("middle_edge", "quantization", "radon")
KEYS = ("found", "angle_deg", "left", "right", "n_samples", "line_color", "threshold",
        "theta_peak", "lateral_offset_ratio", "message", "time_ms")

cases = []
for ex in json.loads((SITE / "assets" / "examples" / "examples.json").read_text(encoding="utf-8")):
    for m in METHODS:
        body = urllib.parse.urlencode({"name": ex["file"], "method": m}).encode()
        r = json.load(urllib.request.urlopen(API + "/api/detect_example", body))
        cases.append({"file": ex["file"], "method": m, "expected": {k: r.get(k) for k in KEYS}})
        print(f"{ex['file']:28s} {m:13s} found={r['found']!s:5s} angle={r.get('angle_deg')} {r['time_ms']} ms")
(SITE / "tests" / "expected_api.json").write_text(
    json.dumps({"api": API, "cases": cases}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("written", SITE / "tests" / "expected_api.json")
