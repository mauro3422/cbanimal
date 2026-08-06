from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

RIG_NAME = "FOX_RIG_GUIDE"
MODEL_COLLECTION = "MODEL_PROXY"
ACTION_NAMES = ("idle", "walking", "sitting", "wave", "laugh", "angry", "sleep")
VALIDATION_PATH = Path(
    r"C:\dev\cbanimal\assets\concepts\chatgpt-fox\blender\proxy-v5-animation-validation.json"
)
IK_VALIDATION_PATH = Path(
    r"C:\dev\cbanimal\assets\concepts\chatgpt-fox\blender\proxy-v5-ik-walk-validation.json"
)

armature = bpy.data.objects.get(RIG_NAME)
model = bpy.data.collections.get(MODEL_COLLECTION)
if armature is None or armature.type != "ARMATURE" or model is None:
    raise RuntimeError("Proxy v5 armature and MODEL_PROXY collection must exist")

missing_actions = [name for name in ACTION_NAMES if bpy.data.actions.get(name) is None]
if missing_actions:
    raise RuntimeError(f"Proxy v5 is missing required actions: {missing_actions}")

required_knee_bones = {
    "knee.L": "thigh.L",
    "knee.R": "thigh.R",
}
for bone_name, expected_parent in required_knee_bones.items():
    bone = armature.data.bones.get(bone_name)
    if bone is None:
        raise RuntimeError(f"Proxy v5 is missing articulated knee bone: {bone_name}")
    if bone.parent is None or bone.parent.name != expected_parent:
        raise RuntimeError(f"{bone_name} must be parented to {expected_parent}")
    if bone.use_deform:
        raise RuntimeError(f"{bone_name} is a presentation joint and must not deform vertices")

