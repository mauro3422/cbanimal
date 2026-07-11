from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[5]
MANIFEST_PATH = ROOT / "assets/concepts/chatgpt-fox/blender/chatgpt_fox_proxy_v2.json"
CONFIG_PATH = ROOT / "client/src/game/config/localPlayerConfig.ts"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(record: dict, label: str) -> dict:
    path = ROOT / record["path"]
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    actual_bytes = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_bytes != int(record["bytes"]):
        raise RuntimeError(
            f"{label} byte mismatch: expected={record['bytes']} actual={actual_bytes}"
        )
    if actual_sha256 != record["sha256"]:
        raise RuntimeError(
            f"{label} SHA-256 mismatch: expected={record['sha256']} actual={actual_sha256}"
        )
    return {
        "path": record["path"],
        "bytes": actual_bytes,
        "sha256": actual_sha256,
    }


def parse_glb(path: Path) -> dict:
    data = path.read_bytes()
    magic, version, total_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total_length != len(data):
        raise RuntimeError(
            f"Invalid GLB header: magic={magic!r} version={version} "
            f"declared={total_length} actual={len(data)}"
        )
    json_length, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise RuntimeError(f"Unexpected first GLB chunk type: {json_type!r}")
    payload = json.loads(data[20 : 20 + json_length].decode("utf-8"))
    return {
        "bytes": len(data),
        "nodes": len(payload.get("nodes", [])),
        "meshes": len(payload.get("meshes", [])),
        "materials": len(payload.get("materials", [])),
        "skins": len(payload.get("skins", [])),
        "animations": [item.get("name") for item in payload.get("animations", [])],
        "scenes": len(payload.get("scenes", [])),
    }


def main() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Proxy v2 manifest is missing: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("stage") != "proxy_v2_integrated_and_validated":
        raise RuntimeError(f"Unexpected checkpoint stage: {manifest.get('stage')}")

    verified_files = {
        "blend": verify_file(manifest["outputs"]["blend"], "active blend"),
        "glb": verify_file(manifest["outputs"]["glb"], "active GLB"),
        "animationValidation": verify_file(
            manifest["rig"]["animationValidation"],
            "animation validation",
        ),
        "baselineMetrics": verify_file(
            manifest["silhouette"]["metrics"]["baseline"],
            "baseline silhouette metrics",
        ),
        "v2Metrics": verify_file(
            manifest["silhouette"]["metrics"]["v2"],
            "v2 silhouette metrics",
        ),
        "gameScreenshot": verify_file(
            manifest["gameSmoke"]["screenshot"],
            "game smoke screenshot",
        ),
        "gameSmokeRecord": verify_file(
            manifest["gameSmoke"]["record"],
            "game smoke record",
        ),
    }
    for name, record in manifest["reviews"].items():
        verified_files[f"review:{name}"] = verify_file(record, f"review {name}")

    glb_path = ROOT / manifest["outputs"]["glb"]["path"]
    actual_glb = parse_glb(glb_path)
    if actual_glb != manifest["glb"]:
        raise RuntimeError(
            "GLB structure mismatch:\n"
            f"expected={json.dumps(manifest['glb'], sort_keys=True)}\n"
            f"actual={json.dumps(actual_glb, sort_keys=True)}"
        )

    expected_actions = ["idle", "sitting", "walking", "wave"]
    if sorted(name for name in actual_glb["animations"] if name) != expected_actions:
        raise RuntimeError(f"Unexpected GLB action set: {actual_glb['animations']}")
    if manifest["model"]["warnings"]:
        raise RuntimeError(f"Model checkpoint contains warnings: {manifest['model']['warnings']}")
    if manifest["silhouette"]["relativeErrorReduction"] < 0.50:
        raise RuntimeError(
            f"Silhouette reduction regressed: {manifest['silhouette']['relativeErrorReduction']}"
        )
    if manifest["rig"]["minimumValidatedZ"] < -0.03:
        raise RuntimeError(
            f"Animation floor tolerance regressed: {manifest['rig']['minimumValidatedZ']}"
        )
    if manifest["gameSmoke"]["pageStatus"] != 200 or manifest["gameSmoke"]["modelStatus"] != 200:
        raise RuntimeError(f"Game smoke status regressed: {manifest['gameSmoke']}")
    if manifest["gameSmoke"]["contentType"] != "model/gltf-binary":
        raise RuntimeError(f"Unexpected game model content type: {manifest['gameSmoke']['contentType']}")
    if manifest["gameSmoke"]["servedBytes"] != actual_glb["bytes"]:
        raise RuntimeError("Served model byte count does not match the GLB")
    pixel_evidence = manifest["gameSmoke"]["pixelEvidence"]
    if pixel_evidence["tealPixels"] < 5000 or pixel_evidence["cyanPixels"] < 250:
        raise RuntimeError(f"Insufficient fox pixels in game smoke: {pixel_evidence}")
    if pixel_evidence["placeholderPinkPixels"] != 0:
        raise RuntimeError(f"Placeholder pixels remain visible: {pixel_evidence}")

    config_text = CONFIG_PATH.read_text(encoding="utf-8")
    if '"/models/chatgpt-fox-proxy-v2.glb"' not in config_text:
        raise RuntimeError("localPlayerConfig no longer points to proxy v2")
    for rollback_key, rollback_path in manifest["rollback"].items():
        path = ROOT / rollback_path
        if not path.is_file():
            raise FileNotFoundError(f"Rollback {rollback_key} is missing: {path}")

    print(
        json.dumps(
            {
                "ok": True,
                "stage": manifest["stage"],
                "verifiedFiles": len(verified_files),
                "glb": actual_glb,
                "silhouetteErrorReduction": manifest["silhouette"]["relativeErrorReduction"],
                "minimumValidatedZ": manifest["rig"]["minimumValidatedZ"],
                "gamePixelEvidence": pixel_evidence,
                "rollback": manifest["rollback"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
