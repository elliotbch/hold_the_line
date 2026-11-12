"""Hold The Line: web demo.

Thin FastAPI layer over the Python port in ``holdtheline/`` (repository root):
the uploaded image goes through one of the ported detectors, the server
returns the angle, the stereo volumes of findsound.m and an annotated image;
the browser plays the guidance tone with the Web Audio API.

Run from the repository root:  uvicorn demo.app:app --port 7860
"""
from __future__ import annotations

import base64
import json
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
# holdtheline/ lives at the repository root; in the Docker image it is copied
# to demo/_core/ by demo/sync_core.sh.
for candidate in (HERE.parent, HERE / "_core"):
    if (candidate / "holdtheline" / "__init__.py").exists():
        CORE = candidate
        break
else:  # pragma: no cover
    raise RuntimeError("holdtheline/ not found: run demo/sync_core.sh before building the image")
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from holdtheline import METHODS, quantization, stereo_gains  # noqa: E402
from holdtheline.common import line_endpoints  # noqa: E402

STATIC = HERE / "static"
EXAMPLES_DIR = STATIC / "examples"
METRICS_FILE = HERE / "eval_metrics.json"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_SIDE = 1600            # larger photos are downscaled before detection
DISPLAY_WIDTH = 640
_SLOTS = threading.BoundedSemaphore(2)
# French wording of the messages returned by the detectors of holdtheline/
# (the detectors themselves are not modified).
MESSAGES_FR = {
    "Fewer than two rows with two borders: no line found.":
        "Moins de deux lignes de pixels avec deux bords : aucune ligne trouvée.",
    "No colour forms a line-like set of segments.":
        "Aucune couleur ne forme un ensemble de segments alignés comme une ligne.",
    "No pixel close enough to the line colour after filtering.":
        "Aucun pixel assez proche de la couleur de la ligne après filtrage.",
    "No edge found.": "Aucun bord trouvé.",
}

app = FastAPI(title="Démo Hold The Line", docs_url="/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def decode_image(data: bytes) -> np.ndarray:
    if not data:
        raise HTTPException(422, "Fichier vide.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image trop volumineuse (8 Mo au maximum).")
    bgr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise HTTPException(422, "Impossible de lire ce fichier comme une image (JPEG, PNG ou WebP attendu).")
    h, w = bgr.shape[:2]
    if min(h, w) < 32:
        raise HTTPException(422, "Image trop petite (32 × 32 pixels au minimum).")
    s = MAX_SIDE / max(h, w)
    if s < 1:
        bgr = cv2.resize(bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def annotate(rgb: np.ndarray, det) -> str:
    """Display copy of the image with the samples, the fitted line and the angle."""
    h, w = rgb.shape[:2]
    scale_disp = DISPLAY_WIDTH / w
    img = cv2.resize(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), (DISPLAY_WIDTH, int(round(h * scale_disp))),
                     interpolation=cv2.INTER_AREA)
    dh, dw = img.shape[:2]
    if det.work_shape[1]:
        k = dw / det.work_shape[1]          # working image -> display
        mask = det.extra.get("mask")
        if mask is not None and mask.any():  # pixels kept as "line colour" (quantization)
            m = cv2.resize(mask.astype(np.uint8), (dw, dh), interpolation=cv2.INTER_NEAREST).astype(bool)
            img[m] = (0.55 * img[m] + 0.45 * np.array([255, 160, 40])).astype(np.uint8)
        edges = det.extra.get("edges")
        if edges is not None and det.method != "quantization":
            e = cv2.resize(edges.astype(np.uint8), (dw, dh), interpolation=cv2.INTER_NEAREST).astype(bool)
            img[e] = (255, 220, 40)  # cyan (BGR)
        for r, c in det.points[:: max(1, len(det.points) // 150)]:
            cv2.circle(img, (int(round(c * k)), int(round(r * k))), 3, (60, 220, 60), -1, cv2.LINE_AA)
        if det.found:
            p0, p1 = line_endpoints(det.coef, det.intercept, det.work_shape[0], k)
            cv2.line(img, p0, p1, (0, 0, 0), 6, cv2.LINE_AA)
            cv2.line(img, p0, p1, (40, 40, 235), 3, cv2.LINE_AA)
    # walking direction (vertical through the centre) and label
    cv2.line(img, (dw // 2, dh - 1), (dw // 2, int(dh * 0.6)), (255, 255, 255), 2, cv2.LINE_AA)
    # Hershey fonts have no accents nor degree sign: plain ASCII French label.
    label = f"{det.angle_deg:+.1f} deg".replace(".", ",") if det.found else "pas de ligne"
    cv2.rectangle(img, (8, 8), (16 + 13 * len(label), 44), (20, 20, 20), -1)
    cv2.putText(img, label, (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def run(rgb: np.ndarray, method: str, color: Optional[str], threshold: Optional[float]) -> dict:
    if method not in METHODS:
        raise HTTPException(422, f"Méthode inconnue '{method}'. Choisissez parmi : {', '.join(METHODS)}.")
    if not _SLOTS.acquire(timeout=10):
        raise HTTPException(503, "Serveur occupé, réessayez dans quelques secondes.")
    try:
        t0 = time.perf_counter()
        if method == "quantization" and color and threshold is not None:
            try:
                c = [float(x) for x in color.split(",")]
                assert len(c) == 3
            except Exception:
                raise HTTPException(422, "color doit être au format 'r,g,b'.")
            det = quantization.detect(rgb, color=c, threshold=threshold)
        else:
            det = METHODS[method](rgb)
        dt = (time.perf_counter() - t0) * 1000
    finally:
        _SLOTS.release()
    out = {"method": method, "found": det.found, "time_ms": round(dt, 1), "message": MESSAGES_FR.get(det.message, det.message),
           "image": annotate(rgb, det), "n_samples": len(det.points)}
    if det.found:
        left, right = stereo_gains(det.angle_deg)
        out.update({"angle_deg": round(det.angle_deg, 2), "left": round(left, 3), "right": round(right, 3)})
    for key in ("line_color", "threshold", "color_updated", "lateral_offset_ratio", "theta_peak"):
        if key in det.extra:
            out[key] = det.extra[key]
    return out


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "methods": list(METHODS), "metrics": METRICS_FILE.exists()}


@app.get("/api/examples")
def examples() -> JSONResponse:
    return JSONResponse(json.loads((EXAMPLES_DIR / "examples.json").read_text(encoding="utf-8")))


@app.get("/api/metrics")
def metrics() -> JSONResponse:
    if not METRICS_FILE.exists():
        raise HTTPException(404, "demo/eval_metrics.json introuvable : lancez scripts/evaluate.py.")
    return JSONResponse(json.loads(METRICS_FILE.read_text(encoding="utf-8")))


@app.post("/api/detect")
async def detect(file: UploadFile = File(...), method: str = Form("middle_edge"),
                 color: Optional[str] = Form(None), threshold: Optional[float] = Form(None)) -> dict:
    """Detect the line on an uploaded image. ``color``/``threshold`` (quantization
    only) skip the slow colour search, like task B of the deployed system."""
    rgb = decode_image(await file.read(MAX_UPLOAD_BYTES + 1))
    return run(rgb, method, color, threshold)


@app.post("/api/detect_example")
def detect_example(name: str = Form(...), method: str = Form("middle_edge")) -> dict:
    files = {e["file"] for e in json.loads((EXAMPLES_DIR / "examples.json").read_text(encoding="utf-8"))}
    if name not in files:
        raise HTTPException(404, "Exemple inconnu.")
    return run(decode_image((EXAMPLES_DIR / name).read_bytes()), method, None, None)
