from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
BLEND_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v5.blend"
EVIDENCE_PATH = BLENDER_DIR / "proxy-v5-walk-readability.json"
RIG_NAME = "FOX_RIG_GUIDE"
MODEL_COLLECTION = "MODEL_PROXY"
WALK_FRAMES = (1, 5, 9, 13, 17, 21, 25, 29, 32)
GEOMETRY_MARKER = "cbanimal_proxy_v5_gameplay_leg_proportions_v1"

# Stronger hip-driven stride for the actual top-down gameplay camera.
# Frame 32 intentionally duplicates frame 1 for a seamless loop.
GAIT = {
    "L": {
        "thigh_x": (-40, -28, -12, 20, 40, 28, 12, -20, -40),
        "thigh_z": (-2.0, -3.0, -2.0, 0.8, 2.5, 3.0, 2.0, -0.8, -2.0),
        "shin_x": (-4, -8, -14, -22, -12, -28, -32, -18, -4),
        "foot_world_x": (2, 0, -5, -8, -6, 4, 8, 6, 2),
    },
    "R": {
        "thigh_x": (40, 28, 12, -20, -40, -28, -12, 20, 40),
        "thigh_z": (2.5, 3.0, 2.0, -0.8, -2.0, -3.0, -2.0, 0.8, 2.5),
        "shin_x": (-12, -28, -32, -18, -4, -8, -14, -22, -12),
        "foot_world_x": (-6, 4, 8, 6, 2, 0, -5, -8, -6),
    },
}

PELVIS_X = (-0.055, -0.085, -0.065, -0.020, 0.055, 0.085, 0.065, 0.020, -0.055)
PELVIS_ROLL_Z = (3.5, 5.0, 3.0, 0.0, -3.5, -5.0, -3.0, 0.0, 3.5)
PELVIS_YAW_Y = (-5.0, -3.0, 0.0, 3.0, 5.0, 3.0, 0.0, -3.0, -5.0)
PELVIS_PITCH_X = (2.0, 3.0, 4.0, 3.0, 2.0, 3.0, 4.0, 3.0, 2.0)

SPINE_PITCH_X = (1.0, 1.5, 2.0, 1.5, 1.0, 1.5, 2.0, 1.5, 1.0)
SPINE_ROLL_Z = tuple(-value * 0.45 for value in PELVIS_ROLL_Z)
CHEST_ROLL_Z = tuple(-value * 0.80 for value in PELVIS_ROLL_Z)
SPINE_YAW_Y = tuple(-value * 0.45 for value in PELVIS_YAW_Y)
CHEST_YAW_Y = tuple(-value * 0.75 for value in PELVIS_YAW_Y)
CHEST_PITCH_X = (3.0, 4.0, 5.0, 4.0, 3.0, 4.0, 5.0, 4.0, 3.0)
HEAD_YAW_Y = tuple(value * 0.18 for value in PELVIS_YAW_Y)
HEAD_ROLL_Z = tuple(value * 0.12 for value in PELVIS_ROLL_Z)

ARM_SWING = {
    "L": (30, 20, 5, -20, -30, -20, -5, 20, 30),
    "R": (-30, -20, -5, 20, 30, 20, 5, -20, -30),
}
FOREARM_BEND_X = (2, 5, 8, 5, 2, 5, 8, 5, 2)


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


def mesh_scale(object_name: str, xyz: tuple[float, float, float]) -> None:
    obj = bpy.data.objects.get(object_name)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"Missing mesh: {object_name}")
    obj.data.transform(Matrix.Diagonal((*xyz, 1.0)))
    obj.data.update()


def world_bounds(object_name: str) -> dict[str, list[float]]:
    obj = bpy.data.objects[object_name]
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = [min(corner[index] for corner in corners) for index in range(3)]
    maximum = [max(corner[index] for corner in corners) for index in range(3)]
    return {
        "minimum": [round(float(value), 5) for value in minimum],
        "maximum": [round(float(value), 5) for value in maximum],
        "dimensions": [round(float(maximum[index] - minimum[index]), 5) for index in range(3)],
    }


