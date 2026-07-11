from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

RIG_NAME = "FOX_RIG_GUIDE"
MODEL_COLLECTION = "MODEL_PROXY"
ACTION_NAMES = ("idle", "walking", "sitting", "wave")
VALIDATION_PATH = Path(
    r"C:\dev\cbanimal\assets\concepts\chatgpt-fox\blender\proxy-v5-animation-validation.json"
)

armature = bpy.data.objects.get(RIG_NAME)
model = bpy.data.collections.get(MODEL_COLLECTION)
if armature is None or armature.type != "ARMATURE" or model is None:
    raise RuntimeError("Proxy v5 armature and MODEL_PROXY collection must exist")

missing_actions = [name for name in ACTION_NAMES if bpy.data.actions.get(name) is None]
if missing_actions:
    raise RuntimeError(f"Proxy v5 is missing required actions: {missing_actions}")


def armature_modifier(obj: bpy.types.Object) -> bpy.types.ArmatureModifier | None:
    for modifier in obj.modifiers:
        if modifier.type == "ARMATURE" and modifier.object == armature:
            return modifier
    return None


def binding_kind(obj: bpy.types.Object) -> str:
    if obj.parent == armature and obj.parent_type == "BONE" and obj.parent_bone:
        return f"bone:{obj.parent_bone}"
    if armature_modifier(obj) is not None:
        return "armature_modifier"
    return "unbound"


mesh_objects = sorted(
    (obj for obj in model.objects if obj.type == "MESH"), key=lambda obj: obj.name
)
unbound = [obj.name for obj in mesh_objects if binding_kind(obj) == "unbound"]
if unbound:
    raise RuntimeError(f"Proxy v5 contains unbound runtime meshes: {unbound}")

required_deforming = {
    "MDL_V5_BODY": {"pelvis", "spine", "chest", "neck"},
    "MDL_V5_TAIL_ROOT": {"pelvis", "tail.01"},
}
deforming_report: dict[str, dict] = {}
for object_name, expected_groups in required_deforming.items():
    obj = bpy.data.objects.get(object_name)
    if obj is None or obj.name not in model.objects:
        raise RuntimeError(f"Proxy v5 is missing deforming object: {object_name}")
    modifier = armature_modifier(obj)
    if modifier is None:
        raise RuntimeError(f"{object_name} must have an armature modifier")
    group_names = {group.name for group in obj.vertex_groups}
    if not expected_groups.issubset(group_names):
        raise RuntimeError(
            f"{object_name} is missing vertex groups: {sorted(expected_groups - group_names)}"
        )
    unweighted = []
    for vertex in obj.data.vertices:
        total = sum(
            element.weight
            for element in vertex.groups
            if element.group < len(obj.vertex_groups)
        )
        if total < 0.999:
            unweighted.append(vertex.index)
    if unweighted:
        raise RuntimeError(
            f"{object_name} has insufficiently weighted vertices: {unweighted[:12]}"
        )
    deforming_report[object_name] = {
        "vertices": len(obj.data.vertices),
        "groups": sorted(group_names),
        "modifier": modifier.name,
    }

tracked_objects = (
    "MDL_HAND_L",
    "MDL_HAND_R",
    "MDL_FOOT_L",
    "MDL_FOOT_R",
    "MDL_TAIL_TIP",
    "MDL_HEAD",
)


def world_position(name: str) -> tuple[float, float, float]:
    return tuple(float(value) for value in bpy.data.objects[name].matrix_world.translation)


def bone_head_world(name: str) -> tuple[float, float, float]:
    return tuple(float(value) for value in (armature.matrix_world @ armature.pose.bones[name].head))


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum((left - right) ** 2 for left, right in zip(a, b)) ** 0.5


def finite(values: list[float]) -> bool:
    return all(math.isfinite(value) for value in values)


def evaluated_object_bounds(obj: bpy.types.Object) -> dict[str, list[float]]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    minimum = Vector((float("inf"), float("inf"), float("inf")))
    maximum = Vector((float("-inf"), float("-inf"), float("-inf")))
    mesh = evaluated.to_mesh()
    try:
        for vertex in mesh.vertices:
            world = evaluated.matrix_world @ vertex.co
            minimum.x = min(minimum.x, world.x)
            minimum.y = min(minimum.y, world.y)
            minimum.z = min(minimum.z, world.z)
            maximum.x = max(maximum.x, world.x)
            maximum.y = max(maximum.y, world.y)
            maximum.z = max(maximum.z, world.z)
    finally:
        evaluated.to_mesh_clear()
    values = list(minimum) + list(maximum)
    if not finite(values):
        raise RuntimeError(f"Non-finite evaluated bounds for {obj.name}")
    dimensions = [maximum[index] - minimum[index] for index in range(3)]
    if max(dimensions) > 8.0 or min(dimensions) <= 0.0:
        raise RuntimeError(f"Implausible evaluated bounds for {obj.name}: {dimensions}")
    return {
        "minimum": [round(value, 5) for value in minimum],
        "maximum": [round(value, 5) for value in maximum],
        "dimensions": [round(value, 5) for value in dimensions],
        "center": [round((minimum[index] + maximum[index]) / 2.0, 5) for index in range(3)],
    }


def evaluated_ring_center(
    obj: bpy.types.Object,
    start_index: int,
    count: int,
) -> tuple[float, float, float]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        points = [
            evaluated.matrix_world @ mesh.vertices[index].co
            for index in range(start_index, start_index + count)
        ]
    finally:
        evaluated.to_mesh_clear()
    center = sum(points, Vector()) / len(points)
    return tuple(float(value) for value in center)


