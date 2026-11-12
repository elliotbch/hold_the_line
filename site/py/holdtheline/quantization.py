"""Quantization + middle-sampled linear regression (the method deployed on the Raspberry Pi).

Python port of the three MATLAB Function blocks of simulink/projects5.slx,
extracted in:

* matlab/simulink_blocks/rgbtoimg.m  -- input block: 18x18 average filter
* matlab/simulink_blocks/findcolor.m -- slow task A: k-means colour
  quantization (n = 20, the constant wired to the block in the model), one
  middle-sampled regression per colour, choice of the line colour and of a
  colour threshold
* matlab/simulink_blocks/findsound.m -- fast task B: keep the pixels close to
  the line colour, 16x16 median filter, middle sampling, linear regression,
  angle and stereo volumes

The camera block of the model captures 320x240 RGB frames every 0.1 s, so
images are first resized to a width of 320 pixels.

Where the MATLAB code has indexing bugs we port the evident intent and say so
next to the code (see ``quantize`` and ``find_color``).
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy import ndimage

from .common import Detection, coef_to_angle_deg, fit_line, resize_to_width, rgb2gray, run_midpoints

WORK_WIDTH = 320          # Raspi V4L2 capture block: Resolution 320x240
N_COLORS = 20             # Constant block wired to findcolor's n input
AVERAGE_SIZE = 18         # rgbtoimg.m: fspecial("average", [18, 18])
MEDIAN_SIZE = 16          # findsound.m: medfilt2(img, [16, 16])


def rgbtoimg(rgb: np.ndarray) -> np.ndarray:
    """rgbtoimg.m: 18x18 mean filter on each channel, zero padding (imfilter default)."""
    # MATLAB puts the centre of an even 18x18 kernel at index 9 (1-based),
    # i.e. anchor 8 (0-based) in OpenCV.
    out = cv2.blur(rgb.astype(np.float64), (AVERAGE_SIZE, AVERAGE_SIZE),
                   anchor=(AVERAGE_SIZE // 2 - 1, AVERAGE_SIZE // 2 - 1),
                   borderType=cv2.BORDER_CONSTANT)
    return np.clip(np.floor(out + 0.5), 0, 255).astype(np.uint8)


def quantize(rgb: np.ndarray, k: int, seed: int = 0):
    """findcolor.m / quantize: k-means on the RGB values of every pixel.

    MATLAB's ``kmeans`` (k-means++ seeding, squared Euclidean distance) is
    replaced by ``cv2.kmeans`` with k-means++ seeding and a fixed seed.
    The MATLAB code writes the labels back with
    ``imgt(uint32(i/W)+1, mod(i,W)+1) = idx(i)``, which shifts them by half a
    row and one column (and drops the last row); we use the intended
    row-major reshape.

    Returns (label image HxW in 0..k-1, centroids kx3 float, squared distances HWxk).
    """
    h, w = rgb.shape[:2]
    data = rgb.reshape(-1, 3).astype(np.float32)
    cv2.setRNGSeed(seed)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-3)
    _, labels, centers = cv2.kmeans(data, k, None, criteria, 1, cv2.KMEANS_PP_CENTERS)
    centers = centers.astype(np.float64)
    d2 = ((data[:, None, :].astype(np.float64) - centers[None, :, :]) ** 2).sum(axis=2)
    return labels.reshape(h, w), centers, d2


def find_color(rgb: np.ndarray, n: int = N_COLORS, seed: int = 0) -> dict:
    """findcolor.m (slow task A): colour of the line and acceptance radius.

    For every colour i, the middles of its horizontal segments are sampled
    row by row and fitted with a line; ``err_i`` is the sum of squared
    residuals and ``len_i`` the number of samples. The selection loop is
    ported as written:

        minerror = max(err)
        for i: if err_i < minerror and len_i != max(len):
                   index = i; minerror = err_i / log(len_i)

    (the colour with the most samples, usually the ground, is excluded).

    Threshold: the MATLAB loop is commented "choose the biggest sphere
    possible that contain the only color specified by index", but it indexes
    the distance matrix with ``D(x*y, i)`` (not a valid pixel index) and
    overwrites the running minimum unconditionally, so the value it returns
    is the distance of an arbitrary pixel to an arbitrary centroid. We
    compute the sphere described by the comment: the largest RGB ball around
    the line colour that stays inside its k-means cell, whose radius is half
    the distance to the nearest other centroid.
    """
    labels, centers, _ = quantize(rgb, n, seed)
    errs, lens, fits = [], [], []
    for i in range(n):
        pts = run_midpoints(labels == i, drop_runs_touching_last_col=False)
        fit = fit_line(pts)
        errs.append(np.inf if fit is None else fit[2])
        lens.append(len(pts))
        fits.append((pts, fit))
    errs_a, lens_a = np.array(errs), np.array(lens)
    minerror = np.max(errs_a)
    index = None
    for i in range(n):
        if errs_a[i] < minerror and lens_a[i] != lens_a.max():
            index = i
            minerror = errs_a[i] / np.log(lens_a[i]) if lens_a[i] > 1 else np.inf
    if index is None:
        return {"found": False}
    color = centers[index]
    gaps = np.sqrt(((np.delete(centers, index, axis=0) - color) ** 2).sum(axis=1))
    tresh = float(gaps.min() / 2) if len(gaps) else 0.0
    return {"found": True, "index": int(index), "color": color, "threshold": tresh,
            "cluster_points": fits[index][0], "n_samples": int(lens_a[index])}


def find_sound(rgb: np.ndarray, color: np.ndarray, tresh: float) -> dict:
    """findsound.m (fast task B): threshold on the line colour, median filter, regression."""
    dist = np.sqrt(((rgb.astype(np.float64) - np.asarray(color, dtype=np.float64)) ** 2).sum(axis=2))
    binary = np.where(dist > tresh, 0, 255).astype(np.uint8)
    # rgb2gray of a black/white image is the same image; medfilt2 pads with zeros
    gray = rgb2gray(np.repeat(binary[..., None], 3, axis=2))
    med = ndimage.median_filter(gray, size=(MEDIAN_SIZE, MEDIAN_SIZE), mode="constant", cval=0,
                                origin=(-1, -1))
    pts = run_midpoints(med > 0, drop_runs_touching_last_col=True)
    return {"mask": med > 0, "points": pts, "fit": fit_line(pts)}


def detect(rgb_full: np.ndarray, color=None, threshold=None, n_colors: int = N_COLORS, seed: int = 0) -> Detection:
    """Full pipeline. Pass ``color`` and ``threshold`` to skip task A, as the
    deployed system does between two (slow) colour updates."""
    rgb = rgbtoimg(resize_to_width(rgb_full, WORK_WIDTH))
    extra = {}
    if color is None or threshold is None:
        fc = find_color(rgb, n_colors, seed)
        if not fc["found"]:
            return Detection("quantization", False, work_shape=rgb.shape[:2],
                             message="No colour forms a line-like set of segments.")
        color, threshold = fc["color"], fc["threshold"]
        extra["color_updated"] = True
    else:
        extra["color_updated"] = False
    fs = find_sound(rgb, np.asarray(color, dtype=float), float(threshold))
    extra.update({"line_color": [round(float(c), 1) for c in color], "threshold": round(float(threshold), 2),
                  "mask": fs["mask"]})
    if fs["fit"] is None:
        return Detection("quantization", False, work_shape=rgb.shape[:2], extra=extra,
                         message="No pixel close enough to the line colour after filtering.")
    coef, b, _ = fs["fit"]
    return Detection("quantization", True, coef_to_angle_deg(coef), coef, b,
                     [tuple(p) for p in fs["points"]], rgb.shape[:2], extra=extra)
