"""Hold The Line: glue code of the static site (runs in Pyodide, in a Web Worker).

Same behaviour as ``/api/detect`` and ``/api/detect_example`` in
``demo/app.py``, without FastAPI: ``decode_image``, ``annotate`` and ``run``
below are copies of the functions of demo/app.py (HTTP errors become
``InvalidImage``). The detectors themselves are the modules of
``holdtheline/``, copied unchanged into ``site/py/`` by ``site/sync_py.sh``.

Loading order: ``holdtheline/__init__.py`` imports the three methods, and the
Radon one needs scikit-image (about 10 MB more to download). To give a first
result sooner, the worker registers the ``holdtheline`` package without
running its ``__init__`` (``register_package``), imports ``middle_edge`` and
``quantization`` right away and ``radon_method`` once scikit-image is loaded
(``enable_radon``). ``METHODS`` below is the dictionary of ``__init__.py``.
"""
from __future__ import annotations

import base64
import importlib
import importlib.util
import json
import sys
import time
from typing import Optional

import cv2
import numpy as np

APP_DIR = "/home/pyodide/app"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_SIDE = 1600            # larger photos are downscaled before detection
DISPLAY_WIDTH = 640
MESSAGES_FR = {
    "Fewer than two rows with two borders: no line found.":
        "Moins de deux lignes de pixels avec deux bords : aucune ligne trouvée.",
    "No colour forms a line-like set of segments.":
        "Aucune couleur ne forme un ensemble de segments alignés comme une ligne.",
    "No pixel close enough to the line colour after filtering.":
        "Aucun pixel assez proche de la couleur de la ligne après filtrage.",
    "No edge found.": "Aucun bord trouvé.",
}


def register_package() -> None:
    """Register holdtheline/ as a package without executing its __init__.py."""
    if "holdtheline" in sys.modules:
        return
    spec = importlib.util.spec_from_file_location(
        "holdtheline", f"{APP_DIR}/holdtheline/__init__.py",
        submodule_search_locations=[f"{APP_DIR}/holdtheline"])
    sys.modules["holdtheline"] = importlib.util.module_from_spec(spec)


register_package()
from holdtheline import middle_edge, quantization  # noqa: E402
from holdtheline.common import line_endpoints, stereo_gains  # noqa: E402

METHODS = {"quantization": quantization.detect, "middle_edge": middle_edge.detect}


def enable_radon() -> None:
    """Called once scikit-image is loaded."""
    radon_method = importlib.import_module("holdtheline.radon_method")
    METHODS["radon"] = radon_method.detect


class InvalidImage(ValueError):
    """Equivalent of the HTTP 4xx errors of demo/app.py."""


def _limit(bgr: np.ndarray) -> np.ndarray:
    h, w = bgr.shape[:2]
    if min(h, w) < 32:
        raise InvalidImage("Image trop petite (32 × 32 pixels au minimum).")
    s = MAX_SIDE / max(h, w)
    if s < 1:
        bgr = cv2.resize(bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def decode_image(data: bytes) -> np.ndarray:
    """demo/app.py: decode_image."""
    if not data:
        raise InvalidImage("Fichier vide.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise InvalidImage("Image trop volumineuse (8 Mo au maximum).")
    bgr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise InvalidImage("Impossible de lire ce fichier comme une image (JPEG, PNG ou WebP attendu).")
    return _limit(bgr)


def annotate(rgb: np.ndarray, det) -> str:
    """demo/app.py: annotate (display copy with the samples, the fitted line and the angle)."""
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
    cv2.line(img, (dw // 2, dh - 1), (dw // 2, int(dh * 0.6)), (255, 255, 255), 2, cv2.LINE_AA)
    label = f"{det.angle_deg:+.1f} deg".replace(".", ",") if det.found else "pas de ligne"
    cv2.rectangle(img, (8, 8), (16 + 13 * len(label), 44), (20, 20, 20), -1)
    cv2.putText(img, label, (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def run(rgb: np.ndarray, method: str, color: Optional[str], threshold: Optional[float]) -> dict:
    """demo/app.py: run."""
    if method not in METHODS:
        raise InvalidImage(f"Méthode inconnue '{method}'. Choisissez parmi : {', '.join(METHODS)}.")
    t0 = time.perf_counter()
    if method == "quantization" and color and threshold is not None:
        try:
            c = [float(x) for x in color.split(",")]
            assert len(c) == 3
        except Exception:
            raise InvalidImage("color doit être au format 'r,g,b'.")
        det = quantization.detect(rgb, color=c, threshold=threshold)
    else:
        det = METHODS[method](rgb)
    dt = (time.perf_counter() - t0) * 1000
    out = {"method": method, "found": det.found, "time_ms": round(dt, 1),
           "message": MESSAGES_FR.get(det.message, det.message),
           "image": annotate(rgb, det), "n_samples": len(det.points)}
    if det.found:
        left, right = stereo_gains(det.angle_deg)
        out.update({"angle_deg": round(det.angle_deg, 2), "left": round(left, 3), "right": round(right, 3),
                    "angle_raw": det.angle_deg})
    for key in ("line_color", "threshold", "color_updated", "lateral_offset_ratio", "theta_peak"):
        if key in det.extra:
            out[key] = det.extra[key]
    return out


def _json(out: dict) -> str:
    return json.dumps(out, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))


def _to_bytes(data) -> bytes:
    """JS Uint8Array (JsProxy) or Python bytes."""
    return data.to_bytes() if hasattr(data, "to_bytes") else bytes(data)


def detect_bytes(data, method: str, color=None, threshold=None) -> str:
    """Encoded image file (JPEG, PNG, WebP), like POST /api/detect. Returns JSON text."""
    try:
        t0 = time.perf_counter()
        rgb = decode_image(_to_bytes(data))
        out = run(rgb, method, color, None if threshold is None else float(threshold))
        out["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return _json(out)
    except InvalidImage as e:
        return _json({"error": str(e)})


def detect_rgba(data, width: int, height: int, method: str, color=None, threshold=None) -> str:
    """Raw RGBA pixels: a webcam frame, or an image file decoded by the browser.

    The worker decodes JPEG files with the browser (libjpeg-turbo, as the
    server's OpenCV) because the libjpeg of Pyodide's OpenCV gives slightly
    different pixels; ``detect_bytes`` (cv2.imdecode) is the fallback.
    """
    try:
        t0 = time.perf_counter()
        rgba = np.frombuffer(_to_bytes(data), np.uint8).reshape(int(height), int(width), 4)
        rgb = _limit(cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR))
        out = run(rgb, method, color, None if threshold is None else float(threshold))
        out["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return _json(out)
    except InvalidImage as e:
        return _json({"error": str(e)})
