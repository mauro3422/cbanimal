from __future__ import annotations

import hashlib
import json
import shutil
import struct
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
REVIEW_DIR = BLENDER_DIR / "proxy-v5-review"
BLEND_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v5.blend"
GLB_PATH = ROOT / "client/public/models/chatgpt-fox-proxy-v5.glb"
CONFIG_PATH = ROOT / "client/src/game/config/localPlayerConfig.ts"
ANIMATION_PATH = BLENDER_DIR / "proxy-v5-animation-validation.json"
SMOKE_PATH = BLENDER_DIR / "proxy-v5-game-smoke.json"
SCREENSHOT_PATH = BLENDER_DIR / "game_smoke_proxy_v5.png"
NEUTRAL_MANIFEST_PATH = BLENDER_DIR / "review-bundles-v5/fox-v5-continuity_review.json"
NEUTRAL_MANIFEST_FINAL = REVIEW_DIR / "neutral-review.json"
MANIFEST_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v5.json"

REVIEW_SOURCES = {
    "neutral-multiview.jpg": BLENDER_DIR / "review-bundles-v5/fox-v5-continuity_contact.png",
    "walk-frame-1-contact.jpg": BLENDER_DIR / "review-bundles-v5-poses/fox-v5-walk-frame1_contact.png",
    "walk-frame-17-contact.jpg": BLENDER_DIR / "review-bundles-v5-poses/fox-v5-walk-frame17_contact.png",
    "sit-frame-12-contact.jpg": BLENDER_DIR / "review-bundles-v5-poses/fox-v5-sit-frame12_contact.png",
    "wave-frame-20-contact.jpg": BLENDER_DIR / "review-bundles-v5-poses/fox-v5-wave-frame20_contact.png",
}

SCRIPT_NAMES = (
    "validate_proxy_v5_animations.py",
    "export_proxy_v5_glb.py",
    "record_proxy_v5_game_smoke.py",
    "finalize_proxy_v5_checkpoint.py",
    "verify_proxy_v5_checkpoint.py",
)

