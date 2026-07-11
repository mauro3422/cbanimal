from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[5]
SAMPLES = [0.04, 0.08, 0.12, 0.16, 0.22, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.96]


def foreground_mask(image: Image.Image, reference: bool) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"), dtype=np.int16)
    if reference:
        background = np.array([255, 255, 255], dtype=np.int16)
        distance = np.linalg.norm(rgb - background, axis=2)
        mask = distance > 28
    else:
        corners = np.array(
            [rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]], dtype=np.int16
        )
        background = np.median(corners, axis=0)
        distance = np.linalg.norm(rgb - background, axis=2)
        mask = distance > 22

    padded = np.pad(mask, 1, mode="constant")
    neighbors = np.zeros_like(mask, dtype=np.uint8)
    for dy in range(3):
        for dx in range(3):
            neighbors += padded[dy : dy + mask.shape[0], dx : dx + mask.shape[1]]
    return mask & (neighbors >= 3)


def analyze(path: Path, reference: bool) -> dict:
    image = Image.open(path).convert("RGB")
    mask = foreground_mask(image, reference)
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise RuntimeError(f"No foreground found in {path}")
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    crop = mask[y0 : y1 + 1, x0 : x1 + 1]
    height, width = crop.shape

    widths = {}
    centers = {}
    for fraction in SAMPLES:
        row = min(height - 1, max(0, int(round(fraction * (height - 1)))))
        band0 = max(0, row - 2)
        band1 = min(height, row + 3)
        band = crop[band0:band1].any(axis=0)
        columns = np.flatnonzero(band)
        if len(columns):
            widths[f"{fraction:.2f}"] = round((columns.max() - columns.min() + 1) / width, 4)
            centers[f"{fraction:.2f}"] = round(((columns.min() + columns.max()) * 0.5) / width, 4)
        else:
            widths[f"{fraction:.2f}"] = 0.0
            centers[f"{fraction:.2f}"] = None

    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "image_size": [image.width, image.height],
        "bbox": [x0, y0, x1 + 1, y1 + 1],
        "bbox_size": [width, height],
        "bbox_aspect_width_over_height": round(width / height, 4),
        "foreground_area_ratio_in_bbox": round(float(crop.mean()), 4),
        "centroid_normalized": [
            round(float((xs.mean() - x0) / width), 4),
            round(float((ys.mean() - y0) / height), 4),
        ],
        "width_profile": widths,
        "center_profile": centers,
    }


def profile_difference(reference: dict, model: dict) -> dict:
    diffs = {}
    absolute = []
    for key in reference["width_profile"]:
        delta = model["width_profile"][key] - reference["width_profile"][key]
        diffs[key] = round(delta, 4)
        absolute.append(abs(delta))
    center_diffs = []
    for key, ref_center in reference["center_profile"].items():
        model_center = model["center_profile"][key]
        if ref_center is not None and model_center is not None:
            center_diffs.append(abs(model_center - ref_center))
    return {
        "model_minus_reference_width": diffs,
        "mean_absolute_width_error": round(float(np.mean(absolute)), 4),
        "mean_absolute_center_error": round(float(np.mean(center_diffs)), 4),
        "aspect_delta": round(
            model["bbox_aspect_width_over_height"] - reference["bbox_aspect_width_over_height"], 4
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Blender review silhouettes against prepared character references.")
    parser.add_argument("--prefix", default="fox-baseline-v2", help="Review-bundle filename prefix.")
    parser.add_argument("--output", help="Optional JSON output path relative to project root.")
    args = parser.parse_args()

    review_dir = ROOT / "assets/concepts/chatgpt-fox/blender/review-bundles"
    images = {
        "reference_front": ROOT / "assets/concepts/chatgpt-fox/prepared/chatgpt_fox_front.jpg",
        "reference_side": ROOT / "assets/concepts/chatgpt-fox/prepared/chatgpt_fox_side.jpg",
        "model_front": review_dir / f"{args.prefix}_front.png",
        "model_side": review_dir / f"{args.prefix}_right.png",
    }
    missing = [str(path) for path in images.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing silhouette input(s): {missing}")

    results = {
        name: analyze(path, name.startswith("reference_"))
        for name, path in images.items()
    }
    results["prefix"] = args.prefix
    results["front_comparison"] = profile_difference(results["reference_front"], results["model_front"])
    results["side_comparison"] = profile_difference(results["reference_side"], results["model_side"])
    results["combined_mean_absolute_width_error"] = round(
        (results["front_comparison"]["mean_absolute_width_error"] + results["side_comparison"]["mean_absolute_width_error"]) / 2,
        4,
    )

    payload = json.dumps(results, indent=2)
    if args.output:
        output_path = (ROOT / args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
