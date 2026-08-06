from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request

import numpy as np
from PIL import Image, ImageDraw
import websocket

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
OUTPUT_PATH = BLENDER_DIR / "proxy-v5-walk-visual-smoke.json"
FRAME_DIR = BLENDER_DIR / "proxy-v5-walk-visual-frames"
CONTACT_PATH = BLENDER_DIR / "proxy-v5-review/walk-gameplay-camera-contact.jpg"
DEFAULT_CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
# Eight samples span one calibrated 0.341 s gameplay cycle.
CAPTURE_INTERVAL = 0.043
CAPTURE_COUNT = 8


def fetch_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": "CBAnimalWalkVisualSmoke/1.0"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


class CDPClient:
    def __init__(self, websocket_url: str) -> None:
        self.socket = websocket.create_connection(websocket_url, timeout=1)
        self.next_id = 1
        self.events: list[dict] = []

    def close(self) -> None:
        self.socket.close()

    def send(self, method: str, params: dict | None = None, timeout: float = 8.0) -> dict:
        message_id = self.next_id
        self.next_id += 1
        self.socket.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self._receive_once()
            if message is None:
                continue
            if message.get("id") == message_id:
                if "error" in message:
                    raise RuntimeError(f"CDP {method} failed: {message['error']}")
                return message.get("result", {})
            self.events.append(message)
        raise TimeoutError(f"Timed out waiting for CDP response to {method}")

    def pump(self, duration: float) -> None:
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            message = self._receive_once()
            if message is not None:
                self.events.append(message)

    def _receive_once(self) -> dict | None:
        try:
            return json.loads(self.socket.recv())
        except websocket.WebSocketTimeoutException:
            return None


def wait_for_page_target(debug_port: int, timeout: float = 15.0) -> dict:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            targets = fetch_json(f"http://127.0.0.1:{debug_port}/json/list")
            for target in targets:
                if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                    return target
        except Exception as error:
            last_error = error
        time.sleep(0.15)
    raise TimeoutError(f"Chrome DevTools target did not become ready: {last_error}")


def console_text(event: dict) -> str:
    if event.get("method") != "Runtime.consoleAPICalled":
        return ""
    parts = []
    for argument in event.get("params", {}).get("args", []):
        if "value" in argument:
            parts.append(str(argument["value"]))
        elif argument.get("description"):
            parts.append(argument["description"])
    return " ".join(parts)


def wait_for_animation(client: CDPClient, animation: str, timeout: float = 15.0) -> None:
    marker = f"Animación activa: {animation}"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        client.pump(0.15)
        if any(marker in console_text(event) for event in client.events):
            return
    raise RuntimeError(f"Browser never reported active animation: {animation}")


def dispatch_w(client: CDPClient, event_type: str) -> None:
    client.send(
        "Input.dispatchKeyEvent",
        {
            "type": event_type,
            "key": "w",
            "code": "KeyW",
            "windowsVirtualKeyCode": 87,
            "nativeVirtualKeyCode": 87,
        },
    )


def capture_frame(client: CDPClient, path: Path) -> None:
    result = client.send(
        "Page.captureScreenshot",
        {"format": "png", "fromSurface": True, "captureBeyondViewport": False},
        timeout=15.0,
    )
    encoded = result.get("data")
    if not encoded:
        raise RuntimeError("Chrome returned no screenshot data")
    path.write_bytes(base64.b64decode(encoded))


def fox_mask(image: Image.Image) -> np.ndarray:
    pixels = np.asarray(image.convert("RGB"))
    red = pixels[:, :, 0].astype(np.int32)
    green = pixels[:, :, 1].astype(np.int32)
    blue = pixels[:, :, 2].astype(np.int32)
    teal = (
        (green > 65)
        & (blue > 65)
        & (green > red * 1.25)
        & (blue > red * 1.25)
        & (np.abs(green - blue) < 90)
    )
    cyan = (green > 120) & (blue > 130) & (red < 120)
    mask = teal | cyan

    height, width = mask.shape
    x0, x1 = int(width * 0.34), int(width * 0.66)
    y0, y1 = int(height * 0.16), int(height * 0.94)
    restricted = np.zeros_like(mask)
    restricted[y0:y1, x0:x1] = mask[y0:y1, x0:x1]
    return restricted


