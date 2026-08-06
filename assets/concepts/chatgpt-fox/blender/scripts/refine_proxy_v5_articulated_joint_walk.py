from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
BLEND_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v5.blend"
EVIDENCE_PATH = BLENDER_DIR / "proxy-v5-joint-walk-validation.json"
RIG_NAME = "FOX_RIG_GUIDE"
MODEL_COLLECTION = "MODEL_PROXY"
WALK_FRAMES = (1, 5, 9, 13, 17, 21, 25, 29, 32)
GEOMETRY_MARKER = "cbanimal_proxy_v5_articulated_joint_geometry_v1"

# Contact -> down -> passing -> up -> opposite contact.
# The swing leg now reaches a real 55-65 degree knee flexion instead of
# staying almost straight while only the foot and shin appeared to move.
GAIT = {
    "L": {
        "thigh_x": (-30, -20, -6, 14, 30, 20, 6, -14, -30),
        "thigh_z": (-2.0, -2.5, -1.5, 0.8, 2.0, 2.5, 1.5, -0.8, -2.0),
        "shin_x": (-8, -16, -32, -58, -12, -20, -44, -64, -8),
        "foot_world_x": (2, 0, 5, 12, 2, -2, 6, 14, 2),
    },
    "R": {
        "thigh_x": (30, 20, 6, -14, -30, -20, -6, 14, 30),
        "thigh_z": (2.0, 2.5, 1.5, -0.8, -2.0, -2.5, -1.5, 0.8, 2.0),
        "shin_x": (-12, -20, -44, -64, -8, -16, -32, -58, -12),
        "foot_world_x": (2, -2, 6, 14, 2, 0, 5, 12, 2),
    },
}

PELVIS_X = (-0.055, -0.075, -0.055, -0.018, 0.055, 0.075, 0.055, 0.018, -0.055)
PELVIS_ROLL_Z = (3.0, 4.0, 2.5, 0.0, -3.0, -4.0, -2.5, 0.0, 3.0)
PELVIS_YAW_Y = (-4.0, -2.5, 0.0, 2.5, 4.0, 2.5, 0.0, -2.5, -4.0)
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
    "L": (28, 18, 4, -18, -28, -18, -4, 18, 28),
    "R": (-28, -18, -4, 18, 28, 18, 4, -18, -28),
}
FOREARM_BEND_X = (4, 7, 10, 8, 4, 7, 10, 8, 4)


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


def taper_mesh(object_name: str, bottom_factor: float, top_factor: float) -> None:
    obj = bpy.data.objects.get(object_name)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"Missing mesh: {object_name}")
    vertices = obj.data.vertices
    z_min = min(vertex.co.z for vertex in vertices)
    z_max = max(vertex.co.z for vertex in vertices)
    height = max(z_max - z_min, 1e-6)
    for vertex in vertices:
        t = (vertex.co.z - z_min) / height
        smooth_t = t * t * (3.0 - 2.0 * t)
        factor = bottom_factor + (top_factor - bottom_factor) * smooth_t
        vertex.co.x *= factor
        vertex.co.y *= factor
    obj.data.update()


def scale_mesh_data(object_name: str, xyz: tuple[float, float, float]) -> None:
    obj = bpy.data.objects.get(object_name)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"Missing mesh: {object_name}")
    for vertex in obj.data.vertices:
        vertex.co.x *= xyz[0]
        vertex.co.y *= xyz[1]
        vertex.co.z *= xyz[2]
    obj.data.update()


def reparent_to_bone_preserve_world(obj: bpy.types.Object, rig: bpy.types.Object, bone_name: str) -> None:
    world_matrix = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world_matrix


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


def apply_joint_geometry(rig: bpy.types.Object) -> dict:
    scene = bpy.context.scene
    if scene.get(GEOMETRY_MARKER):
        return {"applied": False, "reason": "already_applied"}

    names = [
        *(f"MDL_HIP_{side}" for side in ("L", "R")),
        *(f"MDL_THIGH_{side}" for side in ("L", "R")),
        *(f"MDL_KNEE_{side}" for side in ("L", "R")),
        *(f"MDL_SHIN_{side}" for side in ("L", "R")),
    ]
    before = {name: world_bounds(name) for name in names}
    dark_material = bpy.data.materials.get("FOX_DARK_TEAL_V2")
    if dark_material is None:
        raise RuntimeError("Missing FOX_DARK_TEAL_V2 material")

    for side in ("L", "R"):
        hip = bpy.data.objects[f"MDL_HIP_{side}"]
        reparent_to_bone_preserve_world(hip, rig, "pelvis")

        thigh = bpy.data.objects[f"MDL_THIGH_{side}"]
        shin = bpy.data.objects[f"MDL_SHIN_{side}"]
        knee = bpy.data.objects[f"MDL_KNEE_{side}"]

        # Open a visible seam around the hinge and taper both rigid segments into it.
        thigh.location.y = -0.38503
        shin.location.y = -0.43015
        taper_mesh(thigh.name, bottom_factor=0.68, top_factor=0.98)
        taper_mesh(shin.name, bottom_factor=0.84, top_factor=0.68)
        scale_mesh_data(knee.name, (0.92, 0.92, 0.66))

        knee.data.materials.clear()
        knee.data.materials.append(dark_material)

    bpy.context.view_layer.update()
    scene[GEOMETRY_MARKER] = True
    scene["cbanimal_proxy_v5_joint_visual_direction"] = (
        "pelvis_anchored_hip_caps_tapered_thigh_shin_dark_knee_hinges"
    )
    after = {name: world_bounds(name) for name in names}
    return {
        "applied": True,
        "before": before,
        "after": after,
        "hipParent": "pelvis",
        "kneeMaterial": dark_material.name,
    }


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
            set_rotation(knee, (shin_x * 0.50, 0.0, thigh_z * 0.20))
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


