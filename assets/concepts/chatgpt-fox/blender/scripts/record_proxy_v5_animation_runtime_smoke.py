from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import time
import urllib.request

import websocket

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
GLB_PATH = ROOT / "client/public/models/chatgpt-fox-proxy-v5.glb"
OUTPUT_PATH = BLENDER_DIR / "proxy-v5-animation-runtime-smoke.json"
DEFAULT_CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
EXPECTED_CLIPS = ["angry", "idle", "laugh", "sitting", "sleep", "walking", "wave"]
EXPECTED_EMOTES = ["wave", "laugh", "angry", "sleep"]


def parse_glb_animations(path: Path) -> list[str]:
    data = path.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise RuntimeError("Invalid proxy v5 GLB header")
    json_length, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise RuntimeError("Proxy v5 GLB JSON chunk is missing")
    payload = json.loads(data[20 : 20 + json_length].decode("utf-8"))
    return sorted(
        entry.get("name")
        for entry in payload.get("animations", [])
        if entry.get("name")
    )


def fetch_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": "CBAnimalAnimationSmoke/1.0"})
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
        self.socket.send(
            json.dumps(
                {
                    "id": message_id,
                    "method": method,
                    "params": params or {},
                }
            )
        )
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


def console_argument_text(argument: dict) -> str:
    if "value" in argument:
        value = argument["value"]
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    preview = argument.get("preview") or {}
    properties = preview.get("properties") or []
    if properties:
        return json.dumps(
            [prop.get("value") for prop in properties if prop.get("value") is not None],
            ensure_ascii=False,
        )
    return argument.get("description") or argument.get("type") or ""


def collect_console(events: list[dict]) -> list[dict]:
    records: list[dict] = []
    for event in events:
        if event.get("method") == "Runtime.consoleAPICalled":
            params = event.get("params", {})
            records.append(
                {
                    "type": params.get("type"),
                    "text": " ".join(
                        console_argument_text(argument)
                        for argument in params.get("args", [])
                    ).strip(),
                    "timestamp": params.get("timestamp"),
                }
            )
        elif event.get("method") == "Log.entryAdded":
            entry = event.get("params", {}).get("entry", {})
            records.append(
                {
                    "type": entry.get("level"),
                    "text": entry.get("text", ""),
                    "timestamp": entry.get("timestamp"),
                }
            )
    return records


def active_animation_names(console_records: list[dict]) -> list[str]:
    prefix = "Animación activa:"
    names: list[str] = []
    for record in console_records:
        text = record.get("text", "")
        if prefix not in text:
            continue
        name = text.split(prefix, 1)[1].strip().split()[0]
        if name:
            names.append(name)
    return names


def wait_for_page_target(debug_port: int, timeout: float = 15.0) -> dict:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            targets = fetch_json(f"http://127.0.0.1:{debug_port}/json/list")
            for target in targets:
                if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                    return target
        except Exception as error:  # Chrome can reject while it is still starting.
            last_error = error
        time.sleep(0.15)
    raise TimeoutError(f"Chrome DevTools target did not become ready: {last_error}")