def mask_bounds(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(mask)
    if len(xs) < 500:
        raise RuntimeError(f"Fox mask too small: {len(xs)} pixels")
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def align_mask(mask: np.ndarray, bounds: tuple[int, int, int, int], canvas_size: tuple[int, int] = (320, 360)) -> np.ndarray:
    x0, y0, x1, y1 = bounds
    crop = mask[y0:y1, x0:x1]
    canvas_width, canvas_height = canvas_size
    canvas = np.zeros((canvas_height, canvas_width), dtype=bool)
    height, width = crop.shape
    if width > canvas_width or height > canvas_height:
        raise RuntimeError(f"Fox crop exceeds analysis canvas: {(width, height)}")
    left = (canvas_width - width) // 2
    top = (canvas_height - height) // 2
    canvas[top : top + height, left : left + width] = crop
    return canvas


def analyze_frames(paths: list[Path]) -> dict:
    images = [Image.open(path).convert("RGB") for path in paths]
    masks = [fox_mask(image) for image in images]
    bounds = [mask_bounds(mask) for mask in masks]
    aligned = [align_mask(mask, box) for mask, box in zip(masks, bounds, strict=True)]

    union = np.logical_or.reduce(aligned)
    ys, xs = np.nonzero(union)
    top, bottom = int(ys.min()), int(ys.max()) + 1

    # The fox uses dark, white, cyan, and teal materials. The color mask intentionally
    # isolates cyan/teal, which produces two vertical components at gameplay distance:
    # head/ears above and legs below. Detect the large empty gap and analyze the lower
    # component directly so the test measures upper-leg motion rather than empty torso rows.
    row_counts = union.sum(axis=1)
    active_rows = np.flatnonzero(row_counts > 0)
    gaps = np.diff(active_rows)
    if gaps.size == 0:
        raise RuntimeError("Gameplay fox mask does not contain enough vertical structure")
    largest_gap_index = int(np.argmax(gaps))
    largest_gap = int(gaps[largest_gap_index])
    leg_top = int(active_rows[largest_gap_index + 1])
    leg_bottom = int(active_rows[-1]) + 1
    leg_height = leg_bottom - leg_top
    if largest_gap < 20 or leg_height < 55:
        raise RuntimeError(
            f"Could not isolate the colored leg silhouette: gap={largest_gap}, legHeight={leg_height}"
        )

    upper_leg_end = leg_top + int(leg_height * 0.55)
    lower_leg_start = upper_leg_end

    comparison_pairs = [
        (first, second)
        for first in range(len(aligned))
        for second in range(first + 1, len(aligned))
    ]
    pair_metrics = []
    for first, second in comparison_pairs:
        difference = np.logical_xor(aligned[first], aligned[second])
        upper_leg_xor = int(difference[leg_top:upper_leg_end].sum())
        lower_leg_xor = int(difference[lower_leg_start:leg_bottom].sum())
        total_xor = int(difference[top:bottom].sum())
        pair_metrics.append(
            {
                "frames": [first + 1, second + 1],
                "upperLegXorPixels": upper_leg_xor,
                "lowerLegXorPixels": lower_leg_xor,
                "totalXorPixels": total_xor,
                "upperToLowerRatio": round(upper_leg_xor / max(lower_leg_xor, 1), 4),
            }
        )

    bbox_widths = [x1 - x0 for x0, _, x1, _ in bounds]
    bbox_heights = [y1 - y0 for _, y0, _, y1 in bounds]
    foreground = [int(mask.sum()) for mask in masks]
    readable_metrics = [item for item in pair_metrics if item["upperLegXorPixels"] >= 80]
    readable_pairs = len(readable_metrics)
    maximum_upper_xor = max(item["upperLegXorPixels"] for item in pair_metrics)
    average_upper_ratio = (
        sum(item["upperToLowerRatio"] for item in readable_metrics) / max(readable_pairs, 1)
    )

    # CDP screenshots are time-based and their capture cost can alias a nominal half-cycle.
    # Compare every unique pose pair and require several independently readable thigh changes.
    if readable_pairs < 4 or maximum_upper_xor < 800:
        raise RuntimeError(f"Upper-leg silhouette still reads as static: {pair_metrics}")
    if average_upper_ratio < 0.30:
        raise RuntimeError(f"Lower legs still dominate the gameplay silhouette: {pair_metrics}")

    return {
        "frameCount": len(paths),
        "foregroundPixels": foreground,
        "boundingBoxes": [list(box) for box in bounds],
        "boundingBoxWidthRange": [min(bbox_widths), max(bbox_widths)],
        "boundingBoxHeightRange": [min(bbox_heights), max(bbox_heights)],
        "alignedUnionBounds": [int(xs.min()), top, int(xs.max()) + 1, bottom],
        "detectedVerticalGapPixels": largest_gap,
        "analysisBands": {
            "upperLeg": [leg_top, upper_leg_end],
            "lowerLeg": [lower_leg_start, leg_bottom],
        },
        "comparisonPairs": pair_metrics,
        "averageUpperToLowerRatio": round(average_upper_ratio, 4),
        "readableUpperLegPairs": readable_pairs,
        "maximumUpperLegXorPixels": maximum_upper_xor,
    }


def create_contact_sheet(paths: list[Path], output: Path) -> None:
    images = [Image.open(path).convert("RGB") for path in paths]
    width, height = images[0].size
    crop_box = (int(width * 0.31), int(height * 0.11), int(width * 0.69), int(height * 0.96))
    crops = [image.crop(crop_box) for image in images]
    tile_width, tile_height = 300, 360
    sheet = Image.new("RGB", (tile_width * 4, tile_height * 2), "white")
    draw = ImageDraw.Draw(sheet)
    for index, crop in enumerate(crops):
        crop.thumbnail((tile_width, tile_height - 24), Image.Resampling.LANCZOS)
        x = (index % 4) * tile_width + (tile_width - crop.width) // 2
        y = (index // 4) * tile_height + 22
        sheet.paste(crop, (x, y))
        draw.text(((index % 4) * tile_width + 8, (index // 4) * tile_height + 5), f"Walk sample {index + 1}", fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=88, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture the v5 walk from the actual gameplay camera")
    parser.add_argument("--base-url", default="http://127.0.0.1:4173")
    parser.add_argument("--chrome", type=Path, default=DEFAULT_CHROME)
    parser.add_argument("--debug-port", type=int, default=9224)
    args = parser.parse_args()

    if not args.chrome.is_file():
        raise FileNotFoundError(args.chrome)

    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    for old_path in FRAME_DIR.glob("walk-*.png"):
        old_path.unlink()

    page_url = args.base_url.rstrip("/") + f"/?walkVisualSmoke={time.time_ns()}"
    frame_paths = [FRAME_DIR / f"walk-{index + 1:02d}.png" for index in range(CAPTURE_COUNT)]

    with tempfile.TemporaryDirectory(prefix="cbanimal-walk-visual-") as profile:
        command = [
            str(args.chrome),
            "--headless=new",
            "--hide-scrollbars",
            "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader",
            "--ignore-gpu-blocklist",
            "--remote-allow-origins=*",
            f"--remote-debugging-port={args.debug_port}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1280,720",
            page_url,
        ]
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        client: CDPClient | None = None
        try:
            target = wait_for_page_target(args.debug_port)
            client = CDPClient(target["webSocketDebuggerUrl"])
            client.send("Runtime.enable")
            client.send("Page.enable")
            client.send("Page.bringToFront")
            wait_for_animation(client, "idle")

            dispatch_w(client, "keyDown")
            wait_for_animation(client, "walking")
            client.pump(0.08)
            for path in frame_paths:
                capture_frame(client, path)
                client.pump(CAPTURE_INTERVAL)
            dispatch_w(client, "keyUp")
            client.pump(0.25)

            create_contact_sheet(frame_paths, CONTACT_PATH)
            visual = analyze_frames(frame_paths)
            evidence = {
                "stage": "proxy_v5_gameplay_walk_visual_smoke_verified",
                "baseUrl": args.base_url.rstrip("/"),
                "capture": {
                    "viewport": [1280, 720],
                    "intervalSeconds": CAPTURE_INTERVAL,
                    "frames": [str(path.relative_to(ROOT)).replace("\\", "/") for path in frame_paths],
                    "contactSheet": str(CONTACT_PATH.relative_to(ROOT)).replace("\\", "/"),
                },
                "visualAnalysis": visual,
                "consoleAnimations": [console_text(event) for event in client.events if "Animación activa:" in console_text(event)],
            }
            OUTPUT_PATH.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(evidence, indent=2, ensure_ascii=False))
        finally:
            if client is not None:
                try:
                    dispatch_w(client, "keyUp")
                except Exception:
                    pass
                client.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
