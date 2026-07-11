from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
MANIFEST_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v5.json"
CONFIG_PATH = ROOT / "client/src/game/config/localPlayerConfig.ts"
EXPECTED_ACTIONS = ["idle", "sitting", "walking", "wave"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_record(record: dict) -> dict:
    path = ROOT / record["path"]
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_bytes = path.stat().st_size
    actual_hash = sha256_file(path)
    if actual_bytes != record["bytes"] or actual_hash != record["sha256"]:
        raise RuntimeError(
            f"Artifact mismatch for {record['path']}: "
            f"bytes {actual_bytes}/{record['bytes']} hash {actual_hash}/{record['sha256']}"
        )
    return {"path": record["path"], "bytes": actual_bytes, "sha256": actual_hash}


def collect_records(value: Any, output: list[dict]) -> None:
    if isinstance(value, dict):
        if {"path", "bytes", "sha256"}.issubset(value):
            output.append(value)
        for nested in value.values():
            collect_records(nested, output)
    elif isinstance(value, list):
        for nested in value:
            collect_records(nested, output)


def parse_glb(path: Path) -> dict:
    data = path.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise RuntimeError("Invalid proxy v5 GLB header")
    json_length, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise RuntimeError("Proxy v5 GLB JSON chunk missing")
    payload = json.loads(data[20 : 20 + json_length].decode("utf-8"))
    return {
        "version": version,
        "bytes": len(data),
        "nodes": len(payload.get("nodes", [])),
        "meshes": len(payload.get("meshes", [])),
        "materials": len(payload.get("materials", [])),
        "skins": len(payload.get("skins", [])),
        "animations": [entry.get("name") for entry in payload.get("animations", [])],
        "scenes": len(payload.get("scenes", [])),
    }


if not MANIFEST_PATH.is_file():
    raise FileNotFoundError(MANIFEST_PATH)
manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
if manifest.get("stage") != "hybrid_proxy_v5_integrated_and_verified":
    raise RuntimeError(f"Unexpected proxy v5 stage: {manifest.get('stage')}")

records: list[dict] = []
collect_records(manifest, records)
unique_records = {record["path"]: record for record in records}
verified = [verify_record(record) for record in unique_records.values()]

expected_geometry = {
    "objects": 47,
    "mesh_objects": 47,
    "vertices": 994,
    "edges": 2306,
    "polygons": 1404,
    "triangles": 1780,
}
if manifest["construction"]["geometry"] != expected_geometry:
    raise RuntimeError(f"Unexpected proxy v5 geometry: {manifest['construction']['geometry']}")
if manifest["construction"]["warnings"]:
    raise RuntimeError("Proxy v5 geometry warnings are not empty")
if manifest["construction"]["deformingMeshes"] != {
    "MDL_V5_BODY": ["pelvis", "spine", "chest", "neck"],
    "MDL_V5_TAIL_ROOT": ["pelvis", "tail.01"],
}:
    raise RuntimeError("Proxy v5 deforming-mesh declaration changed")

structure = parse_glb(ROOT / manifest["export"]["file"]["path"])
if structure != manifest["export"]["structure"]:
    raise RuntimeError(f"GLB structure mismatch: {structure}")
if structure != {
    "version": 2,
    "bytes": 189924,
    "nodes": 72,
    "meshes": 47,
    "materials": 4,
    "skins": 1,
    "animations": EXPECTED_ACTIONS,
    "scenes": 1,
}:
    raise RuntimeError(f"Unexpected proxy v5 GLB structure: {structure}")

validation_path = ROOT / manifest["animations"]["validation"]["path"]
validation = json.loads(validation_path.read_text(encoding="utf-8"))
if validation.get("stage") != "proxy_v5_animations_and_deformation_validated":
    raise RuntimeError("Proxy v5 deformation validation stage is missing")
if validation.get("minimumValidatedZ", -1.0) < -0.035:
    raise RuntimeError("Proxy v5 floor penetration exceeds tolerance")
if sorted(validation.get("actions", [])) != sorted(["idle", "walking", "sitting", "wave"]):
    raise RuntimeError("Proxy v5 validated action names changed")
for object_name in ("MDL_V5_BODY", "MDL_V5_TAIL_ROOT"):
    if object_name not in validation.get("deformingObjects", {}):
        raise RuntimeError(f"Missing deformation validation for {object_name}")

smoke_path = ROOT / manifest["integration"]["browserSmoke"]["record"]["path"]
smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
if smoke.get("stage") != "proxy_v5_browser_smoke_verified":
    raise RuntimeError("Proxy v5 browser smoke stage is missing")
if smoke["page"]["status"] != 200 or smoke["model"]["status"] != 200:
    raise RuntimeError("Proxy v5 HTTP smoke failed")
if smoke["model"]["contentType"] != "model/gltf-binary":
    raise RuntimeError("Proxy v5 GLB MIME type changed")
if smoke["model"]["servedBytes"] != structure["bytes"]:
    raise RuntimeError("Proxy v5 served GLB length changed")
if smoke["pixelEvidence"]["tealPixels"] < 5000:
    raise RuntimeError("Proxy v5 teal evidence is insufficient")
if smoke["pixelEvidence"]["cyanPixels"] < 250:
    raise RuntimeError("Proxy v5 cyan evidence is insufficient")
if smoke["pixelEvidence"]["placeholderPinkPixels"] != 0:
    raise RuntimeError("Proxy v5 browser screenshot contains placeholder pixels")

config_text = CONFIG_PATH.read_text(encoding="utf-8")
if 'const DEFAULT_PLAYER_MODEL_URL = "/models/chatgpt-fox-proxy-v5.glb";' not in config_text:
    raise RuntimeError("Proxy v5 is not the active default game model")
if "VITE_PLAYER_MODEL_URL" not in config_text or "configuredModelUrl || DEFAULT_PLAYER_MODEL_URL" not in config_text:
    raise RuntimeError("The environment override/fallback path was not preserved")

review_names = {Path(record["path"]).name for record in manifest["review"]["sheets"]}
if review_names != {
    "neutral-multiview.jpg",
    "walk-frame-1-contact.jpg",
    "walk-frame-17-contact.jpg",
    "sit-frame-12-contact.jpg",
    "wave-frame-20-contact.jpg",
}:
    raise RuntimeError(f"Unexpected proxy v5 review sheets: {sorted(review_names)}")

retained_sources = manifest.get("source", {}).get("retainedSources", [])
if len(retained_sources) < 10:
    raise RuntimeError("Approved source/reference retention set is incomplete")
for source in retained_sources:
    verify_record(source)
if not manifest.get("construction", {}).get("legacyArchivePurged"):
    raise RuntimeError("Legacy Blender archive was not marked as purged")

result = {
    "ok": True,
    "manifest": str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
    "verifiedArtifacts": len(verified),
    "geometry": expected_geometry,
    "glb": structure,
    "minimumValidatedZ": validation["minimumValidatedZ"],
    "browserEvidence": smoke["pixelEvidence"],
    "activeModel": "/models/chatgpt-fox-proxy-v5.glb",
    "retainedSourceCount": len(retained_sources),
}
print(json.dumps(result, indent=2))



