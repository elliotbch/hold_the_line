"""Middle edge method.

Python port of matlab/approaches/draw_line__1_.m (report, section 2.2):

1. grey level, ``imresize(.., 1/8)``, ``imsharpen`` (unsharp masking,
   radius 1, amount 0.8), ``imgaussfilt(.., 5)``;
2. ``edge(.., 'log')``: zero crossings of a Laplacian of Gaussian
   (sigma 2, automatic threshold 0.75 x mean |LoG|), which gives the two
   borders of the painted line;
3. on every row, the first two edge pixels found from the left are taken as
   the two borders and their middle ``floor((p + j) / 2)`` is drawn.

The prototype then read only one row, at 9/10 of the height, and played a
tone whose volume grows with the lateral distance between the image centre
(the walker) and the drawn middle. To give an angle comparable with the other
methods, we additionally fit ``col = coef*row + b`` through all the drawn
middles (same regression as findsound.m); the lateral offset at 9/10 of the
height is reported too.

The prototype read full-size photos; we first bring every image to a width of
1280 pixels, so the 1/8 reduction gives a 160-pixel-wide working image.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy import ndimage

from .common import Detection, coef_to_angle_deg, fit_line, resize_to_width, rgb2gray

INPUT_WIDTH = 1280
REDUCTION = 8
SHARPEN_SIGMA, SHARPEN_AMOUNT = 1.0, 0.8     # imsharpen defaults
SMOOTH_SIGMA = 5.0                           # imgaussfilt(s, 5)
LOG_SIGMA = 2.0                              # edge(.., 'log') default


def _gauss(img: np.ndarray, sigma: float) -> np.ndarray:
    """imgaussfilt: kernel 2*ceil(2*sigma)+1, replicate padding."""
    k = 2 * int(np.ceil(2 * sigma)) + 1
    return cv2.GaussianBlur(img, (k, k), sigma, borderType=cv2.BORDER_REPLICATE)


def _log_kernel(sigma: float) -> np.ndarray:
    """fspecial('log', ceil(sigma*3)*2+1, sigma), zero-sum as in MATLAB."""
    size = int(np.ceil(sigma * 3) * 2 + 1)
    r = (size - 1) / 2
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    arg = -(x * x + y * y) / (2 * sigma * sigma)
    h = np.exp(arg)
    h[h < np.finfo(float).eps * h.max()] = 0
    h /= h.sum()
    h1 = h * (x * x + y * y - 2 * sigma * sigma) / sigma ** 4
    return h1 - h1.sum() / h1.size


def edge_log(img: np.ndarray, sigma: float = LOG_SIGMA) -> np.ndarray:
    """MATLAB ``edge(I, 'log')``: zero crossings of the LoG response whose jump exceeds the threshold."""
    a = img.astype(np.float64) / 255.0
    b = ndimage.correlate(a, _log_kernel(sigma), mode="nearest")
    thresh = 0.75 * np.mean(np.abs(b))
    e = np.zeros(b.shape, dtype=bool)
    c, r_ = b[:, :-1], b[:, 1:]                  # horizontal neighbours
    e[:, :-1] |= (c < 0) & (r_ > 0) & (np.abs(c - r_) > thresh)
    e[:, 1:] |= (c > 0) & (r_ < 0) & (np.abs(c - r_) > thresh)
    c, d = b[:-1, :], b[1:, :]                   # vertical neighbours
    e[:-1, :] |= (c < 0) & (d > 0) & (np.abs(c - d) > thresh)
    e[1:, :] |= (c > 0) & (d < 0) & (np.abs(c - d) > thresh)
    return e


def preprocess(rgb_full: np.ndarray) -> np.ndarray:
    gray = rgb2gray(resize_to_width(rgb_full, INPUT_WIDTH))
    h, w = gray.shape
    small = cv2.resize(gray, (w // REDUCTION, h // REDUCTION), interpolation=cv2.INTER_AREA)
    s = small.astype(np.float64)
    sharp = np.clip(s + SHARPEN_AMOUNT * (s - _gauss(s, SHARPEN_SIGMA)), 0, 255)
    return _gauss(np.floor(sharp + 0.5).astype(np.uint8), SMOOTH_SIGMA)


def detect(rgb_full: np.ndarray) -> Detection:
    smo = preprocess(rgb_full)
    edges = edge_log(smo)
    h, w = edges.shape
    points = []
    for i in range(h):
        cols = np.flatnonzero(edges[i])
        if len(cols) >= 2:                       # first two borders from the left
            p, j = cols[0], cols[1]
            points.append((float(i), float((p + j) // 2)))
    pts = np.array(points, dtype=float).reshape(-1, 2)
    fit = fit_line(pts)
    extra = {"edges": edges}
    a = int(round(h * 9 / 10)) - 1               # row used by the prototype for the sound
    on_a = pts[pts[:, 0] == a] if len(pts) else pts
    if len(on_a):
        extra["lateral_offset_px"] = float(on_a[0, 1] - (w // 2))  # >0: line right of the walker
        extra["lateral_offset_ratio"] = round(float(on_a[0, 1] - (w // 2)) / w, 3)
    if fit is None:
        return Detection("middle_edge", False, work_shape=(h, w), extra=extra,
                         message="Fewer than two rows with two borders: no line found.")
    coef, b, _ = fit
    return Detection("middle_edge", True, coef_to_angle_deg(coef), coef, b,
                     [tuple(p) for p in pts], (h, w), extra=extra)