required_knee_meshes = {
    "MDL_KNEE_L": "knee.L",
    "MDL_KNEE_R": "knee.R",
}
for object_name, expected_bone in required_knee_meshes.items():
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        raise RuntimeError(f"Proxy v5 is missing knee mesh: {object_name}")
    if obj.parent != armature or obj.parent_type != "BONE" or obj.parent_bone != expected_bone:
        raise RuntimeError(f"{object_name} must be attached to {expected_bone}")


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
    "MDL_THIGH_L",
    "MDL_THIGH_R",
    "MDL_KNEE_L",
    "MDL_KNEE_R",
    "MDL_SHIN_L",
    "MDL_SHIN_R",
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
    """Return exact evaluated mesh-vertex bounds, not stale object bound boxes."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    minimum = Vector((float("inf"), float("inf"), float("inf")))
    maximum = Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in mesh_objects:
        evaluated = obj.evaluated_get(depsgraph)
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


if not IK_VALIDATION_PATH.is_file():
    raise FileNotFoundError(IK_VALIDATION_PATH)
ik_walk = json.loads(IK_VALIDATION_PATH.read_text(encoding="utf-8"))
if ik_walk.get("stage") != "proxy_v5_ik_walk_mathematically_validated":
    raise RuntimeError(f"Unexpected IK walk stage: {ik_walk.get('stage')}")
ik_kinematics = ik_walk.get("kinematics", {})
ik_validation = ik_walk.get("validation", {})
if ik_kinematics.get("frameRange") != [1, 13]:
    raise RuntimeError(f"Walking action must use the verified 1-13 frame cycle: {ik_kinematics}")
if abs(float(ik_kinematics.get("fps", 0.0)) - 24.0) > 1e-6:
    raise RuntimeError(f"Walking validation must use 24 fps: {ik_kinematics}")
if abs(float(ik_kinematics.get("durationSeconds", 0.0)) - 0.5) > 1e-6:
    raise RuntimeError(f"Walking cycle duration changed: {ik_kinematics}")
if abs(float(ik_kinematics.get("runtimeScale", 0.0)) - 0.32) > 1e-6:
    raise RuntimeError(f"Walking runtime scale changed: {ik_kinematics}")
if abs(float(ik_kinematics.get("referenceSpeed", 0.0)) - 1.688) > 1e-6:
    raise RuntimeError(f"Walking/player speed contract changed: {ik_kinematics}")
if abs(float(ik_kinematics.get("strideHalfBlender", 0.0)) - 0.65) > 1e-6:
    raise RuntimeError(f"Walking stride changed: {ik_kinematics}")
if abs(float(ik_kinematics.get("stanceFraction", 0.0)) - 0.5) > 1e-6:
    raise RuntimeError(f"Walking stance fraction changed: {ik_kinematics}")

checks = {
    "idle": evaluate("idle", [1, 20, 40]),
    "walking": evaluate("walking", [1, 2, 4, 6, 7, 8, 10, 12, 13]),
    "sitting": evaluate("sitting", [1, 12, 24]),
    "wave": evaluate("wave", [1, 10, 20, 30, 40, 48]),
    "laugh": evaluate("laugh", [1, 8, 16, 24, 32, 48]),
    "angry": evaluate("angry", [1, 10, 18, 26, 34, 48]),
    "sleep": evaluate("sleep", [1, 12, 36, 60, 72]),
}

walking_action_range = [round(float(value), 3) for value in bpy.data.actions["walking"].frame_range]
if walking_action_range != [1.0, 13.0]:
    raise RuntimeError(f"Walking action frame range changed: {walking_action_range}")

walk_joint_samples: dict[str, dict] = {}
walk_body_motion = {
    "cycleDurationSeconds": float(ik_kinematics["durationSeconds"]),
    "fps": float(ik_kinematics["fps"]),
    "runtimeScale": float(ik_kinematics["runtimeScale"]),
    "referenceSpeed": float(ik_kinematics["referenceSpeed"]),
    "expectedStanceFootSpeed": float(ik_kinematics["expectedStanceFootSpeed"]),
    "stanceFraction": float(ik_kinematics["stanceFraction"]),
    "strideSweepRuntime": round(
        float(ik_kinematics["strideHalfBlender"])
        * 2.0
        * float(ik_kinematics["runtimeScale"]),
        6,
    ),
    "legs": {},
}

for side in ("L", "R"):
    leg = ik_validation.get("legs", {}).get(side)
    if not isinstance(leg, dict):
        raise RuntimeError(f"IK walking validation is missing leg {side}")
    flexion_range = [float(value) for value in leg.get("kneeFlexionRangeDegrees", [])]
    support_z = [float(value) for value in leg.get("supportFootMinimumZRange", [])]
    swing_clearance = [float(value) for value in leg.get("swingFootClearanceRange", [])]
    support_speed = [float(value) for value in leg.get("supportFootSpeedRuntimeRange", [])]
    upper_length = [float(value) for value in leg.get("upperLengthRange", [])]
    lower_length = [float(value) for value in leg.get("lowerLengthRange", [])]
    if len(flexion_range) != 2 or not 25.0 <= flexion_range[0] <= 40.0 or not 95.0 <= flexion_range[1] <= 105.0:
        raise RuntimeError(f"Leg {side} knee range is not a complete stance/swing cycle: {leg}")
    if len(support_z) != 2 or support_z[0] < -0.001 or support_z[1] > 0.01:
        raise RuntimeError(f"Leg {side} support foot is not planted: {leg}")
    if len(swing_clearance) != 2 or swing_clearance[0] < 0.08 or swing_clearance[1] < 0.50:
        raise RuntimeError(f"Leg {side} swing foot clearance is invalid: {leg}")
    if len(support_speed) != 2 or support_speed[0] < 1.35 or support_speed[1] > 2.10:
        raise RuntimeError(f"Leg {side} stance-foot speed is inconsistent: {leg}")
    if float(leg.get("referenceSpeedErrorPercent", 100.0)) > 3.0:
        raise RuntimeError(f"Leg {side} does not match the runtime translation speed: {leg}")
    if len(upper_length) != 2 or upper_length[1] - upper_length[0] > 1e-5:
        raise RuntimeError(f"Leg {side} upper segment changes length: {leg}")
    if len(lower_length) != 2 or lower_length[1] - lower_length[0] > 1e-5:
        raise RuntimeError(f"Leg {side} lower segment changes length: {leg}")

    frame_report = ik_kinematics.get("frameReport", {})
    thigh_angles = [
        float(frame["legs"][side]["solution"]["thighDegrees"])
        for frame in frame_report.values()
    ]
    extension_ratios = [
        float(frame["legs"][side]["solution"]["extensionRatio"])
        for frame in frame_report.values()
    ]
    if max(thigh_angles) - min(thigh_angles) < 55.0:
        raise RuntimeError(f"Leg {side} thigh does not perform a readable full step: {thigh_angles}")
    if max(extension_ratios) > 0.970001:
        raise RuntimeError(f"Leg {side} exceeds the 97% extension limit: {extension_ratios}")

    walk_body_motion["legs"][side] = {
        **leg,
        "thighAngleRangeDegrees": [round(min(thigh_angles), 6), round(max(thigh_angles), 6)],
        "maximumExtensionRatio": round(max(extension_ratios), 6),
    }
frame_report = ik_kinematics.get("frameReport", {})
pelvis_lateral_values = [float(frame["pelvisLocation"][0]) for frame in frame_report.values()]
pelvis_vertical_values = [float(frame["pelvisLocation"][1]) for frame in frame_report.values()]
pelvis_lateral_travel = max(pelvis_lateral_values) - min(pelvis_lateral_values)
pelvis_vertical_travel = max(pelvis_vertical_values) - min(pelvis_vertical_values)
if not 0.12 <= pelvis_lateral_travel <= 0.16:
    raise RuntimeError(f"Walking pelvis weight shift is invalid: {pelvis_lateral_travel}")
if not 0.07 <= pelvis_vertical_travel <= 0.12:
    raise RuntimeError(f"Walking pelvis rise/fall is invalid: {pelvis_vertical_travel}")
walk_body_motion["pelvisLateralTravel"] = round(pelvis_lateral_travel, 6)
walk_body_motion["pelvisVerticalTravel"] = round(pelvis_vertical_travel, 6)
walk_body_motion["poseFrames"] = {
    "contactLeft": 1,
    "compressionLeft": 2,
    "passingLeft": 4,
    "elevationLeft": 6,
    "contactRight": 7,
    "compressionRight": 8,
    "passingRight": 10,
    "elevationRight": 12,
}


for frame, sample in ik_validation.get("samples", {}).items():
    frame_payload: dict[str, object] = {"legs": {}}
    for side in ("L", "R"):
        leg_sample = sample["legs"][side]
        frame_payload["legs"][side] = {
            "stance": bool(leg_sample["stance"]),
            "worldKneeFlexionDegrees": float(leg_sample["worldKneeFlexionDegrees"]),
            "footMinimumZ": float(leg_sample["footBounds"]["minimum"][2]),
            "upperLength": float(leg_sample["upperLength"]),
            "lowerLength": float(leg_sample["lowerLength"]),
            "hip": leg_sample["hip"],
            "knee": leg_sample["knee"],
            "ankle": leg_sample["ankle"],
        }
    walk_joint_samples[str(frame)] = frame_payload

for frame, sample in checks["walking"].items():
    minimum_z = float(sample["bounds"]["minimum"][2])
    if minimum_z < -0.01 or minimum_z > 0.01:
        raise RuntimeError(
            f"Walking evaluated mesh vertices are not grounded at frame {frame}: {minimum_z}"
        )

if distance(
    tuple(checks["walking"]["1"]["positions"]["MDL_HAND_R"]),
    tuple(checks["walking"]["7"]["positions"]["MDL_HAND_R"]),
) < 0.20:
    raise RuntimeError("Walking validation failed: right hand counter-swing is too small")
if distance(
    tuple(checks["walking"]["1"]["positions"]["MDL_TAIL_TIP"]),
    tuple(checks["walking"]["4"]["positions"]["MDL_TAIL_TIP"]),
) < 0.10:
    raise RuntimeError("Walking validation failed: tail counterbalance is too small")


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

laugh = checks["laugh"]
if distance(tuple(laugh["8"]["positions"]["MDL_HEAD"]), tuple(laugh["16"]["positions"]["MDL_HEAD"])) < 0.08:
    raise RuntimeError("Laugh validation failed: head bob is too small")
if distance(tuple(laugh["8"]["positions"]["MDL_TAIL_TIP"]), tuple(laugh["16"]["positions"]["MDL_TAIL_TIP"])) < 0.12:
    raise RuntimeError("Laugh validation failed: tail wag is too small")
if distance(tuple(laugh["1"]["positions"]["MDL_HEAD"]), tuple(laugh["48"]["positions"]["MDL_HEAD"])) > 0.03:
    raise RuntimeError("Laugh validation failed: final pose does not return to rest")

angry = checks["angry"]
for hand_name in ("MDL_HAND_L", "MDL_HAND_R"):
    if distance(tuple(angry["1"]["positions"][hand_name]), tuple(angry["10"]["positions"][hand_name])) < 0.30:
        raise RuntimeError(f"Angry validation failed: {hand_name} did not reach the angry pose")
if distance(tuple(angry["18"]["positions"]["MDL_HAND_R"]), tuple(angry["26"]["positions"]["MDL_HAND_R"])) < 0.20:
    raise RuntimeError("Angry validation failed: clenched-fist shake is too small")
if distance(tuple(angry["1"]["positions"]["MDL_HEAD"]), tuple(angry["48"]["positions"]["MDL_HEAD"])) > 0.03:
    raise RuntimeError("Angry validation failed: final pose does not return to rest")

sleep = checks["sleep"]
if distance(tuple(sleep["1"]["positions"]["MDL_HEAD"]), tuple(sleep["36"]["positions"]["MDL_HEAD"])) < 0.15:
    raise RuntimeError("Sleep validation failed: head droop is too small")
if distance(tuple(sleep["12"]["positions"]["MDL_HEAD"]), tuple(sleep["36"]["positions"]["MDL_HEAD"])) < 0.015:
    raise RuntimeError("Sleep validation failed: breathing motion is too small")
if distance(tuple(sleep["1"]["positions"]["MDL_HEAD"]), tuple(sleep["72"]["positions"]["MDL_HEAD"])) < 0.12:
    raise RuntimeError("Sleep validation failed: final pose does not remain asleep")

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
bpy.context.scene["cbanimal_proxy_v5_animation_stage"] = "seven_gameplay_clips_validated"
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

payload = {
    "stage": "proxy_v5_animations_and_deformation_validated",
    "blend": bpy.data.filepath,
    "actions": list(ACTION_NAMES),
    "frameRanges": {
        name: [round(float(value), 3) for value in bpy.data.actions[name].frame_range]
        for name in ACTION_NAMES
    },
    "runtimePolicy": {
        "loop": ["idle", "walking"],
        "once": ["sitting", "wave", "laugh", "angry", "sleep"],
    },
    "rig": {
        "bones": len(armature.data.bones),
        "kneeBones": {
            name: {
                "parent": armature.data.bones[name].parent.name,
                "useDeform": armature.data.bones[name].use_deform,
            }
            for name in required_knee_bones
        },
    },
    "meshBindings": {obj.name: binding_kind(obj) for obj in mesh_objects},
    "deformingObjects": deforming_report,
    "kneeMotion": walk_joint_samples,
    "walkBodyMotion": walk_body_motion,
    "minimumValidatedZ": round(minimum_z, 5),
    "floorMinimums": floor_minimums,
    "checks": checks,
}
VALIDATION_PATH.parent.mkdir(parents=True, exist_ok=True)
VALIDATION_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print("CBANIMAL_PROXY_V5_ANIMATION_RESULT", payload)