def apply_gameplay_leg_proportions() -> dict:
    scene = bpy.context.scene
    if scene.get(GEOMETRY_MARKER):
        return {"applied": False, "reason": "already_applied"}

    before = {
        name: world_bounds(name)
        for name in (
            "MDL_HIP_L", "MDL_HIP_R", "MDL_THIGH_L", "MDL_THIGH_R",
            "MDL_KNEE_L", "MDL_KNEE_R", "MDL_SHIN_L", "MDL_SHIN_R",
            "MDL_ANKLE_L", "MDL_ANKLE_R", "MDL_FOOT_L", "MDL_FOOT_R",
        )
    }

    for side in ("L", "R"):
        mesh_scale(f"MDL_HIP_{side}", (0.90, 0.84, 0.68))
        mesh_scale(f"MDL_THIGH_{side}", (0.94, 0.88, 1.22))
        mesh_scale(f"MDL_KNEE_{side}", (0.88, 0.86, 0.90))
        mesh_scale(f"MDL_SHIN_{side}", (0.88, 0.84, 0.86))
        mesh_scale(f"MDL_ANKLE_{side}", (0.86, 0.82, 0.88))
        mesh_scale(f"MDL_FOOT_{side}", (0.88, 0.82, 0.86))

        thigh = bpy.data.objects[f"MDL_THIGH_{side}"]
        thigh.location.y = -0.42003
        shin = bpy.data.objects[f"MDL_SHIN_{side}"]
        shin.location.y = -0.40015

    bpy.context.view_layer.update()
    scene[GEOMETRY_MARKER] = True
    scene["cbanimal_proxy_v5_leg_visual_direction"] = "longer_exposed_thighs_shorter_quieter_lower_legs"

    after = {name: world_bounds(name) for name in before}
    return {"applied": True, "before": before, "after": after}


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


def rebuild_walk(rig: bpy.types.Object) -> dict:
    action = bpy.data.actions.get("walking")
    if action is None:
        raise RuntimeError("walking action is missing")
    rig.animation_data_create()
    rig.animation_data.action = action

    rotation_bones = {
        "pelvis", "spine", "chest", "head",
        "upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R",
        "thigh.L", "shin.L", "foot.L", "knee.L",
        "thigh.R", "shin.R", "foot.R", "knee.R",
    }
    rotation_paths = {f'pose.bones["{name}"].rotation_euler' for name in rotation_bones}
    location_paths = {'pose.bones["pelvis"].location'}
    remove_curves(action, rotation_paths | location_paths)

    pelvis = rig.pose.bones["pelvis"]
    spine = rig.pose.bones["spine"]
    chest = rig.pose.bones["chest"]
    head = rig.pose.bones["head"]

    for index, frame in enumerate(WALK_FRAMES):
        bpy.context.scene.frame_set(frame)

        pelvis.location = (PELVIS_X[index], 0.0, 0.0)
        set_rotation(pelvis, (PELVIS_PITCH_X[index], PELVIS_YAW_Y[index], PELVIS_ROLL_Z[index]))
        set_rotation(spine, (SPINE_PITCH_X[index], SPINE_YAW_Y[index], SPINE_ROLL_Z[index]))
        set_rotation(chest, (CHEST_PITCH_X[index], CHEST_YAW_Y[index], CHEST_ROLL_Z[index]))
        set_rotation(head, (0.0, HEAD_YAW_Y[index], HEAD_ROLL_Z[index]))

        key_location(pelvis, frame)
        for bone in (pelvis, spine, chest, head):
            key_rotation(bone, frame)

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
            upper_arm = rig.pose.bones[f"upper_arm.{side}"]
            forearm = rig.pose.bones[f"forearm.{side}"]

            set_rotation(thigh, (thigh_x, 0.0, thigh_z))
            set_rotation(shin, (shin_x, 0.0, 0.0))
            set_rotation(foot, (foot_local_x, 0.0, 0.0))
            set_rotation(knee, (shin_x * 0.45, 0.0, thigh_z * 0.20))
            set_rotation(upper_arm, (0.0, ARM_SWING[side][index], 0.0))
            set_rotation(forearm, (FOREARM_BEND_X[index], 0.0, 0.0))

            for bone in (thigh, shin, foot, knee, upper_arm, forearm):
                key_rotation(bone, frame)

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