def wait_for_animation_log(client: CDPClient, name: str, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        client.pump(0.2)
        if name in active_animation_names(collect_console(client.events)):
            return
    raise RuntimeError(f"Browser never reported active animation: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify CBAnimal v5 animation transitions in Chrome")
    parser.add_argument("--base-url", default="http://127.0.0.1:4173")
    parser.add_argument("--chrome", type=Path, default=DEFAULT_CHROME)
    parser.add_argument("--debug-port", type=int, default=9223)
    args = parser.parse_args()

    if not args.chrome.is_file():
        raise FileNotFoundError(f"Chrome executable not found: {args.chrome}")
    if not GLB_PATH.is_file():
        raise FileNotFoundError(GLB_PATH)

    clips = parse_glb_animations(GLB_PATH)
    if clips != EXPECTED_CLIPS:
        raise RuntimeError(f"Unexpected GLB animation contract: {clips}")

    page_url = args.base_url.rstrip("/") + f"/?animationSmoke={time.time_ns()}"
    with tempfile.TemporaryDirectory(prefix="cbanimal-animation-smoke-") as profile:
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
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        client: CDPClient | None = None
        try:
            target = wait_for_page_target(args.debug_port)
            client = CDPClient(target["webSocketDebuggerUrl"])
            client.send("Runtime.enable")
            client.send("Log.enable")
            client.send("Page.enable")
            client.send("Page.bringToFront")

            wait_for_animation_log(client, "idle", timeout=15.0)

            client.send(
                "Input.dispatchKeyEvent",
                {
                    "type": "keyDown",
                    "key": "w",
                    "code": "KeyW",
                    "windowsVirtualKeyCode": 87,
                    "nativeVirtualKeyCode": 87,
                },
            )
            wait_for_animation_log(client, "walking")
            client.pump(0.7)
            client.send(
                "Input.dispatchKeyEvent",
                {
                    "type": "keyUp",
                    "key": "w",
                    "code": "KeyW",
                    "windowsVirtualKeyCode": 87,
                    "nativeVirtualKeyCode": 87,
                },
            )
            client.pump(0.8)

            for emote_name in EXPECTED_EMOTES:
                result = client.send(
                    "Runtime.evaluate",
                    {
                        "expression": (
                            "(() => {"
                            f"const button = document.querySelector('[data-emote-id=\"{emote_name}\"]');"
                            "if (!(button instanceof HTMLButtonElement)) return false;"
                            "button.click(); return true;"
                            "})()"
                        ),
                        "returnByValue": True,
                    },
                )
                clicked = result.get("result", {}).get("value")
                if clicked is not True:
                    raise RuntimeError(f"Could not click emote button: {emote_name}")
                wait_for_animation_log(client, emote_name)
                client.pump(0.35)

            client.pump(3.4)
            console_records = collect_console(client.events)
            active_names = active_animation_names(console_records)
            errors = [
                record
                for record in console_records
                if any(
                    marker in record.get("text", "")
                    for marker in (
                        "Animación no encontrada",
                        "No hay animación disponible",
                        "no existe; se usará",
                        "No se pudo cargar el modelo",
                    )
                )
            ]
            if errors:
                raise RuntimeError(f"Animation runtime emitted errors or fallbacks: {errors}")

            required_observed = {"idle", "walking", *EXPECTED_EMOTES}
            missing_observed = sorted(required_observed.difference(active_names))
            if missing_observed:
                raise RuntimeError(
                    f"Browser did not activate all required animations: {missing_observed}; "
                    f"observed={active_names}"
                )

            first_idle = active_names.index("idle")
            walking_index = active_names.index("walking", first_idle + 1)
            idle_after_walking = next(
                (index for index in range(walking_index + 1, len(active_names)) if active_names[index] == "idle"),
                None,
            )
            if idle_after_walking is None:
                raise RuntimeError(f"Locomotion did not return to idle: {active_names}")

            evidence = {
                "stage": "proxy_v5_animation_runtime_smoke_verified",
                "baseUrl": args.base_url.rstrip("/"),
                "glb": {
                    "path": str(GLB_PATH.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": GLB_PATH.stat().st_size,
                    "animations": clips,
                },
                "gameContract": {
                    "locomotion": ["idle", "walking", "sitting"],
                    "emotes": EXPECTED_EMOTES,
                    "looping": ["idle", "walking"],
                    "oneShotClamp": ["sitting", *EXPECTED_EMOTES],
                },
                "observedActiveSequence": active_names,
                "locomotionSequenceVerified": ["idle", "walking", "idle"],
                "emotesVerified": EXPECTED_EMOTES,
                "fallbackWarnings": errors,
                "console": console_records,
                "chrome": {
                    "command": command[:-2] + ["--user-data-dir=<temporary>", page_url],
                    "pid": process.pid,
                },
            }
            OUTPUT_PATH.write_text(
                json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(evidence, indent=2, ensure_ascii=False))
        finally:
            if client is not None:
                client.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
