import sys
from pathlib import Path

import cv2
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as demo_app  # noqa: E402

client = TestClient(demo_app.app)
EXAMPLES = client.get("/api/examples").json()
METHODS = ["middle_edge", "quantization", "radon"]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert set(r.json()["methods"]) == set(METHODS)


def test_page_is_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "Hold The Line" in r.text
    assert "https://github.com/elliotbch/hold_the_line" in r.text


def test_examples_exist():
    assert 3 <= len(EXAMPLES) <= 6
    for e in EXAMPLES:
        assert client.get(f"/static/examples/{e['file']}").status_code == 200


def test_metrics():
    m = client.get("/api/metrics").json()
    assert m["dataset"]["synthetic"] is True
    assert set(m["methods"]) == set(METHODS)


@pytest.mark.parametrize("method", METHODS)
def test_each_method_on_synthetic_example(method):
    ex = next(e for e in EXAMPLES if e["reference_angle_deg"] is not None)
    r = client.post("/api/detect_example", data={"name": ex["file"], "method": method})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["found"] is True
    assert abs(d["angle_deg"] - ex["reference_angle_deg"]) < 5
    assert abs(d["left"] + d["right"] - 1) < 1e-6
    assert d["image"].startswith("data:image/jpeg;base64,")


def test_upload_and_color_reuse():
    ex = EXAMPLES[-1]
    data = (demo_app.EXAMPLES_DIR / ex["file"]).read_bytes()
    r = client.post("/api/detect", files={"file": ("x.jpg", data, "image/jpeg")}, data={"method": "quantization"})
    assert r.status_code == 200
    d = r.json()
    assert d["color_updated"] is True
    r2 = client.post("/api/detect", files={"file": ("x.jpg", data, "image/jpeg")},
                     data={"method": "quantization", "color": ",".join(map(str, d["line_color"])),
                           "threshold": str(d["threshold"])})
    assert r2.status_code == 200 and r2.json()["color_updated"] is False


def test_errors_are_clean():
    assert client.post("/api/detect", files={"file": ("x.jpg", b"not an image", "image/jpeg")}).status_code == 422
    assert client.post("/api/detect", files={"file": ("x.jpg", b"", "image/jpeg")}).status_code == 422
    ok, png = cv2.imencode(".png", (255 * (cv2.getGaussianKernel(64, 10) @ cv2.getGaussianKernel(64, 10).T)).astype("uint8"))
    r = client.post("/api/detect", files={"file": ("x.png", png.tobytes(), "image/png")}, data={"method": "nope"})
    assert r.status_code == 422
    assert client.post("/api/detect_example", data={"name": "../app.py"}).status_code == 404
    assert client.post("/api/detect").status_code == 422
