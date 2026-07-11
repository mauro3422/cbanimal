from __future__ import annotations

from math import radians
import json
from pathlib import Path

import bpy
from mathutils import Vector

RIG_NAME = "FOX_RIG_GUIDE"
ACTION_NAMES = ("idle", "walking", "sitting", "wave")
VALIDATION_PATH = Path(
    r"C:\dev\cbanimal\assets\concepts\chatgpt-fox\blender\proxy-v2-animation-validation.json"
)


armature = bpy.data.objects.get(RIG_NAME)
if armature is None or armature.type != "ARMATURE":
    raise RuntimeError(f"{RIG_NAME} armature must exist before refining animations")

required_objects = (
    "MDL_HAND_L",
    "MDL_HAND_R",
    "MDL_FOOT_L",
    "MDL_FOOT_R",
    "MDL_PELVIS",
    "MDL_TAIL_TIP",
)
missing_objects = [name for name in required_objects if bpy.data.objects.get(name) is None]
if missing_objects:
    raise RuntimeError(f"Proxy v2 animation validation objects are missing: {missing_objects}")

armature.animation_data_create()
armature.animation_data.action = None
for name in ACTION_NAMES:
    existing = bpy.data.actions.get(name)
    if existing is not None:
        bpy.data.actions.remove(existing)


ROTATION_BONES = tuple(bone.name for bone in armature.pose.bones)
LOCATION_BONES = ("root", "pelvis")


def reset_pose() -> None:
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)


def apply_pose(
    rotations: dict[str, tuple[float, float, float]] | None = None,
    locations: dict[str, tuple[float, float, float]] | None = None,
) -> None:
    rotations = rotations or {}
    locations = locations or {}
    reset_pose()
    for bone_name, values in rotations.items():
        bone = armature.pose.bones.get(bone_name)
        if bone is None:
            raise RuntimeError(f"Animation references missing bone: {bone_name}")
        bone.rotation_euler = tuple(radians(value) for value in values)
    for bone_name, values in locations.items():
        bone = armature.pose.bones.get(bone_name)
        if bone is None:
            raise RuntimeError(f"Animation references missing bone: {bone_name}")
        bone.location = values


def key_full_pose(
    frame: int,
    rotations: dict[str, tuple[float, float, float]] | None = None,
    locations: dict[str, tuple[float, float, float]] | None = None,
) -> None:
    bpy.context.scene.frame_set(frame)
    apply_pose(rotations, locations)
    for bone_name in ROTATION_BONES:
        armature.pose.bones[bone_name].keyframe_insert(
            data_path="rotation_euler",
            frame=frame,
            group=bone_name,
        )
    for bone_name in LOCATION_BONES:
        armature.pose.bones[bone_name].keyframe_insert(
            data_path="location",
            frame=frame,
            group=bone_name,
        )


def make_action(
    name: str,
    frame_end: int,
    poses: list[
        tuple[
            int,
            dict[str, tuple[float, float, float]],
            dict[str, tuple[float, float, float]],
        ]
    ],
) -> bpy.types.Action:
    action = bpy.data.actions.new(name=name)
    action.use_fake_user = True
    armature.animation_data.action = action
    for frame, rotations, locations in poses:
        key_full_pose(frame, rotations, locations)
    try:
        action.use_frame_range = True
        action.frame_start = 1
        action.frame_end = frame_end
    except Exception:
        pass
    armature.animation_data.action = None
    return action


idle = make_action(
    "idle",
    40,
    [
        (
            1,
            {
                "chest": (0.0, 0.0, -1.0),
                "head": (0.0, 0.0, -1.5),
                "tail.01": (0.0, 0.0, -3.0),
                "tail.02": (0.0, 0.0, -2.0),
                "tail.03": (0.0, 0.0, -1.5),
                "tail.04": (0.0, 0.0, -1.0),
            },
            {"pelvis": (0.0, 0.0, 0.0)},
        ),
        (
            20,
            {
                "chest": (1.2, 0.0, 1.0),
                "head": (0.0, 0.0, 1.5),
                "tail.01": (0.0, 0.0, 4.0),
                "tail.02": (0.0, 0.0, 3.0),
                "tail.03": (0.0, 0.0, 2.0),
                "tail.04": (0.0, 0.0, 1.5),
            },
            # Pelvis local Y is the rig's world-vertical translation axis.
            {"pelvis": (0.0, 0.025, 0.0)},
        ),
        (
            40,
            {
                "chest": (0.0, 0.0, -1.0),
                "head": (0.0, 0.0, -1.5),
                "tail.01": (0.0, 0.0, -3.0),
                "tail.02": (0.0, 0.0, -2.0),
                "tail.03": (0.0, 0.0, -1.5),
                "tail.04": (0.0, 0.0, -1.0),
            },
            {"pelvis": (0.0, 0.0, 0.0)},
        ),
    ],
)

