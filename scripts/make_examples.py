#!/usr/bin/env python3
"""Build the clickable examples of the web demo (demo/static/examples/).

    python scripts/make_examples.py

Three images come from the repository (the team's indoor test floor, cropped
from the report figure report/latex/main/pre_process.png; a road-marking photo
from archive/gaetan/ligne.jpg; the team's synthetic test image
archive/gaetan/45degre.jpeg). Three are synthetic, drawn by
holdtheline/synthetic.py with seeds outside the evaluation range, so their
reference angle is known.
"""
from __future__ import annotations

import json
import os
import sys

import cv2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from holdtheline.synthetic import make_sample  # noqa: E402

OUT = os.path.join(ROOT, "demo", "static", "examples")


def save(name, bgr, width=None):
    if width and bgr.shape[1] > width:
        bgr = cv2.resize(bgr, (width, int(round(bgr.shape[0] * width / bgr.shape[1]))), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(OUT, name), bgr, [cv2.IMWRITE_JPEG_QUALITY, 88])


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    items = []
    fig = cv2.imread(os.path.join(ROOT, "report/latex/main/pre_process.png"))
    save("team_floor_tape.jpg", fig[124:428, 100:492])
    items.append({"file": "team_floor_tape.jpg", "title": "Team test floor (curved tape)",
                  "source": "report/latex/main/pre_process.png (input photo, cropped)",
                  "synthetic": False, "reference_angle_deg": None})
    save("team_test_45.jpg", cv2.imread(os.path.join(ROOT, "archive/gaetan/45degre.jpeg")))
    items.append({"file": "team_test_45.jpg", "title": "Team synthetic test image",
                  "source": "archive/gaetan/45degre.jpeg (drawn by the team)",
                  "synthetic": True, "reference_angle_deg": None})
    for seed, curved, title in [(5004, False, "Synthetic: yellow line on concrete"),
                                (5002, True, "Synthetic: curved line on asphalt"),
                                (5007, False, "Synthetic: carpet, strong turn")]:
        s = make_sample(seed, curved)
        name = f"synthetic_{seed}{'_curved' if curved else ''}.jpg"
        save(name, cv2.cvtColor(s.image, cv2.COLOR_RGB2BGR))
        items.append({"file": name, "title": title,
                      "source": f"holdtheline/synthetic.py, make_sample({seed}, curved={curved})",
                      "synthetic": True, "reference_angle_deg": round(s.angle_deg, 1)})
    with open(os.path.join(OUT, "examples.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
        f.write("\n")
    print(f"Wrote {len(items)} examples to {OUT}")


if __name__ == "__main__":
    main()
