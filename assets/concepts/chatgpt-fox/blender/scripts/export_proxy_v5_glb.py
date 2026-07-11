from __future__ import annotations

import json
import struct
from pathlib import Path

import bpy

MODEL_COLLECTION = "MODEL_PROXY"
RIG_COLLECTION = "RIG_GUIDE"
RIG_NAME = "FOX_RIG_GUIDE"
REQUIRED_ACTIONS = ("idle", "walking", "sitting", "wave")
EXPORT_PATH = Path(
    r"C:\dev\cbanimal\client\public\models\chatgpt-fox-proxy-v5.glb"
)


def parse_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20:
        raise RuntimeError("Exported proxy v5 GLB is too small")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise RuntimeError(
            f"Invalid GLB header: magic={magic!r} version={version} "
            f"declared={declared_length} actual={len(data)}"
        )
    json_length, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise RuntimeError(f"Unexpected first GLB chunk: {json_type!r}")
    payload = json.loads(data[20 : 20 + json_length].decode("utf-8"))
    return {
        "bytes": len(data),
        "nodes": len(payload.get("nodes", [])),
        "meshes": len(payload.get("meshes", [])),
        "materials": len(payload.get("materials", [])),
        "skins": len(payload.get("skins", [])),
        "animations": [entry.get("name") for entry in payload.get("animations", [])],
        "scenes": len(payload.get("scenes", [])),
    }


def binding_kind(obj: bpy.types.Object, armature: bpy.types.Object) -> str:
    if obj.parent == armature and obj.parent_type == "BONE" and obj.parent_bone:
        return f"bone:{obj.parent_bone}"
    for modifier in obj.modifiers:
        if modifier.type == "ARMATURE" and modifier.object == armature:
            return "armature_modifier"
    return "unbound"


model = bpy.data.collections.get(MODEL_COLLECTION)
rig_collection = bpy.data.collections.get(RIG_COLLECTION)
armature = bpy.data.objects.get(RIG_NAME)
if model is None or rig_collection is None or armature is None or armature.type != "ARMATURE":
    raise RuntimeError("MODEL_PROXY, RIG_GUIDE and FOX_RIG_GUIDE are required")

mesh_objects = sorted(
    (obj for obj in model.objects if obj.type == "MESH"), key=lambda obj: obj.name
)
if len(mesh_objects) != 47:
    raise RuntimeError(f"Expected 47 visible v5 meshes, found {len(mesh_objects)}")

bindings = {obj.name: binding_kind(obj, armature) for obj in mesh_objects}
unbound = sorted(name for name, binding in bindings.items() if binding == "unbound")
if unbound:
    raise RuntimeError(f"Proxy v5 contains unbound runtime meshes: {unbound}")
expected_deforming = {
    "MDL_V5_BODY": "armature_modifier",
    "MDL_V5_TAIL_ROOT": "armature_modifier",
}
for object_name, expected in expected_deforming.items():
    if bindings.get(object_name) != expected:
        raise RuntimeError(
            f"{object_name} binding mismatch: expected {expected}, got {bindings.get(object_name)}"
        )

missing_actions = [name for name in REQUIRED_ACTIONS if bpy.data.actions.get(name) is None]
if missing_actions:
    raise RuntimeError(f"Proxy v5 is missing actions: {missing_actions}")

armature.animation_data_create()
armature.animation_data.action = bpy.data.actions["idle"]
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 40
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()

for collection_name in ("REFERENCES", "BLOCKOUT", "V3_RIGID_BODY_ARCHIVE"):
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
for obj in mesh_objects:
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

structure = parse_glb(EXPORT_PATH)
if structure["meshes"] != len(mesh_objects):
    raise RuntimeError(f"Unexpected exported mesh count: {structure}")
if structure["materials"] != 4:
    raise RuntimeError(f"Expected four exported materials: {structure}")
if structure["skins"] != 1:
    raise RuntimeError(f"Expected one exported skin: {structure}")
if sorted(name for name in structure["animations"] if name) != sorted(REQUIRED_ACTIONS):
    raise RuntimeError(f"Unexpected animation names: {structure['animations']}")

bpy.context.scene["cbanimal_character_stage"] = "model_proxy_v5_exported"
bpy.context.scene["cbanimal_proxy_v5_glb"] = str(EXPORT_PATH)
bpy.context.scene["cbanimal_proxy_v5_glb_bytes"] = structure["bytes"]
bpy.context.scene["cbanimal_proxy_v5_mesh_bindings"] = json.dumps(bindings, sort_keys=True)
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

print(
    "CBANIMAL_PROXY_V5_EXPORT_RESULT",
    {
        "glb": str(EXPORT_PATH),
        "export_result": sorted(result),
        "deforming": sorted(expected_deforming),
        **structure,
    },
)
