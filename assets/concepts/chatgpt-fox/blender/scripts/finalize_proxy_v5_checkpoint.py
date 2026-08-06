from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
REVIEW_DIR = BLENDER_DIR / "proxy-v5-review"
BLEND_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v5.blend"
GLB_PATH = ROOT / "client/public/models/chatgpt-fox-proxy-v5.glb"
CONFIG_PATH = ROOT / "client/src/game/config/localPlayerConfig.ts"
MOVEMENT_STATE_PATH = ROOT / "client/src/game/entities/MovementState.ts"
CHARACTER_MODEL_PATH = ROOT / "client/src/game/entities/CharacterModel.ts"
PLAYER_PATH = ROOT / "client/src/game/entities/Player.ts"
EMOTE_MENU_PATH = ROOT / "client/src/ui/components/EmoteMenu.ts"
ANIMATION_PATH = BLENDER_DIR / "proxy-v5-animation-validation.json"
IK_WALK_PATH = BLENDER_DIR / "proxy-v5-ik-walk-validation.json"
FOOT_LOCK_PATH = BLENDER_DIR / "proxy-v5-foot-lock-runtime-validation.json"
ANIMATION_RUNTIME_PATH = BLENDER_DIR / "proxy-v5-animation-runtime-smoke.json"
WALK_VISUAL_PATH = BLENDER_DIR / "proxy-v5-walk-visual-smoke.json"
BROWSER_SMOKE_PATH = BLENDER_DIR / "proxy-v5-game-smoke.json"
SCREENSHOT_PATH = BLENDER_DIR / "game_smoke_proxy_v5.png"
WALK_CONTACT_PATH = REVIEW_DIR / "walk-gameplay-camera-contact.jpg"
MANIFEST_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v5.json"

DEFAULT_MODEL_URL = "/models/chatgpt-fox-proxy-v5.glb?rev=fullbody-footlock-3"
EXPECTED_ACTIONS = ["angry", "idle", "laugh", "sitting", "sleep", "walking", "wave"]
EXPECTED_GEOMETRY = {
    "nodes": 74,
    "meshes": 47,
    "materials": 4,
    "skins": 1,
    "scenes": 1,
}

SCRIPT_PATHS = (
    BLENDER_DIR / "scripts/refine_proxy_v5_ik_walk.py",
    BLENDER_DIR / "scripts/validate_proxy_v5_animations.py",
    BLENDER_DIR / "scripts/export_proxy_v5_glb.py",
    BLENDER_DIR / "scripts/record_proxy_v5_game_smoke.py",
    BLENDER_DIR / "scripts/record_proxy_v5_animation_runtime_smoke.py",
    BLENDER_DIR / "scripts/record_proxy_v5_walk_visual_smoke.py",
    BLENDER_DIR / "scripts/finalize_proxy_v5_checkpoint.py",
    BLENDER_DIR / "scripts/verify_proxy_v5_checkpoint.py",
    ROOT / "client/scripts/calibrate-proxy-v5-walk-speed.mjs",
    ROOT / "client/scripts/verify-proxy-v5-foot-lock.mjs",
)

