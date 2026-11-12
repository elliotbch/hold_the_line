"""Synthetic ground images with a painted line and a known angle.

Used for the demo examples and for the evaluation (scripts/evaluate.py). The
repository contains only a handful of real photos and none of them has a
measured line angle, so the angle error is measured on these synthetic
images: textured ground (asphalt, concrete or carpet), a white or yellow line
with rough edges, perspective narrowing, uneven lighting, optional shadow,
blur, sensor noise and JPEG compression.

Reference angle: least-squares fit ``col = coef*row + b`` of the true centre
line over all image rows, ``angle = -atan(coef)`` (positive = the line heads to
the right as it goes away). For a straight line this is exactly the drawing
angle; for a curved line it is the best single straight line, which is what
the ported detectors estimate.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

H, W = 480, 640


@dataclass
class Sample:
    image: np.ndarray        # RGB uint8
    angle_deg: float         # reference angle
    kind: str                # straight / curved
    ground: str
    line_color: str


def _noise(rng, h, w, sigma, amp):
    n = rng.standard_normal((h, w)).astype(np.float32)
    if sigma > 0:
        n = cv2.GaussianBlur(n, (0, 0), sigma)
        n /= n.std() + 1e-6
    return n * amp


def ground(rng: np.random.Generator, kind: str, h: int = H, w: int = W) -> np.ndarray:
    if kind == "asphalt":
        base = rng.uniform(55, 95)
        g = base + _noise(rng, h, w, 0.8, 18) + _noise(rng, h, w, 3, 8) + _noise(rng, h, w, 20, 6)
        stones = rng.random((h, w)) < 0.02
        g = g + stones * rng.uniform(30, 70)
        tint = np.array([1.0, 1.0, rng.uniform(1.0, 1.06)])
    elif kind == "concrete":
        base = rng.uniform(120, 160)
        g = base + _noise(rng, h, w, 1, 7) + _noise(rng, h, w, 12, 10) + _noise(rng, h, w, 40, 8)
        tint = np.array([rng.uniform(1.0, 1.05), 1.0, rng.uniform(0.93, 1.0)])
    else:  # carpet, like the indoor test floor of the project
        base = rng.uniform(80, 110)
        yy, xx = np.mgrid[0:h, 0:w]
        period = rng.uniform(5, 8)
        weave = 8 * np.sin(2 * np.pi * xx / period) * np.sin(2 * np.pi * yy / period)
        g = base + weave + _noise(rng, h, w, 0.7, 10) + _noise(rng, h, w, 15, 6)
        tint = np.array([1.0, 1.0, 1.04])
    img = np.clip(g[..., None] * tint[None, None, :], 0, 255)
    return img.astype(np.float32)


def render(rng: np.random.Generator, angle_deg: float, curvature: float, ground_kind: str,
           line_color: str, h: int = H, w: int = W):
    """Draw the line; returns (RGB uint8 image, reference angle)."""
    img = ground(rng, ground_kind, h, w)
    rows = np.arange(h, dtype=np.float64)
    dist = (h - 1 - rows) / (h - 1)                      # 0 at the bottom, 1 at the top
    x_bottom = rng.uniform(0.35, 0.65) * w
    centre = x_bottom + np.tan(np.radians(angle_deg)) * (h - 1 - rows) + curvature * w * dist ** 2
    width_bottom = rng.uniform(0.06, 0.10) * w
    half = 0.5 * width_bottom * (1 - 0.4 * dist)          # perspective narrowing
    edge_noise_l = _noise(rng, h, 1, 2, 1.2)[:, 0]
    edge_noise_r = _noise(rng, h, 1, 2, 1.2)[:, 0]
    xx = np.arange(w, dtype=np.float64)[None, :]
    left = (centre - half + edge_noise_l)[:, None]
    right = (centre + half + edge_noise_r)[:, None]
    alpha = np.clip(np.minimum(xx - left, right - xx) + 0.5, 0, 1)   # anti-aliased coverage
    if line_color == "white":
        paint = np.array([rng.uniform(225, 245)] * 3)
    else:
        paint = np.array([rng.uniform(215, 235), rng.uniform(175, 200), rng.uniform(30, 60)])
    wear = 1 - np.clip(_noise(rng, h, w, 1.5, 0.08), -0.1, 0.25)
    line_layer = paint[None, None, :] * wear[..., None]
    img = img * (1 - alpha[..., None]) + line_layer * alpha[..., None]

    # lighting gradient and optional soft shadow
    yy, xx2 = np.mgrid[0:h, 0:w].astype(np.float32)
    gx, gy = rng.uniform(-0.25, 0.25, 2)
    light = 1 + gx * (xx2 / w - 0.5) + gy * (yy / h - 0.5)
    if rng.random() < 0.35:
        cx, cy, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.2, 0.5) * w
        shadow = np.exp(-(((xx2 - cx) ** 2 + (yy - cy) ** 2) / (2 * r ** 2)))
        light *= 1 - rng.uniform(0.2, 0.4) * shadow
    img = img * light[..., None]
    img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.4, 1.0))
    img = img + rng.standard_normal(img.shape).astype(np.float32) * rng.uniform(2, 5)
    img = np.clip(img, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
    img = cv2.cvtColor(cv2.imdecode(buf, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)

    coef = np.polyfit(rows, centre, 1)[0]
    return img, float(-np.degrees(np.arctan(coef))), centre


def make_sample(seed: int, curved: bool) -> Sample:
    """Deterministic sample: the same seed always gives the same image."""
    rng = np.random.default_rng(seed)
    for _ in range(100):
        angle = rng.uniform(-35, 35)
        curvature = rng.uniform(0.12, 0.3) * rng.choice([-1, 1]) if curved else 0.0
        g = rng.choice(["asphalt", "concrete", "carpet"])
        c = rng.choice(["white", "yellow"], p=[0.7, 0.3])
        img, ref, centre = render(rng, angle, curvature, g, c)
        if centre.min() > 0.08 * W and centre.max() < 0.92 * W:   # line fully visible
            return Sample(img, ref, "curved" if curved else "straight", str(g), str(c))
    raise RuntimeError("could not draw a visible line")


def dataset(n_per_kind: int = 30, seed: int = 2023):
    """Evaluation set: n straight and n curved lines, seeds seed..seed+2n-1."""
    return [make_sample(seed + i, curved=i >= n_per_kind) for i in range(2 * n_per_kind)]
