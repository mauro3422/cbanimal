from __future__ import annotations

import json
from math import radians
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
BLEND_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v5.blend"
RIG_NAME = "FOX_RIG_GUIDE"
KNEE_MESHES = {
    "L": "MDL_KNEE_L",
    "R": "MDL_KNEE_R",
}
KNEE_BONES = {
    "L": "knee.L",
    "R": "knee.R",
}

WALK_FRAMES = (1, 5, 9, 13, 17, 21, 25, 29, 32)
WALK_POSES_DEG = {
    "L": {
        "thigh": (-28, -20, 0, 20, 28, 20, 0, -20, -28),
        "shin": (-8, -16, -20, -32, -22, -38, -44, -24, -8),
        "foot_world": (8, 0, -8, -15, -12, 8, 12, 10, 8),
    },
    "R": {
        "thigh": (28, 20, 0, -20, -28, -20, 0, 20, 28),
        "shin": (-22, -38, -44, -24, -8, -16, -20, -32, -22),
        "foot_world": (-12, 8, 12, 10, 8, 0, -8, -15, -12),
    },
}


def ensure_canonical_file() -> None:
    current = Path(bpy.data.filepath) if bpy.data.filepath else None
    if current is None or current.resolve() != BLEND_PATH.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))


def get_channelbag(action: bpy.types.Action):
    if not action.layers:
        return None
    layer = action.layers[0]
    if not layer.strips:
        return None
    strip = layer.strips[0]
    if not getattr(strip, "channelbags", None):
        return None
    return strip.channelbags[0]


def remove_rotation_curves(action: bpy.types.Action, bone_names: set[str]) -> None:
    bag = get_channelbag(action)
    if bag is None:
        return
    prefixes = {f'pose.bones["{name}"].rotation_euler' for name in bone_names}
    for curve in list(bag.fcurves):
        if curve.data_path in prefixes:
            bag.fcurves.remove(curve)


def key_rotation(pose_bone: bpy.types.PoseBone, frame: int) -> None:
    pose_bone.keyframe_insert(
        data_path="rotation_euler",
        frame=frame,
        group=pose_bone.name,
    )


def polish_rotation_curves(action: bpy.types.Action, bone_names: set[str]) -> None:
    bag = get_channelbag(action)
    if bag is None:
        return
    paths = {f'pose.bones["{name}"].rotation_euler' for name in bone_names}
    for curve in bag.fcurves:
        if curve.data_path not in paths:
            continue
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"


def unique_key_frames(action: bpy.types.Action) -> list[int]:
    bag = get_channelbag(action)
    frames: set[int] = set()
    if bag is not None:
        for curve in bag.fcurves:
            for point in curve.keyframe_points:
                frames.add(int(round(point.co.x)))
    if not frames:
        start, end = action.frame_range
        frames.update((int(round(start)), int(round(end))))
    return sorted(frames)


def create_knee_bones(rig: bpy.types.Object) -> None:
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    rig.hide_set(False)
    rig.hide_viewport = False
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")

    edit_bones = rig.data.edit_bones
    for side in ("L", "R"):
        thigh = edit_bones[f"thigh.{side}"]
        shin = edit_bones[f"shin.{side}"]
        knee_name = KNEE_BONES[side]
        knee = edit_bones.get(knee_name) or edit_bones.new(knee_name)
        direction = (shin.tail - shin.head).normalized()
        knee.head = shin.head.copy()
        knee.tail = shin.head + direction * min(0.46, shin.length * 0.30)
        knee.roll = shin.roll
        knee.parent = thigh
        knee.use_connect = False
        knee.use_deform = False

    bpy.ops.object.mode_set(mode="POSE")
    for knee_name in KNEE_BONES.values():
        pose_bone = rig.pose.bones[knee_name]
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
    bpy.ops.object.mode_set(mode="OBJECT")


def reparent_knee_meshes(rig: bpy.types.Object) -> None:
    idle = bpy.data.actions.get("idle")
    rig.animation_data_create()
    rig.animation_data.action = idle
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    for side, object_name in KNEE_MESHES.items():
        obj = bpy.data.objects.get(object_name)
        if obj is None:
            raise RuntimeError(f"Missing knee mesh: {object_name}")
        world_matrix = obj.matrix_world.copy()
        obj.parent = rig
        obj.parent_type = "BONE"
        obj.parent_bone = KNEE_BONES[side]
        obj.matrix_world = world_matrix


def bake_knee_carriers_for_existing_actions(rig: bpy.types.Object) -> None:
    for action in bpy.data.actions:
        if action.name == "walking":
            continue
        frames = unique_key_frames(action)
        remove_rotation_curves(action, set(KNEE_BONES.values()))
        rig.animation_data.action = action
        for frame in frames:
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            for side in ("L", "R"):
                shin = rig.pose.bones[f"shin.{side}"]
                knee = rig.pose.bones[KNEE_BONES[side]]
                knee.rotation_mode = "XYZ"
                knee.rotation_euler = (
                    shin.rotation_euler.x * 0.5,
                    shin.rotation_euler.y * 0.5,
                    shin.rotation_euler.z * 0.5,
                )
                key_rotation(knee, frame)
        polish_rotation_curves(action, set(KNEE_BONES.values()))


