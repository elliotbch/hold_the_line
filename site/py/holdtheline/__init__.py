"""Python port of the Hold The Line line detectors (originally MATLAB / Simulink).

Methods (see each module for the MATLAB source it follows):

* ``quantization`` -- k-means colour quantization + middle-sampled linear
  regression, the method deployed on the Raspberry Pi
  (matlab/simulink_blocks/rgbtoimg.m, findcolor.m, findsound.m)
* ``middle_edge``  -- LoG borders and row-by-row middle
  (matlab/approaches/draw_line__1_.m)
* ``radon_method`` -- Canny edges + Radon transform
  (matlab/approaches/find_line_radon.m)
"""
from . import middle_edge, quantization, radon_method
from .common import Detection, stereo_gains

METHODS = {
    "quantization": quantization.detect,
    "middle_edge": middle_edge.detect,
    "radon": radon_method.detect,
}

__all__ = ["METHODS", "Detection", "stereo_gains", "quantization", "middle_edge", "radon_method"]