def evaluated_collection_bounds() -> dict[str, list[float]]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    minimum = Vector((float("inf"), float("inf"), float("inf")))
    maximum = Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in mesh_objects:
        evaluated = obj.evaluated_get(depsgraph)
        for corner in evaluated.bound_box:
            world = evaluated.matrix_world @ Vector(corner)
            minimum.x = min(minimum.x, world.x)
            minimum.y = min(minimum.y, world.y)
            minimum.z = min(minimum.z, world.z)
            maximum.x = max(maximum.x, world.x)
            maximum.y = max(maximum.y, world.y)
            maximum.z = max(maximum.z, world.z)
    values = list(minimum) + list(maximum)
    if not finite(values):
        raise RuntimeError("Non-finite proxy collection bounds")
    return {
        "minimum": [round(value, 5) for value in minimum],
        "maximum": [round(value, 5) for value in maximum],
        "dimensions": [round(maximum[index] - minimum[index], 5) for index in range(3)],
    }


def evaluate(action_name: str, frames: list[int]) -> dict[str, dict]:
    armature.animation_data_create()
    armature.animation_data.action = bpy.data.actions[action_name]
    result: dict[str, dict] = {}
    body = bpy.data.objects["MDL_V5_BODY"]
    tail_root = bpy.data.objects["MDL_V5_TAIL_ROOT"]
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        result[str(frame)] = {
            "positions": {
                name: [round(value, 5) for value in world_position(name)]
                for name in tracked_objects
            },
            "pelvisBoneHead": [round(value, 5) for value in bone_head_world("pelvis")],
            "bounds": evaluated_collection_bounds(),
            "bodyBounds": evaluated_object_bounds(body),
            "tailRootBounds": evaluated_object_bounds(tail_root),
            "tailRootTipCenter": [
                round(value, 5)
                for value in evaluated_ring_center(tail_root, 48, 12)
            ],
        }
    return result


checks = {
    "idle": evaluate("idle", [1, 20, 40]),
    "walking": evaluate("walking", [1, 9, 17, 25, 32]),
    "sitting": evaluate("sitting", [1, 12, 24]),
    "wave": evaluate("wave", [1, 10, 20, 30, 40, 48]),
}

walk = checks["walking"]
if distance(tuple(walk["1"]["positions"]["MDL_FOOT_R"]), tuple(walk["17"]["positions"]["MDL_FOOT_R"])) < 0.45:
    raise RuntimeError("Walking validation failed: right foot travel is too small")
if distance(tuple(walk["1"]["positions"]["MDL_HAND_R"]), tuple(walk["17"]["positions"]["MDL_HAND_R"])) < 0.20:
    raise RuntimeError("Walking validation failed: right hand swing is too small")
if distance(tuple(walk["1"]["positions"]["MDL_TAIL_TIP"]), tuple(walk["17"]["positions"]["MDL_TAIL_TIP"])) < 0.12:
    raise RuntimeError("Walking validation failed: tail sway is too small")
if distance(tuple(walk["1"]["tailRootTipCenter"]), tuple(walk["17"]["tailRootTipCenter"])) < 0.04:
    raise RuntimeError("Walking validation failed: deforming tail-root endpoint did not follow tail.01")

sit = checks["sitting"]
if sit["12"]["pelvisBoneHead"][2] > sit["1"]["pelvisBoneHead"][2] - 0.55:
    raise RuntimeError("Sitting validation failed: pelvis bone did not lower enough")
if distance(tuple(sit["1"]["bodyBounds"]["center"]), tuple(sit["12"]["bodyBounds"]["center"])) < 0.18:
    raise RuntimeError("Sitting validation failed: deforming body did not follow the pelvis")

wave = checks["wave"]
if wave["10"]["positions"]["MDL_HAND_R"][2] < 4.3:
    raise RuntimeError("Wave validation failed: right hand did not reach head height")
if distance(tuple(wave["10"]["positions"]["MDL_HAND_R"]), tuple(wave["20"]["positions"]["MDL_HAND_R"])) < 0.08:
    raise RuntimeError("Wave validation failed: wrist oscillation is too small")
if distance(tuple(wave["1"]["positions"]["MDL_HAND_R"]), tuple(wave["48"]["positions"]["MDL_HAND_R"])) > 0.03:
    raise RuntimeError("Wave validation failed: final pose does not return to rest")

floor_minimums = {
    action_name: {
        frame: payload["bounds"]["minimum"][2]
        for frame, payload in frames.items()
    }
    for action_name, frames in checks.items()
}
minimum_z = min(
    value
    for action_frames in floor_minimums.values()
    for value in action_frames.values()
)
if minimum_z < -0.035:
    raise RuntimeError(f"Proxy v5 penetrates the floor beyond tolerance: {minimum_z}")

armature.animation_data.action = bpy.data.actions["idle"]
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 40
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
bpy.context.scene["cbanimal_proxy_v5_animation_stage"] = "validated_existing_v3_clips_with_deformation"
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

payload = {
    "stage": "proxy_v5_animations_and_deformation_validated",
    "blend": bpy.data.filepath,
    "actions": list(ACTION_NAMES),
    "meshBindings": {obj.name: binding_kind(obj) for obj in mesh_objects},
    "deformingObjects": deforming_report,
    "minimumValidatedZ": round(minimum_z, 5),
    "floorMinimums": floor_minimums,
    "checks": checks,
}
VALIDATION_PATH.parent.mkdir(parents=True, exist_ok=True)
VALIDATION_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print("CBANIMAL_PROXY_V5_ANIMATION_RESULT", payload)
