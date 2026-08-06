from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
MANIFEST_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v5.json"
CONFIG_PATH = ROOT / "client/src/game/config/localPlayerConfig.ts"
CHARACTER_MODEL_PATH = ROOT / "client/src/game/entities/CharacterModel.ts"
PLAYER_PATH = ROOT / "client/src/game/entities/Player.ts"
EXPECTED_STAGE = "hybrid_proxy_v5_fullbody_walk_footlock_verified"
EXPECTED_ACTIONS = ["angry", "idle", "laugh", "sitting", "sleep", "walking", "wave"]
EXPECTED_MODEL_URL = "/models/chatgpt-fox-proxy-v5.glb?rev=fullbody-footlock-3"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_record(record: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / record["path"]
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_bytes = path.stat().st_size
    actual_hash = sha256_file(path)
    if actual_bytes != record["bytes"] or actual_hash != record["sha256"]:
        raise RuntimeError(
            f"Artifact mismatch for {record['path']}: "
            f"bytes {actual_bytes}/{record['bytes']} "
            f"hash {actual_hash}/{record['sha256']}"
        )
    return {
        "path": record["path"],
        "bytes": actual_bytes,
        "sha256": actual_hash,
    }


def collect_records(value: Any, output: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        if {"path", "bytes", "sha256"}.issubset(value):
            output.append(value)
        for nested in value.values():
            collect_records(nested, output)
    elif isinstance(value, list):
        for nested in value:
            collect_records(nested, output)


def load_json_record(record: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / record["path"]
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object in {path}")
    return value


def parse_glb(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise RuntimeError("Invalid proxy v5 GLB header")
    json_length, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise RuntimeError("Proxy v5 GLB JSON chunk is missing")
    payload = json.loads(data[20 : 20 + json_length].decode("utf-8"))
    return {
        "version": version,
        "bytes": len(data),
        "nodes": len(payload.get("nodes", [])),
        "meshes": len(payload.get("meshes", [])),
        "materials": len(payload.get("materials", [])),
        "skins": len(payload.get("skins", [])),
        "animations": sorted(
            entry.get("name")
            for entry in payload.get("animations", [])
            if entry.get("name")
        ),
        "scenes": len(payload.get("scenes", [])),
    }


def require_close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if not math.isclose(float(actual), float(expected), abs_tol=tolerance, rel_tol=0.0):
        raise RuntimeError(f"{label}: expected {expected}, got {actual}")


if not MANIFEST_PATH.is_file():
    raise FileNotFoundError(MANIFEST_PATH)
manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
if manifest.get("stage") != EXPECTED_STAGE:
    raise RuntimeError(f"Unexpected proxy v5 stage: {manifest.get('stage')}")

records: list[dict[str, Any]] = []
collect_records(manifest, records)
unique_records = {record["path"]: record for record in records}
verified = [verify_record(record) for record in unique_records.values()]

if manifest.get("construction", {}).get("bones") != 26:
    raise RuntimeError("Proxy v5 rig must contain 26 bones")
if manifest.get("construction", {}).get("meshes") != 47:
    raise RuntimeError("Proxy v5 must contain 47 visible meshes")
if manifest.get("construction", {}).get("materials") != 4:
    raise RuntimeError("Proxy v5 must contain four materials")
for object_name in ("MDL_V5_BODY", "MDL_V5_TAIL_ROOT"):
    if object_name not in manifest.get("construction", {}).get("deformingObjects", {}):
        raise RuntimeError(f"Missing deformation declaration for {object_name}")

export_record = manifest["export"]["file"]
structure = parse_glb(ROOT / export_record["path"])
if structure != manifest["export"]["structure"]:
    raise RuntimeError(f"GLB structure does not match the manifest: {structure}")
for key, expected in {
    "version": 2,
    "nodes": 74,
    "meshes": 47,
    "materials": 4,
    "skins": 1,
    "scenes": 1,
}.items():
    if structure.get(key) != expected:
        raise RuntimeError(f"Unexpected GLB {key}: {structure.get(key)}")
if structure.get("animations") != EXPECTED_ACTIONS:
    raise RuntimeError(f"Unexpected GLB animation set: {structure.get('animations')}")

locomotion = manifest.get("locomotion", {})
ik_summary = locomotion.get("fullBodyAnalyticalWalk", {})
if ik_summary.get("frameRange") != [1, 13]:
    raise RuntimeError(f"Unexpected walking frame range: {ik_summary}")
require_close(ik_summary.get("fps", 0.0), 24.0, 1e-6, "Walk fps")
require_close(ik_summary.get("authoredDurationSeconds", 0.0), 0.5, 1e-6, "Authored walk duration")
require_close(ik_summary.get("strideHalfBlender", 0.0), 0.65, 1e-6, "Stride half-length")
require_close(ik_summary.get("stanceFraction", 0.0), 0.5, 1e-6, "Stance fraction")
require_close(ik_summary.get("maximumExtensionRatio", 0.0), 0.97, 1e-6, "Extension limit")
require_close(ik_summary.get("pelvisLateralTravel", 0.0), 0.14, 1e-5, "Pelvis lateral travel")
if not 0.07 <= float(ik_summary.get("pelvisVerticalTravel", 0.0)) <= 0.12:
    raise RuntimeError(f"Pelvis vertical travel is invalid: {ik_summary}")

expected_pose_frames = {
    "contactLeft": 1,
    "compressionLeft": 2,
    "passingLeft": 4,
    "elevationLeft": 6,
    "contactRight": 7,
    "compressionRight": 8,
    "passingRight": 10,
    "elevationRight": 12,
}
if ik_summary.get("poseFrames") != expected_pose_frames:
    raise RuntimeError(f"Walking phase map changed: {ik_summary.get('poseFrames')}")

for side in ("L", "R"):
    leg = ik_summary.get("legs", {}).get(side)
    if not isinstance(leg, dict):
        raise RuntimeError(f"Missing leg metrics for {side}")
    flexion = [float(value) for value in leg.get("kneeFlexionRangeDegrees", [])]
    if len(flexion) != 2 or flexion[0] < 25.0 or flexion[1] < 95.0:
        raise RuntimeError(f"Leg {side} knee cycle is incomplete: {leg}")
    thigh_range = [float(value) for value in leg.get("thighAngleRangeDegrees", [])]
    if len(thigh_range) != 2 or thigh_range[1] - thigh_range[0] < 55.0:
        raise RuntimeError(f"Leg {side} thigh motion is insufficient: {leg}")
    if float(leg.get("maximumExtensionRatio", 1.0)) > 0.970001:
        raise RuntimeError(f"Leg {side} exceeds its extension limit: {leg}")
    support_z = [float(value) for value in leg.get("supportFootMinimumZRange", [])]
    if len(support_z) != 2 or min(support_z) < -0.001 or max(support_z) > 0.01:
        raise RuntimeError(f"Leg {side} support foot is not grounded: {leg}")
    clearance = [float(value) for value in leg.get("swingFootClearanceRange", [])]
    if len(clearance) != 2 or clearance[0] < 0.08 or clearance[1] < 0.50:
        raise RuntimeError(f"Leg {side} swing arc is insufficient: {leg}")

ik_evidence = load_json_record(ik_summary["record"])
if ik_evidence.get("stage") != "proxy_v5_ik_walk_mathematically_validated":
    raise RuntimeError("Analytical walk evidence stage is missing")
if ik_evidence.get("kinematics", {}).get("frameRange") != [1, 13]:
    raise RuntimeError("Analytical walk evidence frame range changed")

foot_summary = locomotion.get("worldFootLockAndTurning", {})
foot_evidence = load_json_record(foot_summary["record"])
if foot_evidence.get("stage") != "proxy_v5_fullbody_walk_and_world_foot_lock_validated":
    raise RuntimeError("Foot-lock runtime evidence stage is missing")
calibration = foot_summary.get("calibration", {})
require_close(calibration.get("exportedReferenceSpeed", 0.0), 1.385, 1e-6, "Exported walk reference speed")
require_close(calibration.get("gameplaySpeed", 0.0), 2.2, 1e-6, "Gameplay movement speed")
require_close(calibration.get("turnResponseTime", 0.0), 0.16, 1e-6, "Turn response time")
control_drift = float(foot_summary.get("controlMaximumDrift", 0.0))
locked_drift = float(foot_summary.get("lockedMaximumDrift", 1.0))
if control_drift < 0.10:
    raise RuntimeError(f"Foot-lock control drift is too small to prove the fix: {foot_summary}")
if locked_drift > 0.015 or locked_drift >= control_drift * 0.15:
    raise RuntimeError(f"Foot lock did not eliminate planted-foot drift: {foot_summary}")
if float(foot_summary.get("maximumCorrectionPerFrame", 1.0)) > 0.15:
    raise RuntimeError(f"Foot-lock correction exceeded its safety bound: {foot_summary}")

visual_summary = locomotion.get("gameplayCamera", {})
visual_evidence = load_json_record(visual_summary["record"])
if visual_evidence.get("stage") != "proxy_v5_gameplay_walk_visual_smoke_verified":
    raise RuntimeError("Gameplay-camera visual evidence stage is missing")
visual = visual_summary.get("visualAnalysis", {})
if visual != visual_evidence.get("visualAnalysis"):
    raise RuntimeError("Manifest visual metrics do not match the evidence file")
if visual.get("frameCount") != 8:
    raise RuntimeError(f"Unexpected gameplay-camera frame count: {visual}")
if float(visual.get("averageUpperToLowerRatio", 0.0)) < 0.30:
    raise RuntimeError(f"Lower-leg movement still dominates visually: {visual}")
if int(visual.get("readableUpperLegPairs", 0)) < 4:
    raise RuntimeError(f"Upper-leg movement is not repeatedly visible: {visual}")
if int(visual.get("maximumUpperLegXorPixels", 0)) < 800:
    raise RuntimeError(f"Upper-leg silhouette difference is too small: {visual}")

animation_record = manifest["animations"]["validation"]
animation = load_json_record(animation_record)
if animation.get("stage") != "proxy_v5_animations_and_deformation_validated":
    raise RuntimeError("Animation/deformation validation stage is missing")
if sorted(animation.get("actions", [])) != EXPECTED_ACTIONS:
    raise RuntimeError("Validated action set changed")
if animation.get("frameRanges", {}).get("walking") != [1.0, 13.0]:
    raise RuntimeError("Validated walking frame range changed")
if manifest["animations"].get("frameRanges") != animation.get("frameRanges"):
    raise RuntimeError("Manifest frame ranges do not match validation evidence")

runtime = load_json_record(manifest["animations"]["browserRuntime"]["record"])
if runtime.get("stage") != "proxy_v5_animation_runtime_smoke_verified":
    raise RuntimeError("Browser animation runtime stage is missing")
if runtime.get("locomotionSequenceVerified") != ["idle", "walking", "idle"]:
    raise RuntimeError("Browser runtime did not verify idle -> walking -> idle")
if runtime.get("emotesVerified") != ["wave", "laugh", "angry", "sleep"]:
    raise RuntimeError("Browser runtime did not verify all four emotes")
if runtime.get("fallbackWarnings"):
    raise RuntimeError(f"Browser runtime used animation fallbacks: {runtime['fallbackWarnings']}")

browser = load_json_record(manifest["integration"]["browserSmoke"]["record"])
if browser.get("stage") != "proxy_v5_browser_smoke_verified":
    raise RuntimeError("Browser model smoke stage is missing")
if browser.get("model", {}).get("url") != EXPECTED_MODEL_URL:
    raise RuntimeError(f"Browser loaded an unexpected model URL: {browser.get('model')}")
if browser.get("page", {}).get("status") != 200 or browser.get("model", {}).get("status") != 200:
    raise RuntimeError("Browser HTTP smoke failed")
if browser.get("model", {}).get("contentType") != "model/gltf-binary":
    raise RuntimeError("Browser GLB MIME type changed")
if browser.get("model", {}).get("servedBytes") != structure["bytes"]:
    raise RuntimeError("Browser-served GLB size changed")
pixels = browser.get("pixelEvidence", {})
if int(pixels.get("tealPixels", 0)) < 5000 or int(pixels.get("cyanPixels", 0)) < 250:
    raise RuntimeError(f"Fox is not sufficiently visible in browser smoke: {pixels}")
if int(pixels.get("placeholderPinkPixels", -1)) != 0:
    raise RuntimeError(f"Placeholder remains visible: {pixels}")

integration = manifest.get("integration", {})
if integration.get("defaultUrl") != EXPECTED_MODEL_URL:
    raise RuntimeError(f"Manifest default model URL changed: {integration.get('defaultUrl')}")
require_close(integration.get("movementSpeed", 0.0), 2.2, 1e-6, "Movement speed")
require_close(integration.get("exportedWalkReferenceSpeed", 0.0), 1.385, 1e-6, "Exported reference speed")
require_close(integration.get("turnResponseTimeSeconds", 0.0), 0.16, 1e-6, "Turn response time")

config_text = CONFIG_PATH.read_text(encoding="utf-8")
character_text = CHARACTER_MODEL_PATH.read_text(encoding="utf-8")
player_text = PLAYER_PATH.read_text(encoding="utf-8")
if f'const DEFAULT_PLAYER_MODEL_URL = "{EXPECTED_MODEL_URL}";' not in config_text:
    raise RuntimeError("Proxy v5 full-body walk is not the active default model")
for marker in (
    "const WALK_REFERENCE_SPEED = 1.385;",
    "setWalkingSpeed(unitsPerSecond: number)",
    "getWalkingSupportFootWorldPosition",
):
    if marker not in character_text:
        raise RuntimeError(f"CharacterModel marker is missing: {marker}")
for marker in (
    "const TURN_RESPONSE_TIME = 0.16;",
    "private readonly speed = 2.2;",
    "applyWalkingFootLock",
    "rotateTowardsMovement",
    "this.object.quaternion.slerp",
):
    if marker not in player_text:
        raise RuntimeError(f"Player marker is missing: {marker}")

result = {
    "ok": True,
    "manifest": str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
    "stage": manifest["stage"],
    "verifiedArtifacts": len(verified),
    "glb": structure,
    "walking": {
        "frameRange": ik_summary["frameRange"],
        "pelvisLateralTravel": ik_summary["pelvisLateralTravel"],
        "pelvisVerticalTravel": ik_summary["pelvisVerticalTravel"],
        "lockedMaximumDrift": locked_drift,
        "controlMaximumDrift": control_drift,
        "readableUpperLegPairs": visual["readableUpperLegPairs"],
        "maximumUpperLegXorPixels": visual["maximumUpperLegXorPixels"],
    },
    "browserEvidence": pixels,
    "activeModel": EXPECTED_MODEL_URL,
}
print(json.dumps(result, indent=2))
