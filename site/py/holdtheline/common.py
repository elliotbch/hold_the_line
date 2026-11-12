"""Shared helpers for the Python port of the Hold The Line detectors.

Conventions used everywhere in this package
-------------------------------------------
* Images are RGB ``uint8`` arrays of shape (H, W, 3); row 0 is the top of the
  image, i.e. the part of the ground farthest ahead of the walker.
* As in the MATLAB code, the line is modelled as ``col = coef * row + b``
  (``polyfit(rows, cols, 1)``), which is well conditioned for near-vertical
  lines.
* The reported angle is the angle between the line and the vertical image
  axis (the walking direction), in degrees, **positive when the line heads to
  the right** as it goes away from the walker: ``angle = -atan(coef)``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class Detection:
    """Result of one detector on one image."""

    method: str
    found: bool
    angle_deg: Optional[float] = None
    coef: Optional[float] = None            # d(col)/d(row) of the fitted line
    intercept: Optional[float] = None       # col at row 0, in working-image pixels
    points: List[Tuple[float, float]] = field(default_factory=list)  # (row, col), working image
    work_shape: Tuple[int, int] = (0, 0)    # (H, W) of the working image
    message: str = ""
    extra: Dict = field(default_factory=dict)


def rgb2gray(rgb: np.ndarray) -> np.ndarray:
    """MATLAB ``rgb2gray`` weights (ITU-R BT.601), rounded to uint8."""
    g = rgb[..., 0] * 0.298936 + rgb[..., 1] * 0.587043 + rgb[..., 2] * 0.114021
    return np.clip(np.floor(g + 0.5), 0, 255).astype(np.uint8)


def resize_to_width(rgb: np.ndarray, width: int) -> np.ndarray:
    """Resize keeping the aspect ratio (angles are preserved)."""
    h, w = rgb.shape[:2]
    if w == width:
        return rgb.copy()
    height = max(2, int(round(h * width / w)))
    interp = cv2.INTER_AREA if width < w else cv2.INTER_CUBIC
    return cv2.resize(rgb, (width, height), interpolation=interp)


def run_midpoints(mask: np.ndarray, drop_runs_touching_last_col: bool = True) -> np.ndarray:
    """Middle of every horizontal run of True pixels, row by row.

    Port of ``trouvermilieux`` (matlab/simulink_blocks/findcolor.m and
    findsound.m): for each image row, every maximal segment of same-coloured
    pixels gives one sample at its middle. As in the MATLAB scan, a segment
    that reaches the last column is not recorded.

    Returns an array of shape (N, 2) with (row, col) in pixels (0-based).
    """
    m = mask.astype(np.int8)
    h, w = m.shape
    padded = np.zeros((h, w + 2), dtype=np.int8)
    padded[:, 1:-1] = m
    d = np.diff(padded, axis=1)
    rs, cs = np.nonzero(d == 1)    # run starts (col index)
    re, ce = np.nonzero(d == -1)   # one past run ends
    # np.nonzero is row-major, so starts and ends pair up in order
    ends = ce - 1
    keep = np.ones(len(rs), dtype=bool)
    if drop_runs_touching_last_col:
        keep &= ends < w - 1
    mids = np.floor((cs + ends) / 2 + 0.5)  # MATLAB int16(): round half away from zero
    return np.stack([rs[keep], mids[keep]], axis=1).astype(float)


def fit_line(points: np.ndarray) -> Optional[Tuple[float, float, float]]:
    """``polyfit(rows, cols, 1)``: returns (coef, intercept, sum of squared errors)."""
    if len(points) < 2 or np.ptp(points[:, 0]) == 0:
        return None
    x, y = points[:, 0], points[:, 1]
    coef, intercept = np.polyfit(x, y, 1)
    sse = float(np.sum((y - (coef * x + intercept)) ** 2))
    return float(coef), float(intercept), sse


def coef_to_angle_deg(coef: float) -> float:
    """Angle from the vertical, positive when the line heads right (see module doc)."""
    return float(-np.degrees(np.arctan(coef)))


def stereo_gains(angle_deg: float) -> Tuple[float, float]:
    """Left / right volumes of the guidance tone, as in findsound.m.

    The deployed block computes ``left = sin(a + pi/4)^2`` and
    ``right = cos(a + pi/4)^2`` with saturation beyond +-45 degrees, so the two
    volumes always sum to 1. Two details of the original are not reproduced
    literally because they contradict each other:

    * it uses ``a = (atan(|coef|) + pi/2) * sign(coef)``, whose magnitude is
      always above pi/2, so only the saturated branches were ever reached
      (full left or full right);
    * its saturated branches send the tone to the right ear when the line
      leans to the left ahead (coef > 0), whereas its sine/cosine branch does
      the opposite at the +-45 degree boundary.

    We keep the deployed behaviour of the saturated branches (also used by the
    middle-edge prototype draw_line__1_.m: the tone plays on the side the
    walker is drifting towards, move away from it) and make the law continuous:
    with ``a = atan(coef) = -angle``, clipped to [-45, 45] degrees,
    ``right = sin(a + pi/4)^2`` and ``left = cos(a + pi/4)^2``.
    """
    a = np.radians(np.clip(-angle_deg, -45.0, 45.0))
    right = float(np.sin(a + np.pi / 4) ** 2)
    left = float(np.cos(a + np.pi / 4) ** 2)
    return left, right


def line_endpoints(coef: float, intercept: float, height: int, scale: float = 1.0) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Two (x, y) points of ``col = coef*row + intercept`` at the top and bottom rows."""
    top = (int(round(intercept * scale)), 0)
    bottom_row = height - 1
    bottom = (int(round((coef * bottom_row + intercept) * scale)), int(round(bottom_row * scale)))
    return top, bottom