RETAINED_SOURCE_PATHS = (
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def file_info(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return {
        "path": relative(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def parse_glb(path: Path) -> dict:
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
        "animations": [entry.get("name") for entry in payload.get("animations", [])],
        "scenes": len(payload.get("scenes", [])),
    }


def compress_review(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        if max(rgb.size) > 1100:
            rgb.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        rgb.save(destination, "JPEG", quality=86, optimize=True, progressive=True)


required = [
    BLEND_PATH,
    GLB_PATH,
    CONFIG_PATH,
    ANIMATION_PATH,
    SMOKE_PATH,
    SCREENSHOT_PATH,
]
missing = [str(path) for path in required if not path.is_file()]
if missing:
    raise FileNotFoundError(f"Proxy v5 checkpoint inputs are missing: {missing}")

REVIEW_DIR.mkdir(parents=True, exist_ok=True)
source_reviews_available = NEUTRAL_MANIFEST_PATH.is_file() and all(
    source.is_file() for source in REVIEW_SOURCES.values()
)
if source_reviews_available:
    for destination_name, source in REVIEW_SOURCES.items():
        compress_review(source, REVIEW_DIR / destination_name)
    shutil.copyfile(NEUTRAL_MANIFEST_PATH, NEUTRAL_MANIFEST_FINAL)
else:
    compact_required = [
        NEUTRAL_MANIFEST_FINAL,
        *(REVIEW_DIR / name for name in REVIEW_SOURCES),
    ]
    compact_missing = [str(path) for path in compact_required if not path.is_file()]
    if compact_missing:
        raise FileNotFoundError(
            f"Neither source review bundles nor compact v5 review files are complete: {compact_missing}"
        )

neutral_review = json.loads(NEUTRAL_MANIFEST_FINAL.read_text(encoding="utf-8"))
animation = json.loads(ANIMATION_PATH.read_text(encoding="utf-8"))
smoke = json.loads(SMOKE_PATH.read_text(encoding="utf-8"))
structure = parse_glb(GLB_PATH)
config_text = CONFIG_PATH.read_text(encoding="utf-8")

expected_actions = ["idle", "sitting", "walking", "wave"]
if structure != {
    "version": 2,
    "bytes": 189924,
    "nodes": 72,
    "meshes": 47,
    "materials": 4,
    "skins": 1,
    "animations": expected_actions,
    "scenes": 1,
}:
    raise RuntimeError(f"Unexpected proxy v5 GLB structure: {structure}")
if neutral_review["geometry"]["totals"] != {
    "objects": 47,
    "mesh_objects": 47,
    "vertices": 994,
    "edges": 2306,
    "polygons": 1404,
    "triangles": 1780,
}:
    raise RuntimeError("Neutral v5 geometry totals changed unexpectedly")
if neutral_review.get("warnings"):
    raise RuntimeError(f"Neutral v5 review contains warnings: {neutral_review['warnings']}")
if animation.get("stage") != "proxy_v5_animations_and_deformation_validated":
    raise RuntimeError("Proxy v5 animation validation has not passed")
if animation.get("minimumValidatedZ", -1.0) < -0.035:
    raise RuntimeError("Proxy v5 floor tolerance failed")
if smoke.get("stage") != "proxy_v5_browser_smoke_verified":
    raise RuntimeError("Proxy v5 browser smoke has not passed")
if smoke["pixelEvidence"]["placeholderPinkPixels"] != 0:
    raise RuntimeError("Proxy v5 browser smoke still contains the placeholder")
if '"/models/chatgpt-fox-proxy-v5.glb"' not in config_text:
    raise RuntimeError("The game configuration does not activate proxy v5")

scripts = []
for name in SCRIPT_NAMES:
    path = BLENDER_DIR / "scripts" / name
    if path.is_file():
        scripts.append(file_info(path))

manifest = {
    "stage": "hybrid_proxy_v5_integrated_and_verified",
    "character": "chatgpt-fox",
    "visualBasis": {
        "description": "User-provided front, profile, and back screenshots reviewed in the active ChatGPT session.",
        "preserve": [
            "face and expression",
            "teal/cyan/white palette",
            "ears, hands, and paws",
            "approved segmented tail curve and white tip",
        ],
        "refine": [
            "torso-to-pelvis continuity",
            "neck embedding",
            "tail-root transition",
            "shoulder, hip, knee, and ankle overlap",
        ],
    },
    "source": {
        "canonicalBlend": file_info(BLEND_PATH),
        "retainedSources": [file_info(path) for path in RETAINED_SOURCE_PATHS],
        "cleanupPolicy": "Only canonical v5 runtime/checkpoint assets and approved source/reference inputs are retained.",
    },
    "construction": {
        "mode": "hybrid articulated proxy",
        "rig": "FOX_RIG_GUIDE",
        "bones": 24,
        "rigidMeshes": 45,
        "deformingMeshes": {
            "MDL_V5_BODY": ["pelvis", "spine", "chest", "neck"],
            "MDL_V5_TAIL_ROOT": ["pelvis", "tail.01"],
        },
        "legacyArchivePurged": True,
        "geometry": neutral_review["geometry"]["totals"],
        "materials": neutral_review["geometry"]["materials"],
        "warnings": neutral_review["warnings"],
    },
    "animations": {
        "names": ["idle", "walking", "sitting", "wave"],
        "validation": file_info(ANIMATION_PATH),
        "minimumValidatedZ": animation["minimumValidatedZ"],
        "deformingObjects": animation["deformingObjects"],
    },
    "export": {
        "file": file_info(GLB_PATH),
        "structure": structure,
    },
    "integration": {
        "config": file_info(CONFIG_PATH),
        "defaultUrl": "/models/chatgpt-fox-proxy-v5.glb",
        "scale": 0.32,
        "environmentOverridePreserved": True,
        "build": {
            "command": "npm run build",
            "status": "passed",
            "warning": "Existing non-blocking Vite JavaScript chunk-size warning remains.",
        },
        "browserSmoke": {
            "record": file_info(SMOKE_PATH),
            "screenshot": file_info(SCREENSHOT_PATH),
            "pageStatus": smoke["page"]["status"],
            "modelStatus": smoke["model"]["status"],
            "contentType": smoke["model"]["contentType"],
            "servedBytes": smoke["model"]["servedBytes"],
            "pixelEvidence": smoke["pixelEvidence"],
        },
    },
    "review": {
        "neutralSourceManifest": file_info(NEUTRAL_MANIFEST_FINAL),
        "sheets": [file_info(REVIEW_DIR / name) for name in REVIEW_SOURCES],
    },
    "artifacts": {
        "blend": file_info(BLEND_PATH),
        "scripts": scripts,
    },
    "limitations": [
        "This is a polished hybrid gameplay proxy, not the final unified 8k-12k production mesh.",
        "Face, limbs, paws, ears, and most tail segments remain separate rigid low-poly meshes.",
        "The four animation clips are validated gameplay clips rather than final polished animation.",
        "UVs, a 1024 texture set, production retopology, and close-up deformation polish remain future milestones.",
    ],
    "nextMilestone": [
        "Review v5 at gameplay camera distance and keep it as the creature production-direction baseline.",
        "Build a fully unified production body and tail only when close-up presentation becomes necessary.",
        "Create UVs, a 1024 texture, final weights, and refined animation controls.",
    ],
}
MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"manifest": file_info(MANIFEST_PATH), "checkpoint": manifest}, indent=2))