def rebuild_walking_legs(rig: bpy.types.Object) -> None:
    action = bpy.data.actions.get("walking")
    if action is None:
        raise RuntimeError("walking action is missing")

    target_bones = {
        "thigh.L",
        "shin.L",
        "foot.L",
        "knee.L",
        "thigh.R",
        "shin.R",
        "foot.R",
        "knee.R",
    }
    remove_rotation_curves(action, target_bones)
    rig.animation_data.action = action

    for index, frame in enumerate(WALK_FRAMES):
        bpy.context.scene.frame_set(frame)
        for side in ("L", "R"):
            pose = WALK_POSES_DEG[side]
            thigh_deg = pose["thigh"][index]
            shin_deg = pose["shin"][index]
            foot_world_deg = pose["foot_world"][index]
            foot_local_deg = foot_world_deg - thigh_deg - shin_deg

            thigh = rig.pose.bones[f"thigh.{side}"]
            shin = rig.pose.bones[f"shin.{side}"]
            foot = rig.pose.bones[f"foot.{side}"]
            knee = rig.pose.bones[f"knee.{side}"]

            for bone in (thigh, shin, foot, knee):
                bone.rotation_mode = "XYZ"
                bone.rotation_euler.y = 0.0
                bone.rotation_euler.z = 0.0

            thigh.rotation_euler.x = radians(thigh_deg)
            shin.rotation_euler.x = radians(shin_deg)
            knee.rotation_euler.x = radians(shin_deg * 0.5)
            foot.rotation_euler.x = radians(foot_local_deg)

            for bone in (thigh, shin, foot, knee):
                key_rotation(bone, frame)

    polish_rotation_curves(action, target_bones)


def model_minimum_z() -> float:
    collection = bpy.data.collections.get("MODEL_PROXY")
    if collection is None:
        raise RuntimeError("MODEL_PROXY collection is missing")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    minimum_z = float("inf")
    for obj in collection.objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        for corner in evaluated.bound_box:
            world = evaluated.matrix_world @ Vector(corner)
            minimum_z = min(minimum_z, float(world.z))
    if minimum_z == float("inf"):
        raise RuntimeError("MODEL_PROXY does not contain mesh objects")
    return minimum_z


def ground_walking_cycle(rig: bpy.types.Object, target_z: float = 0.005) -> dict[str, dict[str, float]]:
    action = bpy.data.actions["walking"]
    rig.animation_data.action = action
    root = rig.pose.bones["root"]
    pelvis = rig.pose.bones["pelvis"]
    before: dict[str, float] = {}
    after: dict[str, float] = {}

    # The root bone points along world Y, so its local Z channel must remain zero.
    # Vertical placement is driven by pelvis local Y in this armature.
    for frame in WALK_FRAMES:
        bpy.context.scene.frame_set(frame)
        root.location.z = 0.0
        root.keyframe_insert(data_path="location", frame=frame, group=root.name)

    for frame in WALK_FRAMES:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        current_minimum = model_minimum_z()
        before[str(frame)] = round(current_minimum, 5)
        pelvis.location.y += target_z - current_minimum
        pelvis.keyframe_insert(data_path="location", frame=frame, group=pelvis.name)
        bpy.context.view_layer.update()
        after[str(frame)] = round(model_minimum_z(), 5)

    bag = get_channelbag(action)
    if bag is not None:
        location_paths = {
            'pose.bones["root"].location',
            'pose.bones["pelvis"].location',
        }
        for curve in bag.fcurves:
            if curve.data_path not in location_paths:
                continue
            for point in curve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"

    return {"before": before, "after": after}


def collect_result(rig: bpy.types.Object, grounding: dict[str, dict[str, float]]) -> dict:
    walking = bpy.data.actions["walking"]
    rig.animation_data.action = walking
    samples: dict[str, dict] = {}
    for frame in WALK_FRAMES:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        frame_data: dict[str, dict] = {}
        for side in ("L", "R"):
            thigh = rig.pose.bones[f"thigh.{side}"]
            shin = rig.pose.bones[f"shin.{side}"]
            knee = rig.pose.bones[f"knee.{side}"]
            foot = rig.pose.bones[f"foot.{side}"]
            frame_data[side] = {
                "thighXDegrees": round(thigh.rotation_euler.x * 57.295779513, 3),
                "shinXDegrees": round(shin.rotation_euler.x * 57.295779513, 3),
                "kneeCarrierXDegrees": round(knee.rotation_euler.x * 57.295779513, 3),
                "footLocalXDegrees": round(foot.rotation_euler.x * 57.295779513, 3),
                "footWorldTargetDegrees": WALK_POSES_DEG[side]["foot_world"][WALK_FRAMES.index(frame)],
            }
        samples[str(frame)] = frame_data

    return {
        "blend": str(BLEND_PATH),
        "bones": len(rig.data.bones),
        "kneeBones": {
            name: {
                "parent": rig.data.bones[name].parent.name if rig.data.bones[name].parent else None,
                "useDeform": rig.data.bones[name].use_deform,
            }
            for name in KNEE_BONES.values()
        },
        "kneeMeshes": {
            object_name: {
                "parent": bpy.data.objects[object_name].parent.name,
                "parentType": bpy.data.objects[object_name].parent_type,
                "parentBone": bpy.data.objects[object_name].parent_bone,
            }
            for object_name in KNEE_MESHES.values()
        },
        "walkingSamples": samples,
        "grounding": grounding,
        "actions": sorted(action.name for action in bpy.data.actions),
    }


def main() -> None:
    ensure_canonical_file()
    rig = bpy.data.objects.get(RIG_NAME)
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError(f"Missing armature: {RIG_NAME}")

    create_knee_bones(rig)
    reparent_knee_meshes(rig)
    bake_knee_carriers_for_existing_actions(rig)
    rebuild_walking_legs(rig)
    grounding = ground_walking_cycle(rig)

    result = collect_result(rig, grounding)

    rig.animation_data.action = bpy.data.actions["idle"]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
