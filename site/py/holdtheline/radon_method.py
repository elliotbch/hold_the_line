"""Radon transform method.

Python port of matlab/approaches/find_line_radon.m (report, section 2.3):
``imresize(.., 0.2)``, grey level, ``medfilt2`` (3x3), Canny edges with
threshold 0.5, ``radon(edges, 0:179)``, then the projection angle with the
strongest peak gives the orientation of the line.

One step is not ported literally: the prototype sums the peaks of theta and
theta + 90 degrees (``V(1:90) + V(91:180)``) before taking the maximum, which
makes a line and the perpendicular direction indistinguishable and loses the
sign of the angle (its output only served to rotate the image for display).
We take the maximum over the full 0..179 range instead, and convert it to the
signed angle from the vertical used by the other methods.

As in the prototype, the input is first brought to a common size (width
1280 pixels) and reduced by 0.2, i.e. a 256-pixel-wide working image.
"""
from __future__ import annotations

import cv2
import numpy as np
from scipy import ndimage
from skimage.transform import radon

from .common import Detection, resize_to_width, rgb2gray

INPUT_WIDTH = 1280
SCALE = 0.2
CANNY_HIGH = 0.5               # edge(img, 'canny', 0.5): high threshold, low = 0.4 * high
CANNY_SIGMA = np.sqrt(2)       # MATLAB default
THETA = np.arange(180)


def canny(gray: np.ndarray, high: float = CANNY_HIGH, sigma: float = CANNY_SIGMA) -> np.ndarray:
    """MATLAB-style Canny: thresholds are fractions of the maximum gradient magnitude."""
    g = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), sigma)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag_max = float(np.sqrt(gx ** 2 + gy ** 2).max())
    if mag_max == 0:
        return np.zeros(gray.shape, dtype=bool)
    gx16, gy16 = gx.astype(np.int16), gy.astype(np.int16)
    edges = cv2.Canny(gx16, gy16, 0.4 * high * mag_max, high * mag_max, L2gradient=True)
    return edges > 0


def detect(rgb_full: np.ndarray) -> Detection:
    rgb = resize_to_width(rgb_full, INPUT_WIDTH)
    h, w = rgb.shape[:2]
    small = cv2.resize(rgb, (int(round(w * SCALE)), int(round(h * SCALE))), interpolation=cv2.INTER_AREA)
    gray = ndimage.median_filter(rgb2gray(small), size=3, mode="constant", cval=0)
    edges = canny(gray)
    hh, ww = edges.shape
    if edges.sum() < 2:
        return Detection("radon", False, work_shape=(hh, ww), message="No edge found.")
    sinogram = radon(edges.astype(float), theta=THETA, circle=False)
    peaks = sinogram.max(axis=0)
    theta = int(np.argmax(peaks))
    folded = peaks[:90] + peaks[90:]
    # A line at angle a from the vertical (positive = heads right as it goes
    # up) gives its sharpest projection at theta = -a (mod 180) with
    # skimage's / MATLAB's convention, hence:
    angle = -float(((theta + 90) % 180) - 90)
    coef = -np.tan(np.radians(angle))
    # Place the line through the centroid of the edge pixels
    rr, cc = np.nonzero(edges)
    b = float(cc.mean() - coef * rr.mean())
    return Detection("radon", True, float(angle), float(coef), b, [], (hh, ww),
                     extra={"theta_peak": theta, "folded_index_matlab": int(np.argmax(folded)) + 1,
                            "edges": edges})