walking = make_action(
    "walking",
    32,
    [
        (
            1,
            {
                "upper_arm.L": (0.0, 22.0, 0.0),
                "upper_arm.R": (0.0, -22.0, 0.0),
                "thigh.L": (-28.0, 0.0, 0.0),
                "thigh.R": (28.0, 0.0, 0.0),
                "shin.L": (10.0, 0.0, 0.0),
                "shin.R": (-8.0, 0.0, 0.0),
                "tail.01": (0.0, 0.0, -6.0),
                "tail.02": (0.0, 0.0, -3.0),
            },
            {"pelvis": (0.0, 0.105, 0.0)},
        ),
        (
            9,
            {
                "forearm.L": (5.0, 0.0, 0.0),
                "forearm.R": (5.0, 0.0, 0.0),
                "shin.L": (-18.0, 0.0, 0.0),
                "shin.R": (12.0, 0.0, 0.0),
            },
            {"pelvis": (0.0, 0.155, 0.0)},
        ),
        (
            17,
            {
                "upper_arm.L": (0.0, -22.0, 0.0),
                "upper_arm.R": (0.0, 22.0, 0.0),
                "thigh.L": (28.0, 0.0, 0.0),
                "thigh.R": (-28.0, 0.0, 0.0),
                "shin.L": (-8.0, 0.0, 0.0),
                "shin.R": (10.0, 0.0, 0.0),
                "tail.01": (0.0, 0.0, 6.0),
                "tail.02": (0.0, 0.0, 3.0),
            },
            {"pelvis": (0.0, 0.105, 0.0)},
        ),
        (
            25,
            {
                "forearm.L": (5.0, 0.0, 0.0),
                "forearm.R": (5.0, 0.0, 0.0),
                "shin.L": (12.0, 0.0, 0.0),
                "shin.R": (-18.0, 0.0, 0.0),
            },
            {"pelvis": (0.0, 0.155, 0.0)},
        ),
        (
            32,
            {
                "upper_arm.L": (0.0, 22.0, 0.0),
                "upper_arm.R": (0.0, -22.0, 0.0),
                "thigh.L": (-28.0, 0.0, 0.0),
                "thigh.R": (28.0, 0.0, 0.0),
                "shin.L": (10.0, 0.0, 0.0),
                "shin.R": (-8.0, 0.0, 0.0),
                "tail.01": (0.0, 0.0, -6.0),
                "tail.02": (0.0, 0.0, -3.0),
            },
            {"pelvis": (0.0, 0.105, 0.0)},
        ),
    ],
)

sitting = make_action(
    "sitting",
    24,
    [
        (1, {}, {"pelvis": (0.0, 0.0, 0.0)}),
        (
            12,
            {
                "thigh.L": (50.0, 0.0, 0.0),
                "thigh.R": (50.0, 0.0, 0.0),
                "shin.L": (-105.0, 0.0, 0.0),
                "shin.R": (-105.0, 0.0, 0.0),
                "chest": (-4.0, 0.0, 0.0),
                "head": (3.0, 0.0, 0.0),
                "foot.L": (54.99016, -0.68121, 0.55996),
                "foot.R": (54.99016, 0.68121, -0.55996),
                "tail.01": (15.0, 0.0, 0.0),
            },
            # Pelvis local Y maps to world Z; -0.65 lowers the body.
            {"pelvis": (0.0, -0.65, 0.0)},
        ),
        (
            24,
            {
                "thigh.L": (50.0, 0.0, 0.0),
                "thigh.R": (50.0, 0.0, 0.0),
                "shin.L": (-105.0, 0.0, 0.0),
                "shin.R": (-105.0, 0.0, 0.0),
                "chest": (-4.0, 0.0, 0.0),
                "head": (3.0, 0.0, 0.0),
                "foot.L": (54.99016, -0.68121, 0.55996),
                "foot.R": (54.99016, 0.68121, -0.55996),
                "tail.01": (15.0, 0.0, 0.0),
            },
            {"pelvis": (0.0, -0.65, 0.0)},
        ),
    ],
)

wave = make_action(
    "wave",
    48,
    [
        (1, {}, {}),
        (
            10,
            {
                "upper_arm.R": (30.0, 0.0, -120.0),
                "forearm.R": (-30.0, 0.0, -60.0),
                "hand.R": (0.0, -8.0, -18.0),
                "head": (0.0, 0.0, -5.0),
            },
            {},
        ),
        (
            20,
            {
                "upper_arm.R": (30.0, 0.0, -120.0),
                "forearm.R": (-30.0, 0.0, -60.0),
                "hand.R": (0.0, 8.0, 18.0),
                "head": (0.0, 0.0, -5.0),
            },
            {},
        ),
        (
            30,
            {
                "upper_arm.R": (30.0, 0.0, -120.0),
                "forearm.R": (-30.0, 0.0, -60.0),
                "hand.R": (0.0, -8.0, -18.0),
                "head": (0.0, 0.0, -5.0),
            },
            {},
        ),
        (
            40,
            {
                "upper_arm.R": (30.0, 0.0, -120.0),
                "forearm.R": (-30.0, 0.0, -60.0),
                "hand.R": (0.0, 8.0, 18.0),
                "head": (0.0, 0.0, -5.0),
            },
            {},
        ),
        (48, {}, {}),
    ],
)