SOURCE_CANDIDATES = (
    ROOT / "assets/concepts/chatgpt-fox/character-brief.json",
    ROOT / "assets/concepts/chatgpt-fox/source/chatgpt_fox_front.jpg",
    ROOT / "assets/concepts/chatgpt-fox/source/chatgpt_fox_side.jpg",
    ROOT / "assets/concepts/chatgpt-fox/source/chatgpt_fox_back.jpg",
    ROOT / "assets/concepts/chatgpt-fox/source/chatgpt_fox_three_quarter.jpg",
    ROOT / "assets/concepts/chatgpt-fox/source/generation-manifest.json",
    ROOT / "assets/concepts/chatgpt-fox/prepared/chatgpt_fox_front.jpg",
    ROOT / "assets/concepts/chatgpt-fox/prepared/chatgpt_fox_side.jpg",
    ROOT / "assets/concepts/chatgpt-fox/prepared/chatgpt_fox_back.jpg",
    ROOT / "assets/concepts/chatgpt-fox/prepared/chatgpt_fox_three-quarter.jpg",
    ROOT / "assets/concepts/chatgpt-fox/prepared/prepared-manifest.json",
    BLENDER_DIR / "chatgpt_fox_references.blend",
    BLENDER_DIR / "chatgpt_fox_references.loop.json",
)


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_info(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return {
        "path": relative(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object in {path}")
    return value


def parse_glb(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise RuntimeError("Proxy v5 GLB header is invalid")
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


required_paths = (
    BLEND_PATH,
    GLB_PATH,
    CONFIG_PATH,
    MOVEMENT_STATE_PATH,
    CHARACTER_MODEL_PATH,
    PLAYER_PATH,
    EMOTE_MENU_PATH,
    ANIMATION_PATH,
    IK_WALK_PATH,
    FOOT_LOCK_PATH,
    ANIMATION_RUNTIME_PATH,
    WALK_VISUAL_PATH,
    BROWSER_SMOKE_PATH,
    SCREENSHOT_PATH,
    WALK_CONTACT_PATH,
    *SCRIPT_PATHS,
)
missing = [relative(path) for path in required_paths if not path.is_file()]
if missing:
    raise FileNotFoundError(f"Proxy v5 checkpoint inputs are missing: {missing}")

animation = load_json(ANIMATION_PATH)
ik_walk = load_json(IK_WALK_PATH)
foot_lock = load_json(FOOT_LOCK_PATH)
animation_runtime = load_json(ANIMATION_RUNTIME_PATH)
walk_visual = load_json(WALK_VISUAL_PATH)
browser_smoke = load_json(BROWSER_SMOKE_PATH)
structure = parse_glb(GLB_PATH)

if animation.get("stage") != "proxy_v5_animations_and_deformation_validated":
    raise RuntimeError("Proxy v5 animation validation has not passed")
if sorted(animation.get("actions", [])) != EXPECTED_ACTIONS:
    raise RuntimeError(f"Unexpected validated animation set: {animation.get('actions')}")
if animation.get("frameRanges", {}).get("walking") != [1.0, 13.0]:
    raise RuntimeError(f"Walking frame range changed: {animation.get('frameRanges')}")
if animation.get("runtimePolicy") != {
    "loop": ["idle", "walking"],
    "once": ["sitting", "wave", "laugh", "angry", "sleep"],
}:
    raise RuntimeError(f"Runtime animation policy changed: {animation.get('runtimePolicy')}")
if float(animation.get("minimumValidatedZ", -1.0)) < -0.035:
    raise RuntimeError("Proxy v5 exceeds the floor-penetration tolerance")
if animation.get("rig", {}).get("bones") != 26:
    raise RuntimeError(f"Proxy v5 rig count changed: {animation.get('rig')}")

if ik_walk.get("stage") != "proxy_v5_ik_walk_mathematically_validated":
    raise RuntimeError("Full-body analytical walk evidence is missing")
kinematics = ik_walk.get("kinematics", {})
ik_validation = ik_walk.get("validation", {})
if kinematics.get("frameRange") != [1, 13]:
    raise RuntimeError(f"Unexpected analytical walk frame range: {kinematics}")
require_close(kinematics.get("fps", 0.0), 24.0, 1e-6, "Walk fps")
require_close(kinematics.get("durationSeconds", 0.0), 0.5, 1e-6, "Authored walk duration")
require_close(kinematics.get("runtimeScale", 0.0), 0.32, 1e-6, "Runtime scale")
require_close(kinematics.get("strideHalfBlender", 0.0), 0.65, 1e-6, "Stride half-length")
require_close(kinematics.get("stanceFraction", 0.0), 0.5, 1e-6, "Stance fraction")

walk_motion = animation.get("walkBodyMotion", {})
require_close(walk_motion.get("pelvisLateralTravel", 0.0), 0.14, 1e-5, "Pelvis lateral travel")
vertical_travel = float(walk_motion.get("pelvisVerticalTravel", 0.0))
if not 0.07 <= vertical_travel <= 0.12:
    raise RuntimeError(f"Pelvis rise/fall is invalid: {vertical_travel}")
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
if walk_motion.get("poseFrames") != expected_pose_frames:
    raise RuntimeError(f"Walk phase map changed: {walk_motion.get('poseFrames')}")

for side in ("L", "R"):
    leg = walk_motion.get("legs", {}).get(side)
    if not isinstance(leg, dict):
        raise RuntimeError(f"Missing walk metrics for leg {side}")
    flexion = [float(value) for value in leg.get("kneeFlexionRangeDegrees", [])]
    if len(flexion) != 2 or flexion[0] < 25.0 or flexion[1] < 95.0:
        raise RuntimeError(f"Leg {side} lacks a complete knee cycle: {leg}")
    support_z = [float(value) for value in leg.get("supportFootMinimumZRange", [])]
    if len(support_z) != 2 or min(support_z) < -0.001 or max(support_z) > 0.01:
        raise RuntimeError(f"Leg {side} support foot is not planted: {leg}")
    clearance = [float(value) for value in leg.get("swingFootClearanceRange", [])]
    if len(clearance) != 2 or clearance[0] < 0.08 or clearance[1] < 0.50:
        raise RuntimeError(f"Leg {side} swing arc is insufficient: {leg}")
    thigh_range = [float(value) for value in leg.get("thighAngleRangeDegrees", [])]
    if len(thigh_range) != 2 or thigh_range[1] - thigh_range[0] < 55.0:
        raise RuntimeError(f"Leg {side} thigh does not participate in the step: {leg}")
    if float(leg.get("maximumExtensionRatio", 1.0)) > 0.970001:
        raise RuntimeError(f"Leg {side} exceeds the 97% extension limit: {leg}")
    if float(leg.get("referenceSpeedErrorPercent", 100.0)) > 3.0:
        raise RuntimeError(f"Leg {side} authored stance speed is inconsistent: {leg}")

if foot_lock.get("stage") != "proxy_v5_fullbody_walk_and_world_foot_lock_validated":
    raise RuntimeError("World-space foot-lock evidence is missing")
foot_calibration = foot_lock.get("calibration", {})
require_close(foot_calibration.get("exportedReferenceSpeed", 0.0), 1.385, 1e-6, "Exported walk reference speed")
require_close(foot_calibration.get("gameplaySpeed", 0.0), 2.2, 1e-6, "Gameplay movement speed")
require_close(foot_calibration.get("turnResponseTime", 0.0), 0.16, 1e-6, "Turn response time")
without_lock = foot_lock.get("evidence", {}).get("withoutFootLock", {})
with_lock = foot_lock.get("evidence", {}).get("withFootLock", {})
without_drift = float(without_lock.get("maximumSupportDrift", 0.0))
with_drift = float(with_lock.get("maximumSupportDrift", 1.0))
if without_drift < 0.10:
    raise RuntimeError(f"Foot-lock control case is not meaningful: {without_lock}")
if with_drift > 0.015 or with_drift >= without_drift * 0.15:
    raise RuntimeError(f"World-space foot lock did not remove support drift: {foot_lock}")
if float(with_lock.get("maximumCorrection", 1.0)) > 0.15:
    raise RuntimeError(f"Foot-lock correction exceeded its frame bound: {with_lock}")

if walk_visual.get("stage") != "proxy_v5_gameplay_walk_visual_smoke_verified":
    raise RuntimeError("Gameplay-camera walk smoke has not passed")
visual = walk_visual.get("visualAnalysis", {})
if visual.get("frameCount") != 8:
    raise RuntimeError(f"Unexpected gameplay-camera sample count: {visual}")
if float(visual.get("averageUpperToLowerRatio", 0.0)) < 0.30:
    raise RuntimeError(f"Lower legs still dominate the gameplay silhouette: {visual}")
if int(visual.get("readableUpperLegPairs", 0)) < 4:
    raise RuntimeError(f"Upper-leg motion is not repeatedly visible: {visual}")
if int(visual.get("maximumUpperLegXorPixels", 0)) < 800:
    raise RuntimeError(f"Upper-leg silhouette change is too small: {visual}")

if animation_runtime.get("stage") != "proxy_v5_animation_runtime_smoke_verified":
    raise RuntimeError("Browser animation runtime smoke has not passed")
if animation_runtime.get("locomotionSequenceVerified") != ["idle", "walking", "idle"]:
    raise RuntimeError("Browser did not verify idle -> walking -> idle")
if animation_runtime.get("emotesVerified") != ["wave", "laugh", "angry", "sleep"]:
    raise RuntimeError("Browser did not verify all emotes")
if animation_runtime.get("fallbackWarnings"):
    raise RuntimeError(f"Browser animation runtime used fallbacks: {animation_runtime['fallbackWarnings']}")

if browser_smoke.get("stage") != "proxy_v5_browser_smoke_verified":
    raise RuntimeError("Browser model smoke has not passed")
if browser_smoke.get("model", {}).get("url") != DEFAULT_MODEL_URL:
    raise RuntimeError(f"Browser smoke used an unexpected model URL: {browser_smoke.get('model')}")
if browser_smoke.get("page", {}).get("status") != 200 or browser_smoke.get("model", {}).get("status") != 200:
    raise RuntimeError("Browser HTTP smoke failed")
if browser_smoke.get("model", {}).get("contentType") != "model/gltf-binary":
    raise RuntimeError("Browser served an unexpected GLB content type")
if browser_smoke.get("model", {}).get("servedBytes") != structure["bytes"]:
    raise RuntimeError("Browser-served GLB bytes do not match the exported file")
pixels = browser_smoke.get("pixelEvidence", {})
if int(pixels.get("tealPixels", 0)) < 5000 or int(pixels.get("cyanPixels", 0)) < 250:
    raise RuntimeError(f"Fox colors are not visible in browser smoke: {pixels}")
if int(pixels.get("placeholderPinkPixels", -1)) != 0:
    raise RuntimeError(f"Placeholder remains visible: {pixels}")

for key, expected in EXPECTED_GEOMETRY.items():
    if structure.get(key) != expected:
        raise RuntimeError(f"Unexpected GLB {key}: {structure.get(key)}")
if structure.get("animations") != EXPECTED_ACTIONS:
    raise RuntimeError(f"Unexpected GLB animation set: {structure.get('animations')}")

config_text = CONFIG_PATH.read_text(encoding="utf-8")
character_text = CHARACTER_MODEL_PATH.read_text(encoding="utf-8")
player_text = PLAYER_PATH.read_text(encoding="utf-8")
if f'"{DEFAULT_MODEL_URL}"' not in config_text:
    raise RuntimeError("The active model URL was not cache-busted for the full-body walk")
for marker in (
    "const WALK_REFERENCE_SPEED = 1.385;",
    "setWalkingSpeed(unitsPerSecond: number)",
    "getWalkingSupportFootWorldPosition",
    "THREE.LoopRepeat",
):
    if marker not in character_text:
        raise RuntimeError(f"CharacterModel locomotion marker is missing: {marker}")
for marker in (
    "const TURN_RESPONSE_TIME = 0.16;",
    "private readonly speed = 2.2;",
    "applyWalkingFootLock",
    "rotateTowardsMovement",
    "this.object.quaternion.slerp",
):
    if marker not in player_text:
        raise RuntimeError(f"Player locomotion marker is missing: {marker}")

frame_records = [file_info(ROOT / frame_path) for frame_path in walk_visual["capture"]["frames"]]
source_records = [file_info(path) for path in SOURCE_CANDIDATES if path.is_file()]
script_records = [file_info(path) for path in SCRIPT_PATHS]

manifest = {
    "stage": "hybrid_proxy_v5_fullbody_walk_footlock_verified",
    "character": "chatgpt-fox",
    "source": {
        "canonicalBlend": file_info(BLEND_PATH),
        "retainedReferences": source_records,
    },
    "construction": {
        "mode": "hybrid articulated gameplay proxy",
        "rig": "FOX_RIG_GUIDE",
        "bones": 26,
        "meshes": 47,
        "materials": 4,
        "deformingObjects": animation["deformingObjects"],
        "meshBindings": animation["meshBindings"],
    },
    "locomotion": {
        "fullBodyAnalyticalWalk": {
            "record": file_info(IK_WALK_PATH),
            "frameRange": kinematics["frameRange"],
            "fps": kinematics["fps"],
            "authoredDurationSeconds": kinematics["durationSeconds"],
            "strideHalfBlender": kinematics["strideHalfBlender"],
            "stanceFraction": kinematics["stanceFraction"],
            "maximumExtensionRatio": 0.97,
            "pelvisLateralTravel": walk_motion["pelvisLateralTravel"],
            "pelvisVerticalTravel": walk_motion["pelvisVerticalTravel"],
            "poseFrames": walk_motion["poseFrames"],
            "legs": walk_motion["legs"],
        },
        "worldFootLockAndTurning": {
            "record": file_info(FOOT_LOCK_PATH),
            "calibration": foot_calibration,
            "controlMaximumDrift": without_drift,
            "lockedMaximumDrift": with_drift,
            "maximumCorrectionPerFrame": with_lock["maximumCorrection"],
        },
        "gameplayCamera": {
            "record": file_info(WALK_VISUAL_PATH),
            "contactSheet": file_info(WALK_CONTACT_PATH),
            "frames": frame_records,
            "visualAnalysis": visual,
        },
    },
    "animations": {
        "names": EXPECTED_ACTIONS,
        "frameRanges": animation["frameRanges"],
        "runtimePolicy": animation["runtimePolicy"],
        "validation": file_info(ANIMATION_PATH),
        "browserRuntime": {
            "record": file_info(ANIMATION_RUNTIME_PATH),
            "observedActiveSequence": animation_runtime["observedActiveSequence"],
            "locomotionSequenceVerified": animation_runtime["locomotionSequenceVerified"],
            "emotesVerified": animation_runtime["emotesVerified"],
            "fallbackWarnings": animation_runtime["fallbackWarnings"],
        },
        "minimumValidatedZ": animation["minimumValidatedZ"],
    },
    "export": {
        "file": file_info(GLB_PATH),
        "structure": structure,
    },
    "integration": {
        "defaultUrl": DEFAULT_MODEL_URL,
        "scale": 0.32,
        "movementSpeed": 2.2,
        "exportedWalkReferenceSpeed": 1.385,
        "turnResponseTimeSeconds": 0.16,
        "footLock": "world-space XZ support-foot anchoring with bounded correction",
        "phasePolicy": "walking action phase is preserved during direction changes",
        "files": {
            "config": file_info(CONFIG_PATH),
            "movementState": file_info(MOVEMENT_STATE_PATH),
            "characterModel": file_info(CHARACTER_MODEL_PATH),
            "player": file_info(PLAYER_PATH),
            "emoteMenu": file_info(EMOTE_MENU_PATH),
        },
        "build": {
            "command": "npm run build",
            "status": "passed",
            "warning": "Existing non-blocking Vite JavaScript chunk-size warning remains.",
        },
        "browserSmoke": {
            "record": file_info(BROWSER_SMOKE_PATH),
            "screenshot": file_info(SCREENSHOT_PATH),
            "pageStatus": browser_smoke["page"]["status"],
            "modelStatus": browser_smoke["model"]["status"],
            "contentType": browser_smoke["model"]["contentType"],
            "servedBytes": browser_smoke["model"]["servedBytes"],
            "pixelEvidence": pixels,
        },
    },
    "artifacts": {
        "scripts": script_records,
    },
    "limitations": [
        "This remains a hybrid low-poly gameplay proxy rather than a final unified production mesh.",
        "Most limb and facial components remain separate rigid meshes, so close-up deformation is limited.",
        "The foot lock is runtime root compensation rather than a fully procedural per-leg IK rig in Three.js.",
    ],
    "nextMilestone": [
        "Review the corrected gait in normal gameplay and tune stride character only from new visual evidence.",
        "Move to unified production topology, final weights, UVs, and textures when close-up presentation requires it.",
    ],
}

MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"manifest": file_info(MANIFEST_PATH), "checkpoint": manifest}, indent=2))
