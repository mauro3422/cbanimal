from __future__ import annotations

import json
import struct
from pathlib import Path

import bpy

MODEL_COLLECTION = "MODEL_PROXY"
RIG_COLLECTION = "RIG_GUIDE"
RIG_NAME = "FOX_RIG_GUIDE"
EXPORT_PATH = Path(r"C:\dev\cbanimal\client\public\models\chatgpt-fox-proxy-v2.glb")


def parse_glb_header(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20:
        raise RuntimeError("Exported GLB is too small")
    magic, version, total_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total_length != len(data):
        raise RuntimeError(
            f"Invalid GLB header: magic={magic!r} version={version} declared={total_length} actual={len(data)}"
        )
    json_length, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise RuntimeError(f"First GLB chunk is not JSON: {json_type!r}")
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


model = bpy.data.collections.get(MODEL_COLLECTION)
rig_collection = bpy.data.collections.get(RIG_COLLECTION)
armature = bpy.data.objects.get(RIG_NAME)
if model is None or rig_collection is None or armature is None:
    raise RuntimeError("MODEL_PROXY, RIG_GUIDE, and FOX_RIG_GUIDE must exist before export")

missing_parenting = []
for obj in model.objects:
    if obj.type != "MESH":
        continue
    if obj.parent != armature or obj.parent_type != "BONE" or not obj.parent_bone:
        missing_parenting.append(obj.name)
if missing_parenting:
    raise RuntimeError(f"Proxy v2 contains unbound objects: {sorted(missing_parenting)}")

required_actions = ["idle", "walking", "sitting", "wave"]
missing_actions = [name for name in required_actions if bpy.data.actions.get(name) is None]
if missing_actions:
    raise RuntimeError(f"Proxy v2 is missing actions: {missing_actions}")

armature.animation_data_create()
armature.animation_data.action = bpy.data.actions["idle"]
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 40
bpy.context.scene.frame_set(1)

for collection_name in ("REFERENCES", "BLOCKOUT"):
    collection = bpy.data.collections.get(collection_name)
    if collection is not None:
        collection.hide_viewport = True
        collection.hide_render = True
model.hide_viewport = False
model.hide_render = False
rig_collection.hide_viewport = False
rig_collection.hide_render = True
armature.hide_set(False)
armature.hide_viewport = False
armature.hide_render = True

bpy.ops.object.select_all(action="DESELECT")
armature.select_set(True)
for obj in model.objects:
    if obj.type == "MESH":
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
bpy.context.view_layer.objects.active = armature

EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
result = bpy.ops.export_scene.gltf(
    filepath=str(EXPORT_PATH),
    export_format="GLB",
    use_selection=True,
    export_yup=True,
    export_apply=False,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_anim_single_armature=True,
    export_force_sampling=True,
    export_optimize_animation_size=True,
    export_optimize_animation_keep_anim_armature=True,
    export_skins=True,
    export_morph=False,
    export_cameras=False,
    export_lights=False,
    export_extras=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
)
if "FINISHED" not in result:
    raise RuntimeError(f"glTF export failed: {result}")

structure = parse_glb_header(EXPORT_PATH)
if structure["meshes"] != len([obj for obj in model.objects if obj.type == "MESH"]):
    raise RuntimeError(f"Unexpected exported mesh count: {structure}")
if structure["skins"] != 1:
    raise RuntimeError(f"Expected one exported skin: {structure}")
if sorted(name for name in structure["animations"] if name) != sorted(required_actions):
    raise RuntimeError(f"Unexpected animation names: {structure['animations']}")

bpy.context.scene["cbanimal_character_stage"] = "model_proxy_v2_exported"
bpy.context.scene["cbanimal_proxy_v2_glb"] = str(EXPORT_PATH)
bpy.context.scene["cbanimal_proxy_v2_glb_bytes"] = structure["bytes"]
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

print(
    "CBANIMAL_PROXY_V2_EXPORT_RESULT",
    {
        "glb": str(EXPORT_PATH),
        "export_result": sorted(result),
        **structure,
    },
)
