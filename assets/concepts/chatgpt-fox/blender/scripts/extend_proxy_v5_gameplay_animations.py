from __future__ import annotations

from math import radians
from pathlib import Path

import bpy

RIG_NAME = "FOX_RIG_GUIDE"
BLEND_PATH = Path(
    r"C:\dev\cbanimal\assets\concepts\chatgpt-fox\blender\chatgpt_fox_proxy_v5.blend"
)
NEW_ACTION_NAMES = ("laugh", "angry", "sleep")

armature = bpy.data.objects.get(RIG_NAME)
if armature is None or armature.type != "ARMATURE":
    raise RuntimeError(f"Missing required armature: {RIG_NAME}")

armature.animation_data_create()
armature.animation_data.action = None

for action_name in NEW_ACTION_NAMES:
    existing = bpy.data.actions.get(action_name)
    if existing is not None:
        bpy.data.actions.remove(existing)

rotation_bones = tuple(bone.name for bone in armature.pose.bones)
location_bones = ("root", "pelvis")


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
    reset_pose()
    rotations = rotations or {}
    locations = locations or {}

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

    for bone_name in rotation_bones:
        armature.pose.bones[bone_name].keyframe_insert(
            data_path="rotation_euler",
            frame=frame,
            group=bone_name,
        )

    for bone_name in location_bones:
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
    runtime_loop: str,
) -> bpy.types.Action:
    action = bpy.data.actions.new(name=name)
    action.use_fake_user = True
    action["cbanimal_runtime_loop"] = runtime_loop
    action["cbanimal_runtime_role"] = "emote"
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


laugh = make_action(
    "laugh",
    48,
    [
        (1, {}, {}),
        (
            8,
            {
                "chest": (-7.0, 0.0, -3.0),
                "neck": (5.0, 0.0, 0.0),
                "head": (10.0, 0.0, 4.0),
                "upper_arm.L": (0.0, 15.0, 14.0),
                "upper_arm.R": (0.0, -15.0, -14.0),
                "forearm.L": (-18.0, 0.0, 6.0),
                "forearm.R": (-18.0, 0.0, -6.0),
                "tail.01": (0.0, 0.0, -9.0),
                "tail.02": (0.0, 0.0, -5.0),
            },
            {"pelvis": (0.0, 0.0, 0.0)},
        ),
        (
            16,
            {
                "chest": (5.0, 0.0, 3.0),
                "neck": (-3.0, 0.0, 0.0),
                "head": (-7.0, 0.0, -4.0),
                "upper_arm.L": (0.0, 10.0, 10.0),
                "upper_arm.R": (0.0, -10.0, -10.0),
                "forearm.L": (-12.0, 0.0, 4.0),
                "forearm.R": (-12.0, 0.0, -4.0),
                "tail.01": (0.0, 0.0, 9.0),
                "tail.02": (0.0, 0.0, 5.0),
            },
            {"pelvis": (0.0, 0.035, 0.0)},
        ),
        (
            24,
            {
                "chest": (-7.0, 0.0, -3.0),
                "neck": (5.0, 0.0, 0.0),
                "head": (10.0, 0.0, 4.0),
                "upper_arm.L": (0.0, 15.0, 14.0),
                "upper_arm.R": (0.0, -15.0, -14.0),
                "forearm.L": (-18.0, 0.0, 6.0),
                "forearm.R": (-18.0, 0.0, -6.0),
                "tail.01": (0.0, 0.0, -9.0),
                "tail.02": (0.0, 0.0, -5.0),
            },
            {"pelvis": (0.0, 0.0, 0.0)},
        ),
        (
            32,
            {
                "chest": (5.0, 0.0, 3.0),
                "neck": (-3.0, 0.0, 0.0),
                "head": (-7.0, 0.0, -4.0),
                "upper_arm.L": (0.0, 10.0, 10.0),
                "upper_arm.R": (0.0, -10.0, -10.0),
                "forearm.L": (-12.0, 0.0, 4.0),
                "forearm.R": (-12.0, 0.0, -4.0),
                "tail.01": (0.0, 0.0, 9.0),
                "tail.02": (0.0, 0.0, 5.0),
            },
            {"pelvis": (0.0, 0.035, 0.0)},
        ),
        (
            40,
            {
                "chest": (-5.0, 0.0, -2.0),
                "head": (7.0, 0.0, 2.0),
                "upper_arm.L": (0.0, 10.0, 8.0),
                "upper_arm.R": (0.0, -10.0, -8.0),
                "tail.01": (0.0, 0.0, -5.0),
            },
            {"pelvis": (0.0, 0.0, 0.0)},
        ),
        (48, {}, {}),
    ],
    "once",
)

