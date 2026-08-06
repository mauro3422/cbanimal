from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
BLEND_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v5.blend"
RIG_NAME = "FOX_RIG_GUIDE"
MODEL_COLLECTION = "MODEL_PROXY"
WALK_FRAMES = (1, 5, 9, 13, 17, 21, 25, 29, 32)

# One complete in-place walk. Frame 32 intentionally matches frame 1.
GAIT = {
    "L": {
        "thigh_x": (-32, -22, -8, 18, 32, 22, 8, -18, -32),
        "thigh_z": (-1.5, -2.5, -1.5, 0.5, 2.0, 2.5, 1.5, -0.5, -1.5),
        "shin_x": (-6, -12, -18, -28, -18, -34, -38, -20, -6),
        "foot_world_x": (6, 2, -4, -8, -8, 6, 10, 8, 6),
    },
    "R": {
        "thigh_x": (32, 22, 8, -18, -32, -22, -8, 18, 32),
        "thigh_z": (2.0, 2.5, 1.5, -0.5, -1.5, -2.5, -1.5, 0.5, 2.0),
        "shin_x": (-18, -34, -38, -20, -6, -12, -18, -28, -18),
        "foot_world_x": (-8, 6, 10, 8, 6, 2, -4, -8, -8),
    },
}

# Pelvis local axes in this rig: X=lateral, Y=vertical, Z=forward/back.
PELVIS_X = (-0.040, -0.070, -0.055, -0.015, 0.040, 0.070, 0.055, 0.015, -0.040)
PELVIS_ROLL_Z = (2.5, 3.5, 2.0, 0.0, -2.5, -3.5, -2.0, 0.0, 2.5)
PELVIS_YAW_Y = (-3.0, -2.0, 0.0, 2.0, 3.0, 2.0, 0.0, -2.0, -3.0)
PELVIS_PITCH_X = (-1.0, -0.5, 0.5, 1.0, -1.0, -0.5, 0.5, 1.0, -1.0)

# Counterbalance the hips so the torso does not remain a rigid vertical post.
SPINE_ROLL_Z = tuple(-value * 0.40 for value in PELVIS_ROLL_Z)
CHEST_ROLL_Z = tuple(-value * 0.70 for value in PELVIS_ROLL_Z)
SPINE_YAW_Y = tuple(-value * 0.35 for value in PELVIS_YAW_Y)
CHEST_YAW_Y = tuple(-value * 0.65 for value in PELVIS_YAW_Y)
CHEST_PITCH_X = (1.0, 0.5, -0.5, -1.0, 1.0, 0.5, -0.5, -1.0, 1.0)


def ensure_canonical_file() -> None:
    current = Path(bpy.data.filepath) if bpy.data.filepath else None
    if current is None or current.resolve() != BLEND_PATH.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))


def channelbag(action: bpy.types.Action):
    if not action.layers or not action.layers[0].strips:
        return None
    strip = action.layers[0].strips[0]
    if not getattr(strip, "channelbags", None):
        return None
    return strip.channelbags[0]


def remove_curves(action: bpy.types.Action, paths: set[str]) -> None:
    bag = channelbag(action)
    if bag is None:
        return
    for curve in list(bag.fcurves):
        if curve.data_path in paths:
            bag.fcurves.remove(curve)


def set_rotation(pose_bone: bpy.types.PoseBone, xyz_degrees: tuple[float, float, float]) -> None:
    pose_bone.rotation_mode = "XYZ"
    pose_bone.rotation_euler = tuple(math.radians(value) for value in xyz_degrees)


def key_rotation(pose_bone: bpy.types.PoseBone, frame: int) -> None:
    pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=pose_bone.name)


def key_location(pose_bone: bpy.types.PoseBone, frame: int) -> None:
    pose_bone.keyframe_insert(data_path="location", frame=frame, group=pose_bone.name)


