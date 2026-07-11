from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import struct

from PIL import Image

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
RAW_REVIEW_DIR = BLENDER_DIR / "review-bundles"
FINAL_REVIEW_DIR = BLENDER_DIR / "proxy-v2-review"
BLEND_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v2.blend"
GLB_PATH = ROOT / "client/public/models/chatgpt-fox-proxy-v2.glb"
CONFIG_PATH = ROOT / "client/src/game/config/localPlayerConfig.ts"
ANIMATION_VALIDATION_PATH = BLENDER_DIR / "proxy-v2-animation-validation.json"
MANIFEST_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v2.json"

CONTACT_SOURCES = {
    "baseline_v1": "fox-baseline-v2_contact.png",
    "model_v2": "fox-v2-pass1_contact.png",
    "walk_frame_1": "fox-v2-walk-frame1_contact.png",
    "walk_frame_17": "fox-v2-walk-frame17_contact.png",
    "sit_frame_12": "fox-v2-sit-frame12_contact.png",
    "wave_frame_20": "fox-v2-wave-frame20_contact.png",
}


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


def parse_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20:
        raise RuntimeError("Proxy v2 GLB is too small")
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


def copy_json(source: Path, destination: Path) -> dict:
    payload = json.loads(source.read_text(encoding="utf-8"))
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def convert_contact(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGB")
    image.save(destination, format="JPEG", quality=88, optimize=True, progressive=True)


required_paths = [
    BLEND_PATH,
    GLB_PATH,
    CONFIG_PATH,
    ANIMATION_VALIDATION_PATH,
    RAW_REVIEW_DIR / "fox-baseline-v2_metrics.json",
    RAW_REVIEW_DIR / "fox-v2-pass1_metrics.json",
    RAW_REVIEW_DIR / "fox-v2-pass1_review.json",
    *(RAW_REVIEW_DIR / filename for filename in CONTACT_SOURCES.values()),
]
missing = [str(path) for path in required_paths if not path.is_file()]
if missing:
    raise FileNotFoundError(f"Proxy v2 checkpoint inputs are missing: {missing}")

FINAL_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
for existing in FINAL_REVIEW_DIR.iterdir():
    if existing.is_file():
        existing.unlink()
    elif existing.is_dir():
        shutil.rmtree(existing)

contact_outputs = {}
for key, filename in CONTACT_SOURCES.items():
    destination = FINAL_REVIEW_DIR / f"{key.replace('_', '-')}-contact.jpg"
    convert_contact(RAW_REVIEW_DIR / filename, destination)
    contact_outputs[key] = file_info(destination)

baseline_metrics_path = FINAL_REVIEW_DIR / "baseline-v1-metrics.json"
v2_metrics_path = FINAL_REVIEW_DIR / "model-v2-metrics.json"
baseline_metrics = copy_json(
    RAW_REVIEW_DIR / "fox-baseline-v2_metrics.json",
    baseline_metrics_path,
)
v2_metrics = copy_json(
    RAW_REVIEW_DIR / "fox-v2-pass1_metrics.json",
    v2_metrics_path,
)
model_review = json.loads(
    (RAW_REVIEW_DIR / "fox-v2-pass1_review.json").read_text(encoding="utf-8")
)
animation_validation = json.loads(ANIMATION_VALIDATION_PATH.read_text(encoding="utf-8"))
glb = parse_glb(GLB_PATH)
config_text = CONFIG_PATH.read_text(encoding="utf-8")

baseline_error = float(baseline_metrics["combined_mean_absolute_width_error"])
v2_error = float(v2_metrics["combined_mean_absolute_width_error"])
error_reduction = (baseline_error - v2_error) / baseline_error
if v2_error >= baseline_error:
    raise RuntimeError(
        f"Proxy v2 silhouette did not improve: baseline={baseline_error} v2={v2_error}"
    )
if error_reduction < 0.50:
    raise RuntimeError(f"Proxy v2 silhouette improvement is below 50%: {error_reduction:.2%}")
if model_review.get("warnings"):
    raise RuntimeError(f"Proxy v2 review contains warnings: {model_review['warnings']}")
if model_review["geometry"]["totals"] != {
    "objects": 44,
    "mesh_objects": 44,
    "vertices": 814,
    "edges": 2000,
    "polygons": 1274,
    "triangles": 1452,
}:
    raise RuntimeError(f"Unexpected proxy v2 geometry totals: {model_review['geometry']['totals']}")
expected_actions = ["idle", "sitting", "walking", "wave"]
if sorted(name for name in glb["animations"] if name) != expected_actions:
    raise RuntimeError(f"Unexpected GLB animations: {glb['animations']}")
if glb["meshes"] != 44 or glb["skins"] != 1 or glb["materials"] != 4:
    raise RuntimeError(f"Unexpected GLB structure: {glb}")
if '"/models/chatgpt-fox-proxy-v2.glb"' not in config_text:
    raise RuntimeError("Local player configuration does not point to proxy v2")

all_ground_values = [
    float(value)
    for frames in animation_validation["ground_minimums"].values()
    for value in frames.values()
]
if min(all_ground_values) < -0.03:
    raise RuntimeError(
        f"Animation validation exceeds floor tolerance: minimum z={min(all_ground_values)}"
    )

manifest = {
    "stage": "proxy_v2_integrated_and_validated",
    "createdAt": datetime.now(timezone.utc).isoformat(),
    "character": "chatgpt-fox",
    "version": 2,
    "rollback": {
        "blend": "assets/concepts/chatgpt-fox/blender/chatgpt_fox_references.blend",
        "glb": "client/public/models/chatgpt-fox-proxy-v1.glb",
    },
    "outputs": {
        "blend": file_info(BLEND_PATH),
        "glb": file_info(GLB_PATH),
        "gameModelUrl": "/models/chatgpt-fox-proxy-v2.glb",
        "gameScale": 0.32,
    },
    "model": {
        "changes": [
            "narrower relaxed A-pose",
            "lower side-swept tail",
            "larger paws",
            "layered fox cheeks and muzzle",
            "separate nose, inner ears, eyes and cyan pupils",
        ],
        "bounds": model_review["bounds"],
        "geometry": model_review["geometry"],
        "materials": model_review["geometry"]["materials"],
        "warnings": model_review["warnings"],
        "restoration": model_review["restoration"],
    },
    "silhouette": {
        "baselineCombinedMeanAbsoluteWidthError": baseline_error,
        "v2CombinedMeanAbsoluteWidthError": v2_error,
        "relativeErrorReduction": round(error_reduction, 4),
        "frontMeanAbsoluteWidthError": {
            "baseline": baseline_metrics["front_comparison"]["mean_absolute_width_error"],
            "v2": v2_metrics["front_comparison"]["mean_absolute_width_error"],
        },
        "sideMeanAbsoluteWidthError": {
            "baseline": baseline_metrics["side_comparison"]["mean_absolute_width_error"],
            "v2": v2_metrics["side_comparison"]["mean_absolute_width_error"],
        },
        "metrics": {
            "baseline": file_info(baseline_metrics_path),
            "v2": file_info(v2_metrics_path),
        },
    },
    "rig": {
        "bones": 24,
        "binding": "rigid bone-parented proxy",
        "actions": animation_validation["actions"],
        "animationValidation": file_info(ANIMATION_VALIDATION_PATH),
        "groundMinimums": animation_validation["ground_minimums"],
        "minimumValidatedZ": min(all_ground_values),
    },
    "glb": glb,
    "reviews": contact_outputs,
}
MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(
    json.dumps(
        {
            "manifest": file_info(MANIFEST_PATH),
            "reviewDirectory": str(FINAL_REVIEW_DIR.relative_to(ROOT)).replace("\\", "/"),
            "contacts": contact_outputs,
            "silhouetteErrorReduction": round(error_reduction, 4),
            "glb": glb,
            "minimumValidatedZ": min(all_ground_values),
        },
        indent=2,
    )
)
