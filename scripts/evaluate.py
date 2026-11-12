#!/usr/bin/env python3
"""Angle error of the ported detectors on synthetic images with a known angle.

    python scripts/evaluate.py                    # 30 straight + 30 curved lines, seed 1000
    python scripts/evaluate.py --n 50 --seed 7 --out /tmp/metrics.json

Writes demo/eval_metrics.json by default. Nothing is tuned on this set: the
detectors keep the parameters of the MATLAB code. The port was debugged on
images with seeds 2023 to 2042 (holdtheline.synthetic.dataset default); the
evaluation uses seeds 1000 to 1059, which were not looked at.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from holdtheline import METHODS  # noqa: E402
from holdtheline.synthetic import dataset  # noqa: E402

SOURCES = {
    "quantization": "matlab/simulink_blocks/rgbtoimg.m, findcolor.m, findsound.m",
    "middle_edge": "matlab/approaches/draw_line__1_.m",
    "radon": "matlab/approaches/find_line_radon.m",
}


def summarize(errors, n_total):
    e = np.array(errors, dtype=float)
    out = {"n_images": n_total, "n_detected": int(len(e)),
           "detection_rate": round(len(e) / n_total, 3) if n_total else None}
    if len(e):
        out.update({"mae_deg": round(float(e.mean()), 2), "median_ae_deg": round(float(np.median(e)), 2),
                    "p90_ae_deg": round(float(np.percentile(e, 90)), 2),
                    "share_within_5deg": round(float((e <= 5).mean()), 3)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=30, help="images per subset (straight, curved)")
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--out", default=os.path.join(ROOT, "demo", "eval_metrics.json"))
    args = ap.parse_args()

    samples = dataset(args.n, args.seed)
    results = {}
    t_start = time.perf_counter()
    for name, fn in METHODS.items():
        errs = {"straight": [], "curved": []}
        times = []
        for s in samples:
            t0 = time.perf_counter()
            d = fn(s.image)
            times.append(time.perf_counter() - t0)
            if d.found:
                errs[s.kind].append(abs(d.angle_deg - s.angle_deg))
        results[name] = {
            "source": SOURCES[name],
            "all": summarize(errs["straight"] + errs["curved"], len(samples)),
            "straight": summarize(errs["straight"], args.n),
            "curved": summarize(errs["curved"], args.n),
            "mean_time_ms": round(1000 * float(np.mean(times)), 1),
        }
        print(f"{name:13s} detected {results[name]['all']['n_detected']}/{len(samples)}  "
              f"MAE {results[name]['all'].get('mae_deg')} deg  "
              f"(straight {results[name]['straight'].get('mae_deg')}, curved {results[name]['curved'].get('mae_deg')})  "
              f"{results[name]['mean_time_ms']} ms/image")

    metrics = {
        "description": "Absolute angle error (degrees) between the detected line and the reference line, "
                       "on synthetic ground images. The MAE is computed over the images where the method "
                       "returned a line; detection_rate gives the share of images where it did.",
        "dataset": {
            "generator": "holdtheline/synthetic.py (dataset)",
            "n_straight": args.n, "n_curved": args.n, "seed": args.seed, "size": "640x480",
            "content": "asphalt / concrete / carpet textures, white or yellow line with rough edges, "
                       "perspective narrowing, lighting gradient, optional shadow, blur, noise, JPEG q85; "
                       "angles uniform in [-35, 35] degrees",
            "reference_angle": "least-squares straight fit of the true centre line over all rows "
                               "(exact drawing angle for straight lines)",
            "synthetic": True,
            "note": "the port was debugged on seeds 2023-2042, disjoint from the evaluation seeds",
        },
        "methods": results,
        "command": f"python scripts/evaluate.py --n {args.n} --seed {args.seed}",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "machine": f"{platform.machine()} / {platform.system()} / Python {platform.python_version()}",
        "duration_s": round(time.perf_counter() - t_start, 1),
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
        f.write("\n")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