def model_minimum_z() -> float:
    collection = bpy.data.collections.get(MODEL_COLLECTION)
    if collection is None:
        raise RuntimeError(f"Missing collection: {MODEL_COLLECTION}")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    minimum_z = float("inf")
    for obj in collection.objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        for corner in evaluated.bound_box:
            minimum_z = min(minimum_z, float((evaluated.matrix_world @ Vector(corner)).z))
    if not math.isfinite(minimum_z):
        raise RuntimeError("MODEL_PROXY contains no evaluable mesh bounds")
    return minimum_z


def world_center(object_name: str) -> Vector:
    obj = bpy.data.objects[object_name]
    return sum((obj.matrix_world @ Vector(corner) for corner in obj.bound_box), Vector()) / 8.0


def polish_curves(action: bpy.types.Action, paths: set[str]) -> None:
    bag = channelbag(action)
    if bag is None:
        return
    for curve in bag.fcurves:
        if curve.data_path not in paths:
            continue
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"


def rebuild_walk(rig: bpy.types.Object) -> dict:
    action = bpy.data.actions.get("walking")
    if action is None:
        raise RuntimeError("walking action is missing")
    rig.animation_data_create()
    rig.animation_data.action = action

    rotation_bones = {
        "pelvis", "spine", "chest",
        "thigh.L", "shin.L", "foot.L", "knee.L",
        "thigh.R", "shin.R", "foot.R", "knee.R",
    }
    rotation_paths = {f'pose.bones["{name}"].rotation_euler' for name in rotation_bones}
    location_paths = {'pose.bones["pelvis"].location'}
    remove_curves(action, rotation_paths | location_paths)

    pelvis = rig.pose.bones["pelvis"]
    spine = rig.pose.bones["spine"]
    chest = rig.pose.bones["chest"]

    for index, frame in enumerate(WALK_FRAMES):
        bpy.context.scene.frame_set(frame)

        pelvis.location = (PELVIS_X[index], 0.0, 0.0)
        set_rotation(
            pelvis,
            (PELVIS_PITCH_X[index], PELVIS_YAW_Y[index], PELVIS_ROLL_Z[index]),
        )
        set_rotation(spine, (0.0, SPINE_YAW_Y[index], SPINE_ROLL_Z[index]))
        set_rotation(chest, (CHEST_PITCH_X[index], CHEST_YAW_Y[index], CHEST_ROLL_Z[index]))

        key_location(pelvis, frame)
        key_rotation(pelvis, frame)
        key_rotation(spine, frame)
        key_rotation(chest, frame)

        for side in ("L", "R"):
            pose = GAIT[side]
            thigh_x = pose["thigh_x"][index]
            thigh_z = pose["thigh_z"][index]
            shin_x = pose["shin_x"][index]
            foot_world_x = pose["foot_world_x"][index]
            foot_local_x = foot_world_x - thigh_x - shin_x

            thigh = rig.pose.bones[f"thigh.{side}"]
            shin = rig.pose.bones[f"shin.{side}"]
            foot = rig.pose.bones[f"foot.{side}"]
            knee = rig.pose.bones[f"knee.{side}"]

            set_rotation(thigh, (thigh_x, 0.0, thigh_z))
            set_rotation(shin, (shin_x, 0.0, 0.0))
            set_rotation(foot, (foot_local_x, 0.0, 0.0))
            set_rotation(knee, (shin_x * 0.5, 0.0, thigh_z * 0.25))

            for bone in (thigh, shin, foot, knee):
                key_rotation(bone, frame)

    # Recompute vertical pelvis placement only after every full-body pose exists.
    grounding: dict[str, float] = {}
    for frame in WALK_FRAMES:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        pelvis.location.y += 0.005 - model_minimum_z()
        key_location(pelvis, frame)
        bpy.context.view_layer.update()
        grounding[str(frame)] = round(model_minimum_z(), 5)

    polish_curves(action, rotation_paths | location_paths)
    return {"rotationPaths": sorted(rotation_paths), "grounding": grounding}


