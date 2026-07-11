from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[5]
SCREENSHOT_PATH = ROOT / "assets/concepts/chatgpt-fox/blender/game_smoke_proxy_v2.png"
GLB_PATH = ROOT / "client/public/models/chatgpt-fox-proxy-v2.glb"
MANIFEST_PATH = ROOT / "assets/concepts/chatgpt-fox/blender/chatgpt_fox_proxy_v2.json"
SMOKE_PATH = ROOT / "assets/concepts/chatgpt-fox/blender/proxy-v2-game-smoke.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_info(path: Path) -> dict:
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def analyze_screenshot(path: Path) -> dict:
    image = Image.open(path).convert("RGB")
    pixels = np.asarray(image)
    height, width, _ = pixels.shape
    x0, x1 = int(width * 0.30), int(width * 0.70)
    y0, y1 = int(height * 0.15), int(height * 0.92)
    crop = pixels[y0:y1, x0:x1]
    red = crop[:, :, 0].astype(np.int32)
    green = crop[:, :, 1].astype(np.int32)
    blue = crop[:, :, 2].astype(np.int32)

    teal = (
        (green > 65)
        & (blue > 65)
        & (green > red * 1.25)
        & (blue > red * 1.25)
        & (np.abs(green - blue) < 90)
    )
    cyan = (green > 120) & (blue > 130) & (red < 120)
    placeholder_pink = (
        (red > 150)
        & (green > 65)
        & (green < 190)
        & (blue > 65)
        & (blue < 190)
        & (red > green * 1.22)
        & (red > blue * 1.22)
    )
    return {
        "width": width,
        "height": height,
        "analysisCrop": [x0, y0, x1, y1],
        "tealPixels": int(teal.sum()),
        "cyanPixels": int(cyan.sum()),
        "placeholderPinkPixels": int(placeholder_pink.sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Record the verified browser smoke result for proxy v2.")
    parser.add_argument("--page-status", type=int, default=200)
    parser.add_argument("--model-status", type=int, default=200)
    parser.add_argument("--content-type", default="model/gltf-binary")
    parser.add_argument("--served-bytes", type=int, default=173376)
    args = parser.parse_args()

    required = [SCREENSHOT_PATH, GLB_PATH, MANIFEST_PATH]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Game smoke inputs are missing: {missing}")

    screenshot = analyze_screenshot(SCREENSHOT_PATH)
    if args.page_status != 200 or args.model_status != 200:
        raise RuntimeError(f"Unexpected HTTP statuses: page={args.page_status} model={args.model_status}")
    if args.content_type != "model/gltf-binary":
        raise RuntimeError(f"Unexpected model content type: {args.content_type}")
    if args.served_bytes != GLB_PATH.stat().st_size:
        raise RuntimeError(
            f"Served GLB size mismatch: served={args.served_bytes} file={GLB_PATH.stat().st_size}"
        )
    if screenshot["tealPixels"] < 5000 or screenshot["cyanPixels"] < 250:
        raise RuntimeError(f"Fox colors were not sufficiently visible in screenshot: {screenshot}")
    if screenshot["placeholderPinkPixels"] != 0:
        raise RuntimeError(f"Placeholder pink pixels remain visible: {screenshot}")

    smoke = {
        "pageStatus": args.page_status,
        "modelStatus": args.model_status,
        "contentType": args.content_type,
        "servedBytes": args.served_bytes,
        "screenshot": file_info(SCREENSHOT_PATH),
        "pixelEvidence": screenshot,
    }
    SMOKE_PATH.write_text(json.dumps(smoke, indent=2) + "\n", encoding="utf-8")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["gameSmoke"] = {
        **smoke,
        "record": file_info(SMOKE_PATH),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "smoke": file_info(SMOKE_PATH),
                "manifest": file_info(MANIFEST_PATH),
                "evidence": smoke,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