angry = make_action(
    "angry",
    48,
    [
        (1, {}, {}),
        (
            10,
            {
                "chest": (-8.0, 0.0, 0.0),
                "neck": (4.0, 0.0, 0.0),
                "head": (5.0, 0.0, -4.0),
                "upper_arm.L": (12.0, 0.0, 48.0),
                "upper_arm.R": (12.0, 0.0, -48.0),
                "forearm.L": (-58.0, 0.0, 22.0),
                "forearm.R": (-58.0, 0.0, -22.0),
                "hand.L": (0.0, 0.0, 12.0),
                "hand.R": (0.0, 0.0, -12.0),
                "ear.L": (0.0, 0.0, 8.0),
                "ear.R": (0.0, 0.0, -8.0),
                "tail.01": (-4.0, 0.0, 11.0),
                "tail.02": (0.0, 0.0, 6.0),
            },
            {},
        ),
        (
            18,
            {
                "chest": (-8.0, 0.0, -6.0),
                "neck": (4.0, 0.0, 4.0),
                "head": (5.0, 0.0, 9.0),
                "upper_arm.L": (12.0, 0.0, 50.0),
                "upper_arm.R": (12.0, 0.0, -46.0),
                "forearm.L": (-58.0, 0.0, 22.0),
                "forearm.R": (-58.0, 0.0, -22.0),
                "hand.L": (0.0, 0.0, 15.0),
                "hand.R": (0.0, 0.0, -9.0),
                "tail.01": (-4.0, 0.0, 13.0),
                "tail.02": (0.0, 0.0, 7.0),
            },
            {},
        ),
        (
            26,
            {
                "chest": (-8.0, 0.0, 6.0),
                "neck": (4.0, 0.0, -4.0),
                "head": (5.0, 0.0, -9.0),
                "upper_arm.L": (12.0, 0.0, 46.0),
                "upper_arm.R": (12.0, 0.0, -50.0),
                "forearm.L": (-58.0, 0.0, 22.0),
                "forearm.R": (-58.0, 0.0, -22.0),
                "hand.L": (0.0, 0.0, 9.0),
                "hand.R": (0.0, 0.0, -15.0),
                "tail.01": (-4.0, 0.0, 9.0),
                "tail.02": (0.0, 0.0, 5.0),
            },
            {},
        ),
        (
            34,
            {
                "chest": (-8.0, 0.0, -3.0),
                "neck": (4.0, 0.0, 1.0),
                "head": (5.0, 0.0, 4.0),
                "upper_arm.L": (12.0, 0.0, 49.0),
                "upper_arm.R": (12.0, 0.0, -47.0),
                "forearm.L": (-58.0, 0.0, 22.0),
                "forearm.R": (-58.0, 0.0, -22.0),
                "tail.01": (-4.0, 0.0, 12.0),
                "tail.02": (0.0, 0.0, 6.0),
            },
            {},
        ),
        (
            42,
            {
                "chest": (-6.0, 0.0, 0.0),
                "head": (4.0, 0.0, 0.0),
                "upper_arm.L": (10.0, 0.0, 42.0),
                "upper_arm.R": (10.0, 0.0, -42.0),
                "forearm.L": (-50.0, 0.0, 18.0),
                "forearm.R": (-50.0, 0.0, -18.0),
                "tail.01": (-3.0, 0.0, 8.0),
            },
            {},
        ),
        (48, {}, {}),
    ],
    "once",
)

