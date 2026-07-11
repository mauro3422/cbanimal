from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
SCREENSHOT_PATH = BLENDER_DIR / "game_smoke_proxy_v5.png"
GLB_PATH = ROOT / "client/public/models/chatgpt-fox-proxy-v5.glb"
CONFIG_PATH = ROOT / "client/src/game/config/localPlayerConfig.ts"
SMOKE_PATH = BLENDER_DIR / "proxy-v5-game-smoke.json"
DEFAULT_CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


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


def fetch(url: str) -> tuple[int, str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "CBAnimalSmoke/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, response.headers.get_content_type(), response.read()


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


def capture(chrome: Path, page_url: str) -> dict:
    if not chrome.is_file():
        raise FileNotFoundError(f"Chrome executable not found: {chrome}")
    SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_PATH.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="cbanimal-v5-chrome-") as profile:
        command = [
            str(chrome),
            "--headless=new",
            "--hide-scrollbars",
            "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader",
            "--ignore-gpu-blocklist",
            "--run-all-compositor-stages-before-draw",
            "--window-size=1280,720",
            "--virtual-time-budget=9000",
            f"--user-data-dir={profile}",
            f"--screenshot={SCREENSHOT_PATH}",
            page_url,
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=45,
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Chrome smoke failed with code {completed.returncode}: {completed.stderr[-2000:]}"
        )
    if not SCREENSHOT_PATH.is_file() or SCREENSHOT_PATH.stat().st_size < 10_000:
        raise RuntimeError("Chrome did not create a useful screenshot")
    return {
        "command": command[:-2] + ["--screenshot=<path>", page_url],
        "exitCode": completed.returncode,
        "stderrTail": completed.stderr[-1200:],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture and verify CBAnimal proxy v5 in the browser")
    parser.add_argument("--base-url", default="http://127.0.0.1:4175")
    parser.add_argument("--chrome", type=Path, default=DEFAULT_CHROME)
    args = parser.parse_args()

    required = [GLB_PATH, CONFIG_PATH]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Proxy v5 smoke inputs are missing: {missing}")
    config_text = CONFIG_PATH.read_text(encoding="utf-8")
    model_url = "/models/chatgpt-fox-proxy-v5.glb"
    if f'"{model_url}"' not in config_text:
        raise RuntimeError("Local player configuration does not point to proxy v5")

    base_url = args.base_url.rstrip("/")
    page_status, page_type, page_data = fetch(base_url + "/")
    model_status, model_type, model_data = fetch(base_url + model_url)
    if page_status != 200 or model_status != 200:
        raise RuntimeError(f"Unexpected HTTP statuses: page={page_status}, model={model_status}")
    if model_type != "model/gltf-binary":
        raise RuntimeError(f"Unexpected model content type: {model_type}")
    if len(model_data) != GLB_PATH.stat().st_size or model_data != GLB_PATH.read_bytes():
        raise RuntimeError("Served GLB bytes do not match the versioned v5 file")

    chrome = capture(args.chrome, base_url + "/")
    pixels = analyze_screenshot(SCREENSHOT_PATH)
    if pixels["tealPixels"] < 5000 or pixels["cyanPixels"] < 250:
        raise RuntimeError(f"Fox colors were not sufficiently visible: {pixels}")
    if pixels["placeholderPinkPixels"] != 0:
        raise RuntimeError(f"Placeholder pink pixels remain visible: {pixels}")

    smoke = {
        "stage": "proxy_v5_browser_smoke_verified",
        "baseUrl": base_url,
        "page": {
            "status": page_status,
            "contentType": page_type,
            "bytes": len(page_data),
        },
        "model": {
            "url": model_url,
            "status": model_status,
            "contentType": model_type,
            "servedBytes": len(model_data),
            "file": file_info(GLB_PATH),
        },
        "screenshot": file_info(SCREENSHOT_PATH),
        "pixelEvidence": pixels,
        "chrome": chrome,
    }
    SMOKE_PATH.write_text(json.dumps(smoke, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"record": file_info(SMOKE_PATH), "evidence": smoke}, indent=2))


if __name__ == "__main__":
    main()
