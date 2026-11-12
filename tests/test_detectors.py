import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from holdtheline import METHODS, stereo_gains  # noqa: E402
from holdtheline.common import run_midpoints  # noqa: E402
from holdtheline.synthetic import make_sample  # noqa: E402


def test_run_midpoints_matches_matlab_scan():
    m = np.zeros((2, 10), dtype=bool)
    m[0, 2:5] = True          # run 2..4 -> middle 3
    m[1, 6:10] = True         # run touching the last column: dropped by findsound
    pts = run_midpoints(m, drop_runs_touching_last_col=True)
    assert pts.tolist() == [[0.0, 3.0]]


def test_stereo_gains_follow_findsound():
    assert stereo_gains(0) == pytest.approx((0.5, 0.5))
    l, r = stereo_gains(30)
    assert l > r and l + r == pytest.approx(1)
    assert stereo_gains(60) == pytest.approx((1.0, 0.0))     # saturated beyond 45 degrees
    assert stereo_gains(-60) == pytest.approx((0.0, 1.0))


@pytest.mark.parametrize("name", list(METHODS))
@pytest.mark.parametrize("seed", [5004, 5007])
def test_detectors_recover_known_angle(name, seed):
    s = make_sample(seed, curved=False)
    d = METHODS[name](s.image)
    assert d.found
    assert abs(d.angle_deg - s.angle_deg) < 3


def test_synthetic_is_deterministic():
    a, b = make_sample(1, False), make_sample(1, False)
    assert np.array_equal(a.image, b.image) and a.angle_deg == b.angle_deg