sleep = make_action(
    "sleep",
    72,
    [
        (1, {}, {}),
        (
            12,
            {
                "chest": (-8.0, 0.0, 0.0),
                "neck": (10.0, 0.0, 0.0),
                "head": (18.0, 0.0, 0.0),
                "upper_arm.L": (0.0, 5.0, 3.0),
                "upper_arm.R": (0.0, -5.0, -3.0),
                "forearm.L": (-7.0, 0.0, 0.0),
                "forearm.R": (-7.0, 0.0, 0.0),
                "ear.L": (5.0, 0.0, -6.0),
                "ear.R": (5.0, 0.0, 6.0),
                "tail.01": (8.0, 0.0, -5.0),
                "tail.02": (4.0, 0.0, -3.0),
            },
            {},
        ),
        (
            36,
            {
                "chest": (-10.0, 0.0, 0.0),
                "neck": (11.0, 0.0, 0.0),
                "head": (20.0, 0.0, 0.0),
                "upper_arm.L": (0.0, 5.0, 3.0),
                "upper_arm.R": (0.0, -5.0, -3.0),
                "forearm.L": (-7.0, 0.0, 0.0),
                "forearm.R": (-7.0, 0.0, 0.0),
                "ear.L": (6.0, 0.0, -7.0),
                "ear.R": (6.0, 0.0, 7.0),
                "tail.01": (9.0, 0.0, -6.0),
                "tail.02": (5.0, 0.0, -3.0),
            },
            {},
        ),
        (
            60,
            {
                "chest": (-8.0, 0.0, 0.0),
                "neck": (10.0, 0.0, 0.0),
                "head": (18.0, 0.0, 0.0),
                "upper_arm.L": (0.0, 5.0, 3.0),
                "upper_arm.R": (0.0, -5.0, -3.0),
                "forearm.L": (-7.0, 0.0, 0.0),
                "forearm.R": (-7.0, 0.0, 0.0),
                "ear.L": (5.0, 0.0, -6.0),
                "ear.R": (5.0, 0.0, 6.0),
                "tail.01": (8.0, 0.0, -5.0),
                "tail.02": (4.0, 0.0, -3.0),
            },
            {},
        ),
        (
            72,
            {
                "chest": (-9.0, 0.0, 0.0),
                "neck": (10.5, 0.0, 0.0),
                "head": (19.0, 0.0, 0.0),
                "upper_arm.L": (0.0, 5.0, 3.0),
                "upper_arm.R": (0.0, -5.0, -3.0),
                "forearm.L": (-7.0, 0.0, 0.0),
                "forearm.R": (-7.0, 0.0, 0.0),
                "ear.L": (5.5, 0.0, -6.5),
                "ear.R": (5.5, 0.0, 6.5),
                "tail.01": (8.5, 0.0, -5.5),
                "tail.02": (4.5, 0.0, -3.0),
            },
            {},
        ),
    ],
    "once_hold",
)

armature.animation_data.action = bpy.data.actions.get("idle")
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 40
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
bpy.context.scene["cbanimal_character_stage"] = "model_proxy_v5_gameplay_animations"
bpy.context.scene["cbanimal_proxy_v5_runtime_actions"] = ",".join(
    sorted(action.name for action in bpy.data.actions)
)
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

print(
    "CBANIMAL_PROXY_V5_GAMEPLAY_ANIMATIONS_RESULT",
    {
        "blend": str(BLEND_PATH),
        "added": list(NEW_ACTION_NAMES),
        "actions": sorted(action.name for action in bpy.data.actions),
        "frameRanges": {
            action.name: [round(float(value), 3) for value in action.frame_range]
            for action in bpy.data.actions
        },
    },
)