def world_position(object_name: str) -> tuple[float, float, float]:
    bpy.context.view_layer.update()
    return tuple(float(value) for value in bpy.data.objects[object_name].matrix_world.translation)


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum((left - right) ** 2 for left, right in zip(a, b)) ** 0.5


def model_minimum_z() -> float:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    minimum = float("inf")
    for obj in bpy.data.collections["MODEL_PROXY"].objects:
        evaluated = obj.evaluated_get(depsgraph)
        object_minimum = min(
            (evaluated.matrix_world @ Vector(corner)).z
            for corner in evaluated.bound_box
        )
        minimum = min(minimum, object_minimum)
    return float(minimum)


def evaluate_ground(action: bpy.types.Action, frames: list[int]) -> dict[int, float]:
    armature.animation_data.action = action
    minimums = {}
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        minimums[frame] = model_minimum_z()
    return minimums


def evaluate(action: bpy.types.Action, frames: list[int]) -> dict[int, dict[str, tuple[float, float, float]]]:
    armature.animation_data.action = action
    evaluated = {}
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        evaluated[frame] = {
            name: world_position(name)
            for name in required_objects
        }
    return evaluated


checks = {
    "idle": evaluate(idle, [1, 20, 40]),
    "walking": evaluate(walking, [1, 9, 17, 25, 32]),
    "sitting": evaluate(sitting, [1, 12, 24]),
    "wave": evaluate(wave, [1, 10, 20, 30, 40, 48]),
}
ground_checks = {
    "idle": evaluate_ground(idle, [1, 20, 40]),
    "walking": evaluate_ground(walking, [1, 9, 17, 25, 32]),
    "sitting": evaluate_ground(sitting, [1, 12, 24]),
    "wave": evaluate_ground(wave, [1, 10, 20, 30, 40, 48]),
}

walk = checks["walking"]
if distance(walk[1]["MDL_FOOT_R"], walk[17]["MDL_FOOT_R"]) < 0.45:
    raise RuntimeError("Walking validation failed: right foot does not travel enough")
if distance(walk[1]["MDL_HAND_R"], walk[17]["MDL_HAND_R"]) < 0.20:
    raise RuntimeError("Walking validation failed: right hand does not swing enough")
if distance(walk[1]["MDL_TAIL_TIP"], walk[17]["MDL_TAIL_TIP"]) < 0.12:
    raise RuntimeError("Walking validation failed: tail tip does not sway enough")
for frame, minimum_z in ground_checks["walking"].items():
    if minimum_z < -0.03:
        raise RuntimeError(
            f"Walking validation failed: frame {frame} penetrates ground at z={minimum_z:.4f}"
        )

sit = checks["sitting"]
if sit[12]["MDL_PELVIS"][2] > sit[1]["MDL_PELVIS"][2] - 0.55:
    raise RuntimeError("Sitting validation failed: pelvis did not lower enough")
for foot_name in ("MDL_FOOT_L", "MDL_FOOT_R"):
    if not (-0.05 <= sit[12][foot_name][2] <= 0.45):
        raise RuntimeError(f"Sitting validation failed: {foot_name} left the ground range")
if sit[12]["MDL_TAIL_TIP"][2] < -0.01:
    raise RuntimeError("Sitting validation failed: tail tip origin penetrates the ground")
if ground_checks["sitting"][12] < -0.01:
    raise RuntimeError(
        f"Sitting validation failed: model penetrates ground at z={ground_checks['sitting'][12]:.4f}"
    )

waving = checks["wave"]
if waving[10]["MDL_HAND_R"][2] < 4.3:
    raise RuntimeError("Wave validation failed: right hand does not reach head height")
if distance(waving[10]["MDL_HAND_R"], waving[20]["MDL_HAND_R"]) < 0.08:
    raise RuntimeError("Wave validation failed: wrist oscillation is too small")
if distance(waving[1]["MDL_HAND_R"], waving[48]["MDL_HAND_R"]) > 0.03:
    raise RuntimeError("Wave validation failed: final pose does not return to rest")

armature.animation_data.action = idle
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 40
bpy.context.scene.frame_set(1)
bpy.context.scene["cbanimal_proxy_v2_animation_stage"] = "local_axes_corrected_and_validated"
bpy.context.scene["cbanimal_proxy_v2_actions"] = ",".join(ACTION_NAMES)
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

rounded_checks = {
    action_name: {
        str(frame): {
            object_name: [round(value, 4) for value in position]
            for object_name, position in objects.items()
        }
        for frame, objects in frames.items()
    }
    for action_name, frames in checks.items()
}
rounded_ground_checks = {
    action_name: {str(frame): round(value, 4) for frame, value in frames.items()}
    for action_name, frames in ground_checks.items()
}
validation_payload = {
    "blend": bpy.data.filepath,
    "actions": list(ACTION_NAMES),
    "validation": rounded_checks,
    "ground_minimums": rounded_ground_checks,
}
VALIDATION_PATH.parent.mkdir(parents=True, exist_ok=True)
VALIDATION_PATH.write_text(json.dumps(validation_payload, indent=2) + "\n", encoding="utf-8")
print("CBANIMAL_PROXY_V2_ANIMATION_RESULT", validation_payload)