def collect_metrics(rig: bpy.types.Object) -> dict:
    action = bpy.data.actions["walking"]
    rig.animation_data.action = action
    samples: dict[str, dict] = {}
    tracked = (
        "MDL_V5_BODY",
        "MDL_THIGH_L", "MDL_KNEE_L", "MDL_SHIN_L", "MDL_FOOT_L",
        "MDL_THIGH_R", "MDL_KNEE_R", "MDL_SHIN_R", "MDL_FOOT_R",
    )
    centers: dict[str, list[Vector]] = {name: [] for name in tracked}

    for frame in WALK_FRAMES:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        frame_sample: dict[str, object] = {
            "floorMinimumZ": round(model_minimum_z(), 5),
            "pelvisLocation": [round(float(value), 5) for value in rig.pose.bones["pelvis"].location],
            "pelvisRotationDegrees": [
                round(math.degrees(float(value)), 3)
                for value in rig.pose.bones["pelvis"].rotation_euler
            ],
            "spineRotationDegrees": [
                round(math.degrees(float(value)), 3)
                for value in rig.pose.bones["spine"].rotation_euler
            ],
            "chestRotationDegrees": [
                round(math.degrees(float(value)), 3)
                for value in rig.pose.bones["chest"].rotation_euler
            ],
            "legs": {},
        }
        for side in ("L", "R"):
            frame_sample["legs"][side] = {
                "thighDegrees": [
                    round(math.degrees(float(value)), 3)
                    for value in rig.pose.bones[f"thigh.{side}"].rotation_euler
                ],
                "shinXDegrees": round(
                    math.degrees(float(rig.pose.bones[f"shin.{side}"].rotation_euler.x)), 3
                ),
                "kneeCarrierXDegrees": round(
                    math.degrees(float(rig.pose.bones[f"knee.{side}"].rotation_euler.x)), 3
                ),
                "footLocalXDegrees": round(
                    math.degrees(float(rig.pose.bones[f"foot.{side}"].rotation_euler.x)), 3
                ),
            }
        for name in tracked:
            center = world_center(name)
            centers[name].append(center)
            frame_sample[name] = [round(float(value), 5) for value in center]
        samples[str(frame)] = frame_sample

    travel = {}
    for name, values in centers.items():
        minimum = [min(value[index] for value in values) for index in range(3)]
        maximum = [max(value[index] for value in values) for index in range(3)]
        travel[name] = [round(maximum[index] - minimum[index], 5) for index in range(3)]

    return {
        "frames": list(WALK_FRAMES),
        "samples": samples,
        "worldCenterTravelXYZ": travel,
        "pelvisLateralTravel": round(max(PELVIS_X) - min(PELVIS_X), 5),
        "pelvisRollRangeDegrees": round(max(PELVIS_ROLL_Z) - min(PELVIS_ROLL_Z), 3),
        "pelvisYawRangeDegrees": round(max(PELVIS_YAW_Y) - min(PELVIS_YAW_Y), 3),
        "thighSwingRangeDegrees": {
            side: round(max(GAIT[side]["thigh_x"]) - min(GAIT[side]["thigh_x"]), 3)
            for side in ("L", "R")
        },
        "maximumShinFlexionDegrees": {
            side: min(GAIT[side]["shin_x"]) for side in ("L", "R")
        },
    }


def main() -> None:
    ensure_canonical_file()
    rig = bpy.data.objects.get(RIG_NAME)
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError(f"Missing armature: {RIG_NAME}")

    rebuild = rebuild_walk(rig)
    metrics = collect_metrics(rig)

    rig.animation_data.action = bpy.data.actions["idle"]
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 40
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    bpy.context.scene["cbanimal_proxy_v5_walk_stage"] = "full_body_weight_shift_walk"
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    print(json.dumps({"blend": str(BLEND_PATH), "rebuild": rebuild, "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