def world_bone_point(rig: bpy.types.Object, value: Vector) -> Vector:
    return rig.matrix_world @ value


def knee_angle_degrees(rig: bpy.types.Object, side: str) -> float:
    thigh = rig.pose.bones[f"thigh.{side}"]
    shin = rig.pose.bones[f"shin.{side}"]
    hip = world_bone_point(rig, thigh.head)
    knee = world_bone_point(rig, shin.head)
    ankle = world_bone_point(rig, shin.tail)
    return math.degrees((hip - knee).normalized().angle((ankle - knee).normalized()))


def collect_joint_metrics(rig: bpy.types.Object) -> dict:
    rig.animation_data.action = bpy.data.actions["walking"]
    samples: dict[str, dict] = {}
    angle_ranges: dict[str, list[float]] = {"L": [], "R": []}
    for frame in WALK_FRAMES:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        frame_sample = {"minimumZ": round(model_minimum_z(), 5), "legs": {}}
        for side in ("L", "R"):
            knee_angle = knee_angle_degrees(rig, side)
            angle_ranges[side].append(knee_angle)
            frame_sample["legs"][side] = {
                "thighXDegrees": round(math.degrees(rig.pose.bones[f"thigh.{side}"].rotation_euler.x), 3),
                "shinXDegrees": round(math.degrees(rig.pose.bones[f"shin.{side}"].rotation_euler.x), 3),
                "footLocalXDegrees": round(math.degrees(rig.pose.bones[f"foot.{side}"].rotation_euler.x), 3),
                "kneeCarrierXDegrees": round(math.degrees(rig.pose.bones[f"knee.{side}"].rotation_euler.x), 3),
                "worldKneeAngleDegrees": round(knee_angle, 3),
                "flexionDegrees": round(180.0 - knee_angle, 3),
            }
        samples[str(frame)] = frame_sample

    result = {
        "frames": list(WALK_FRAMES),
        "samples": samples,
        "worldKneeAngleRangeDegrees": {
            side: [round(min(values), 3), round(max(values), 3)]
            for side, values in angle_ranges.items()
        },
        "maximumWorldFlexionDegrees": {
            side: round(180.0 - min(values), 3)
            for side, values in angle_ranges.items()
        },
        "thighSwingRangeDegrees": {
            side: max(GAIT[side]["thigh_x"]) - min(GAIT[side]["thigh_x"])
            for side in ("L", "R")
        },
        "maximumShinFlexionDegrees": {
            side: min(GAIT[side]["shin_x"]) for side in ("L", "R")
        },
        "pelvisLateralTravel": round(max(PELVIS_X) - min(PELVIS_X), 5),
        "pelvisRollRangeDegrees": round(max(PELVIS_ROLL_Z) - min(PELVIS_ROLL_Z), 3),
        "pelvisYawRangeDegrees": round(max(PELVIS_YAW_Y) - min(PELVIS_YAW_Y), 3),
        "hipParents": {
            side: {
                "parent": bpy.data.objects[f"MDL_HIP_{side}"].parent.name,
                "parentBone": bpy.data.objects[f"MDL_HIP_{side}"].parent_bone,
            }
            for side in ("L", "R")
        },
        "kneeMaterials": {
            side: [material.name for material in bpy.data.objects[f"MDL_KNEE_{side}"].data.materials]
            for side in ("L", "R")
        },
    }
    return result


def main() -> None:
    ensure_canonical_file()
    rig = bpy.data.objects.get(RIG_NAME)
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError(f"Missing armature: {RIG_NAME}")

    rig.animation_data_create()
    rig.animation_data.action = bpy.data.actions["idle"]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    geometry = apply_joint_geometry(rig)
    walk = rebuild_walk(rig)
    metrics = collect_joint_metrics(rig)

    for side in ("L", "R"):
        if metrics["maximumWorldFlexionDegrees"][side] < 55.0:
            raise RuntimeError(f"Knee {side} still does not visibly flex: {metrics}")
        if metrics["thighSwingRangeDegrees"][side] < 55.0:
            raise RuntimeError(f"Upper leg {side} still reads as rigid: {metrics}")
        if metrics["hipParents"][side]["parentBone"] != "pelvis":
            raise RuntimeError(f"Hip cap {side} still follows the thigh: {metrics}")
        if metrics["kneeMaterials"][side] != ["FOX_DARK_TEAL_V2"]:
            raise RuntimeError(f"Knee hinge {side} is not visually separated: {metrics}")
    for frame, value in walk["grounding"].items():
        if abs(value - 0.005) > 0.001:
            raise RuntimeError(f"Walking frame {frame} is not grounded: {value}")

    payload = {
        "stage": "proxy_v5_articulated_joint_walk_refined",
        "blend": str(BLEND_PATH),
        "geometry": geometry,
        "walk": walk,
        "metrics": metrics,
    }
    EVIDENCE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    rig.animation_data.action = bpy.data.actions["idle"]
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 40
    bpy.context.scene.frame_set(1)
    bpy.context.scene["cbanimal_proxy_v5_walk_stage"] = "articulated_hip_and_knee_walk"
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print("CBANIMAL_PROXY_V5_ARTICULATED_JOINT_RESULT", json.dumps(payload))


if __name__ == "__main__":
    main()