def collect_visual_metrics(rig: bpy.types.Object) -> dict:
    rig.animation_data.action = bpy.data.actions["walking"]
    tracked = (
        "MDL_V5_BODY", "MDL_HIP_L", "MDL_HIP_R",
        "MDL_THIGH_L", "MDL_THIGH_R", "MDL_KNEE_L", "MDL_KNEE_R",
        "MDL_SHIN_L", "MDL_SHIN_R", "MDL_FOOT_L", "MDL_FOOT_R",
        "MDL_HAND_L", "MDL_HAND_R",
    )
    centers: dict[str, list[Vector]] = {name: [] for name in tracked}
    samples: dict[str, dict] = {}

    for frame in WALK_FRAMES:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        sample: dict[str, object] = {
            "minimumZ": round(model_minimum_z(), 5),
            "pelvis": {
                "location": [round(float(v), 5) for v in rig.pose.bones["pelvis"].location],
                "rotationDegrees": [round(math.degrees(float(v)), 3) for v in rig.pose.bones["pelvis"].rotation_euler],
            },
            "legs": {},
        }
        for side in ("L", "R"):
            sample["legs"][side] = {
                "thighXDegrees": round(math.degrees(float(rig.pose.bones[f"thigh.{side}"].rotation_euler.x)), 3),
                "shinXDegrees": round(math.degrees(float(rig.pose.bones[f"shin.{side}"].rotation_euler.x)), 3),
                "footLocalXDegrees": round(math.degrees(float(rig.pose.bones[f"foot.{side}"].rotation_euler.x)), 3),
                "upperArmYDegrees": round(math.degrees(float(rig.pose.bones[f"upper_arm.{side}"].rotation_euler.y)), 3),
            }
        for name in tracked:
            center = world_center(name)
            centers[name].append(center)
            sample[name] = [round(float(value), 5) for value in center]
        samples[str(frame)] = sample

    travel = {}
    for name, values in centers.items():
        minimum = [min(value[index] for value in values) for index in range(3)]
        maximum = [max(value[index] for value in values) for index in range(3)]
        travel[name] = [round(maximum[index] - minimum[index], 5) for index in range(3)]

    rig.animation_data.action = bpy.data.actions["idle"]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    body = world_bounds("MDL_V5_BODY")
    proportions = {}
    for side in ("L", "R"):
        thigh = world_bounds(f"MDL_THIGH_{side}")
        shin = world_bounds(f"MDL_SHIN_{side}")
        visible_below_body = max(0.0, body["minimum"][2] - thigh["minimum"][2])
        proportions[side] = {
            "thighHeight": thigh["dimensions"][2],
            "shinHeight": shin["dimensions"][2],
            "thighToShinHeightRatio": round(thigh["dimensions"][2] / shin["dimensions"][2], 4),
            "thighVisibleBelowBody": round(visible_below_body, 5),
        }

    return {
        "frames": list(WALK_FRAMES),
        "samples": samples,
        "worldCenterTravelXYZ": travel,
        "restProportions": proportions,
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
        "armSwingRangeDegrees": {
            side: round(max(ARM_SWING[side]) - min(ARM_SWING[side]), 3)
            for side in ("L", "R")
        },
    }


def main() -> None:
    ensure_canonical_file()
    rig = bpy.data.objects.get(RIG_NAME)
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError(f"Missing armature: {RIG_NAME}")

    geometry = apply_gameplay_leg_proportions()
    rebuild = rebuild_walk(rig)
    metrics = collect_visual_metrics(rig)

    for side in ("L", "R"):
        proportions = metrics["restProportions"][side]
        if proportions["thighToShinHeightRatio"] < 1.25:
            raise RuntimeError(f"Upper-leg silhouette still too short on {side}: {proportions}")
        if proportions["thighVisibleBelowBody"] < 0.62:
            raise RuntimeError(f"Too much thigh remains hidden by the torso on {side}: {proportions}")
    if metrics["thighSwingRangeDegrees"] != {"L": 80, "R": 80}:
        raise RuntimeError(f"Unexpected thigh swing: {metrics['thighSwingRangeDegrees']}")
    if any(value < 55 for value in metrics["armSwingRangeDegrees"].values()):
        raise RuntimeError(f"Arm swing remains unreadable: {metrics['armSwingRangeDegrees']}")

    payload = {
        "stage": "proxy_v5_gameplay_walk_readability_refined",
        "blend": str(BLEND_PATH),
        "geometry": geometry,
        "walk": rebuild,
        "metrics": metrics,
    }
    EVIDENCE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    rig.animation_data.action = bpy.data.actions["idle"]
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 40
    bpy.context.scene.frame_set(1)
    bpy.context.scene["cbanimal_proxy_v5_walk_stage"] = "gameplay_camera_readable_hip_driven_walk"
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print("CBANIMAL_PROXY_V5_WALK_READABILITY_RESULT", json.dumps(payload))


if __name__ == "__main__":
    main()
