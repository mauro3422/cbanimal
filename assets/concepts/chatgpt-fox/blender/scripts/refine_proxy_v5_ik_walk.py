from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[5]
BLENDER_DIR = ROOT / "assets/concepts/chatgpt-fox/blender"
BLEND_PATH = BLENDER_DIR / "chatgpt_fox_proxy_v5.blend"
EVIDENCE_PATH = BLENDER_DIR / "proxy-v5-ik-walk-validation.json"
RIG_NAME = "FOX_RIG_GUIDE"
MODEL_COLLECTION = "MODEL_PROXY"
ACTION_NAME = "walking"

FPS = 24.0
FRAME_START = 1
FRAME_END = 13
FRAME_COUNT = FRAME_END - FRAME_START
RUNTIME_SCALE = 0.32
REFERENCE_SPEED = 1.688
TARGET_FLOOR_Z = 0.005
STRIDE_HALF = 0.65
STANCE_FRACTION = 0.50
MAX_EXTENSION_RATIO = 0.97
PELVIS_LATERAL_SHIFT = 0.07

ALL_BONES = (
    "root",
    "pelvis",
    "spine",
    "chest",
    "neck",
    "head",
    "ear.L",
    "ear.R",
    "upper_arm.L",
    "forearm.L",
    "hand.L",
    "upper_arm.R",
    "forearm.R",
    "hand.R",
    "thigh.L",
    "shin.L",
    "foot.L",
    "knee.L",
    "thigh.R",
    "shin.R",
    "foot.R",
    "knee.R",
    "tail.01",
    "tail.02",
    "tail.03",
    "tail.04",
)


def ensure_canonical_file() -> None:
    current = Path(bpy.data.filepath) if bpy.data.filepath else None
    if current is None or current.resolve() != BLEND_PATH.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))


def action_channelbag(action: bpy.types.Action):
    if not action.layers or not action.layers[0].strips:
        return None
    strip = action.layers[0].strips[0]
    if not getattr(strip, "channelbags", None):
        return None
    return strip.channelbags[0]


def clear_action(action: bpy.types.Action) -> None:
    bag = action_channelbag(action)
    if bag is None:
        return
    for curve in list(bag.fcurves):
        bag.fcurves.remove(curve)


def set_linear_interpolation(action: bpy.types.Action) -> None:
    bag = action_channelbag(action)
    if bag is None:
        raise RuntimeError("Walking action did not create an animation channel bag")
    for curve in bag.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"


def reset_pose(rig: bpy.types.Object) -> None:
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.location = (0.0, 0.0, 0.0)
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)


def key_pose_bone(bone: bpy.types.PoseBone, frame: int) -> None:
    bone.keyframe_insert(data_path="location", frame=frame, group=bone.name)
    bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone.name)
    bone.keyframe_insert(data_path="scale", frame=frame, group=bone.name)


def radians_tuple(values: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(math.radians(value) for value in values)


def set_rotation_degrees(bone: bpy.types.PoseBone, values: tuple[float, float, float]) -> None:
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = radians_tuple(values)


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def phase_for(frame: int, side: str) -> float:
    normalized = (frame - FRAME_START) / FRAME_COUNT
    if frame == FRAME_END:
        normalized = 0.0
    offset = 0.0 if side == "L" else 0.5
    return (normalized + offset) % 1.0


def smooth_keyframes(value: float, keys: tuple[tuple[float, float], ...]) -> float:
    value = max(keys[0][0], min(keys[-1][0], value))
    for index in range(len(keys) - 1):
        left_t, left_value = keys[index]
        right_t, right_value = keys[index + 1]
        if value <= right_t:
            local = (value - left_t) / (right_t - left_t)
            eased = smoothstep(local)
            return left_value + (right_value - left_value) * eased
    return keys[-1][1]


def target_ankle(phase: float) -> dict[str, float | bool]:
    if phase < STANCE_FRACTION:
        u = phase / STANCE_FRACTION
        # The support foot travels backward at constant speed relative to the body.
        # The world-space translation cancels this movement, producing foot locking.
        fore_aft = -STRIDE_HALF + 2.0 * STRIDE_HALF * u
        # Four readable poses: contact, compression, passing and elevation/toe-off.
        # Larger down values place the pelvis higher once the support foot is grounded.
        down = smooth_keyframes(
            u,
            (
                (0.00, 1.51),
                (0.25, 1.43),
                (0.50, 1.55),
                (0.75, 1.58),
                (1.00, 1.48),
            ),
        )
        toe_roll = 0.0
        if u > 0.72:
            toe_roll = 15.0 * smoothstep((u - 0.72) / 0.28)
        return {
            "foreAft": fore_aft,
            "down": down,
            "footOffsetDegrees": toe_roll,
            "stance": True,
        }

    u = (phase - STANCE_FRACTION) / (1.0 - STANCE_FRACTION)
    fore_aft = STRIDE_HALF - 2.0 * STRIDE_HALF * smoothstep(u)
    # The free foot follows an arc and the knee folds before the thigh advances.
    down = smooth_keyframes(
        u,
        (
            (0.00, 1.48),
            (0.25, 1.26),
            (0.50, 1.10),
            (0.75, 1.30),
            (1.00, 1.51),
        ),
    )
    foot_offset = -12.0 * math.sin(math.pi * u)
    return {
        "foreAft": fore_aft,
        "down": down,
        "footOffsetDegrees": foot_offset,
        "stance": False,
    }


def rest_sagittal_angle(vector: Vector) -> float:
    return math.atan2(float(vector.y), float(-vector.z))


def solve_two_bone(
    fore_aft: float,
    down: float,
    upper_length: float,
    lower_length: float,
    upper_rest_angle: float,
    lower_rest_angle: float,
) -> dict[str, float]:
    target_y = float(fore_aft)
    target_z = -float(down)
    distance = math.hypot(target_y, target_z)
    minimum = abs(upper_length - lower_length) + 1e-5
    anatomical_maximum = upper_length + lower_length
    maximum = anatomical_maximum * MAX_EXTENSION_RATIO
    if not minimum <= distance <= maximum:
        raise RuntimeError(
            f"Unreachable or overextended ankle target y={target_y:.5f} z={target_z:.5f}; "
            f"distance={distance:.5f}, allowed=[{minimum:.5f}, {maximum:.5f}] "
            f"({MAX_EXTENSION_RATIO:.1%} of leg length)"
        )

    target_angle = math.atan2(target_y, -target_z)
    cos_beta = (
        upper_length * upper_length
        + distance * distance
        - lower_length * lower_length
    ) / (2.0 * upper_length * distance)
    beta = math.acos(max(-1.0, min(1.0, cos_beta)))

    cos_internal = (
        upper_length * upper_length
        + lower_length * lower_length
        - distance * distance
    ) / (2.0 * upper_length * lower_length)
    internal = math.acos(max(-1.0, min(1.0, cos_internal)))
    flexion = math.pi - internal

    upper_world_angle = target_angle + beta
    rest_relative = lower_rest_angle - upper_rest_angle
    thigh_local = upper_world_angle - upper_rest_angle
    shin_local = -flexion - rest_relative

    return {
        "thighDegrees": math.degrees(thigh_local),
        "shinDegrees": math.degrees(shin_local),
        "flexionDegrees": math.degrees(flexion),
        "targetAngleDegrees": math.degrees(target_angle),
        "upperWorldAngleDegrees": math.degrees(upper_world_angle),
        "distance": distance,
        "extensionRatio": distance / anatomical_maximum,
    }


def evaluated_mesh_points(obj: bpy.types.Object) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def evaluated_bounds(obj: bpy.types.Object) -> dict[str, list[float]]:
    points = evaluated_mesh_points(obj)
    minimum = Vector(
        (
            min(point.x for point in points),
            min(point.y for point in points),
            min(point.z for point in points),
        )
    )
    maximum = Vector(
        (
            max(point.x for point in points),
            max(point.y for point in points),
            max(point.z for point in points),
        )
    )
    return {
        "minimum": [round(float(value), 6) for value in minimum],
        "maximum": [round(float(value), 6) for value in maximum],
        "center": [round(float(value), 6) for value in ((minimum + maximum) * 0.5)],
        "dimensions": [round(float(value), 6) for value in (maximum - minimum)],
    }


def foot_minimum_z(side: str) -> float:
    bounds = evaluated_bounds(bpy.data.objects[f"MDL_FOOT_{side}"])
    return float(bounds["minimum"][2])


def ground_support_feet(rig: bpy.types.Object, frame: int, support_sides: list[str]) -> dict[str, float]:
    pelvis = rig.pose.bones["pelvis"]
    if not support_sides:
        raise RuntimeError(f"Frame {frame} has no support foot")

    for _ in range(3):
        bpy.context.view_layer.update()
        support_minimum = min(foot_minimum_z(side) for side in support_sides)
        pelvis.location.y += TARGET_FLOOR_Z - support_minimum

    pelvis.keyframe_insert(data_path="location", frame=frame, group="pelvis")
    bpy.context.view_layer.update()
    return {side: round(foot_minimum_z(side), 6) for side in ("L", "R")}


def world_bone_point(rig: bpy.types.Object, point: Vector) -> Vector:
    return rig.matrix_world @ point


def world_knee_flexion(rig: bpy.types.Object, side: str) -> float:
    thigh = rig.pose.bones[f"thigh.{side}"]
    shin = rig.pose.bones[f"shin.{side}"]
    hip = world_bone_point(rig, thigh.head)
    knee = world_bone_point(rig, shin.head)
    ankle = world_bone_point(rig, shin.tail)
    internal = math.degrees((hip - knee).normalized().angle((ankle - knee).normalized()))
    return 180.0 - internal


def build_walk(rig: bpy.types.Object) -> dict:
    action = bpy.data.actions.get(ACTION_NAME)
    if action is None:
        raise RuntimeError("walking action is missing")

    rig.animation_data_create()
    rig.animation_data.action = action
    clear_action(action)
    reset_pose(rig)

    scene = bpy.context.scene
    scene.render.fps = int(FPS)
    scene.render.fps_base = 1.0

    upper_length: dict[str, float] = {}
    lower_length: dict[str, float] = {}
    upper_rest_angle: dict[str, float] = {}
    lower_rest_angle: dict[str, float] = {}
    for side in ("L", "R"):
        upper_rest = rig.data.bones[f"thigh.{side}"].tail_local - rig.data.bones[f"thigh.{side}"].head_local
        lower_rest = rig.data.bones[f"shin.{side}"].tail_local - rig.data.bones[f"shin.{side}"].head_local
        upper_length[side] = float(upper_rest.length)
        lower_length[side] = float(lower_rest.length)
        upper_rest_angle[side] = rest_sagittal_angle(upper_rest)
        lower_rest_angle[side] = rest_sagittal_angle(lower_rest)

    frame_report: dict[str, dict] = {}
    for frame in range(FRAME_START, FRAME_END + 1):
        scene.frame_set(frame)
        reset_pose(rig)

        normalized = 0.0 if frame == FRAME_END else (frame - FRAME_START) / FRAME_COUNT
        gait_wave = math.sin(2.0 * math.pi * normalized)
        gait_cos = math.cos(2.0 * math.pi * normalized)

        pelvis = rig.pose.bones["pelvis"]
        # Shift weight over the planted leg and let the torso counterbalance it.
        pelvis.location.x = -PELVIS_LATERAL_SHIFT * gait_cos
        set_rotation_degrees(pelvis, (1.5 * gait_wave, 2.0 * gait_wave, 4.0 * gait_cos))
        set_rotation_degrees(rig.pose.bones["spine"], (1.5, -1.4 * gait_wave, -2.4 * gait_cos))
        set_rotation_degrees(rig.pose.bones["chest"], (2.5, -2.2 * gait_wave, -3.2 * gait_cos))
        set_rotation_degrees(rig.pose.bones["neck"], (-1.0, 0.5 * gait_wave, 0.4 * gait_cos))
        set_rotation_degrees(rig.pose.bones["head"], (-1.0, 0.8 * gait_wave, 0.6 * gait_cos))
        set_rotation_degrees(rig.pose.bones["ear.L"], (1.5 * gait_wave, 0.0, 1.0 * gait_cos))
        set_rotation_degrees(rig.pose.bones["ear.R"], (-1.5 * gait_wave, 0.0, -1.0 * gait_cos))

        # Arm swing opposes the legs. Bone-local Y is the established arm-swing axis.
        arm_swing = 34.0 * gait_cos
        set_rotation_degrees(rig.pose.bones["upper_arm.L"], (0.0, arm_swing, 0.0))
        set_rotation_degrees(rig.pose.bones["upper_arm.R"], (0.0, -arm_swing, 0.0))
        set_rotation_degrees(rig.pose.bones["forearm.L"], (8.0 + 5.0 * max(0.0, -gait_cos), 0.0, 0.0))
        set_rotation_degrees(rig.pose.bones["forearm.R"], (8.0 + 5.0 * max(0.0, gait_cos), 0.0, 0.0))

        set_rotation_degrees(rig.pose.bones["tail.01"], (8.0, 7.0 * gait_wave, -5.0 * gait_cos))
        set_rotation_degrees(rig.pose.bones["tail.02"], (4.0, 9.0 * gait_wave, -7.0 * gait_cos))
        set_rotation_degrees(rig.pose.bones["tail.03"], (0.0, 11.0 * gait_wave, -8.0 * gait_cos))
        set_rotation_degrees(rig.pose.bones["tail.04"], (0.0, 13.0 * gait_wave, -9.0 * gait_cos))

        support_sides: list[str] = []
        legs: dict[str, dict] = {}
        for side in ("L", "R"):
            phase = phase_for(frame, side)
            target = target_ankle(phase)
            solution = solve_two_bone(
                fore_aft=float(target["foreAft"]),
                down=float(target["down"]),
                upper_length=upper_length[side],
                lower_length=lower_length[side],
                upper_rest_angle=upper_rest_angle[side],
                lower_rest_angle=lower_rest_angle[side],
            )

            thigh_degrees = solution["thighDegrees"]
            shin_degrees = solution["shinDegrees"]
            foot_degrees = float(target["footOffsetDegrees"]) - thigh_degrees - shin_degrees

            set_rotation_degrees(rig.pose.bones[f"thigh.{side}"], (thigh_degrees, 0.0, 0.0))
            set_rotation_degrees(rig.pose.bones[f"shin.{side}"], (shin_degrees, 0.0, 0.0))
            set_rotation_degrees(rig.pose.bones[f"foot.{side}"], (foot_degrees, 0.0, 0.0))
            set_rotation_degrees(rig.pose.bones[f"knee.{side}"], (shin_degrees * 0.50, 0.0, 0.0))

            if bool(target["stance"]):
                support_sides.append(side)

            legs[side] = {
                "phase": round(phase, 6),
                "target": {
                    "foreAft": round(float(target["foreAft"]), 6),
                    "down": round(float(target["down"]), 6),
                    "footOffsetDegrees": round(float(target["footOffsetDegrees"]), 6),
                    "stance": bool(target["stance"]),
                },
                "solution": {key: round(float(value), 6) for key, value in solution.items()},
                "footLocalDegrees": round(foot_degrees, 6),
            }

        for bone_name in ALL_BONES:
            key_pose_bone(rig.pose.bones[bone_name], frame)

        bpy.context.view_layer.update()
        foot_minima = ground_support_feet(rig, frame, support_sides)
        for bone_name in ALL_BONES:
            # Re-key pelvis location after grounding; other keys are unchanged.
            if bone_name == "pelvis":
                continue
        frame_report[str(frame)] = {
            "supportSides": support_sides,
            "footMinimumZ": foot_minima,
            "pelvisLocation": [round(float(value), 6) for value in pelvis.location],
            "legs": legs,
        }

    action.use_frame_range = True
    action.frame_start = FRAME_START
    action.frame_end = FRAME_END
    set_linear_interpolation(action)
    return {
        "frameRange": [FRAME_START, FRAME_END],
        "fps": FPS,
        "durationSeconds": round((FRAME_END - FRAME_START) / FPS, 6),
        "runtimeScale": RUNTIME_SCALE,
        "referenceSpeed": REFERENCE_SPEED,
        "strideHalfBlender": STRIDE_HALF,
        "stanceFraction": STANCE_FRACTION,
        "expectedStanceFootSpeed": round(
            (2.0 * STRIDE_HALF * RUNTIME_SCALE)
            / (((FRAME_END - FRAME_START) / FPS) * STANCE_FRACTION),
            6,
        ),
        "frameReport": frame_report,
    }


def validate_walk(rig: bpy.types.Object, build: dict) -> dict:
    action = bpy.data.actions[ACTION_NAME]
    rig.animation_data.action = action
    scene = bpy.context.scene
    samples: dict[str, dict] = {}
    support_speeds: dict[str, list[float]] = {"L": [], "R": []}
    flexions: dict[str, list[float]] = {"L": [], "R": []}
    swing_clearances: dict[str, list[float]] = {"L": [], "R": []}
    segment_lengths: dict[str, dict[str, list[float]]] = {
        "L": {"upper": [], "lower": []},
        "R": {"upper": [], "lower": []},
    }

    foot_centers: dict[str, list[Vector]] = {"L": [], "R": []}
    stance_flags: dict[str, list[bool]] = {"L": [], "R": []}
    frames = list(range(FRAME_START, FRAME_END + 1))

    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        sample = {"legs": {}}
        for side in ("L", "R"):
            thigh = rig.pose.bones[f"thigh.{side}"]
            shin = rig.pose.bones[f"shin.{side}"]
            hip = world_bone_point(rig, thigh.head)
            knee = world_bone_point(rig, shin.head)
            ankle = world_bone_point(rig, shin.tail)
            upper = float((knee - hip).length)
            lower = float((ankle - knee).length)
            flexion = world_knee_flexion(rig, side)
            bounds = evaluated_bounds(bpy.data.objects[f"MDL_FOOT_{side}"])
            center = Vector(bounds["center"])
            stance = bool(build["frameReport"][str(frame)]["legs"][side]["target"]["stance"])

            foot_centers[side].append(center)
            stance_flags[side].append(stance)
            flexions[side].append(flexion)
            segment_lengths[side]["upper"].append(upper)
            segment_lengths[side]["lower"].append(lower)
            if not stance:
                swing_clearances[side].append(float(bounds["minimum"][2]))

            sample["legs"][side] = {
                "stance": stance,
                "hip": [round(float(value), 6) for value in hip],
                "knee": [round(float(value), 6) for value in knee],
                "ankle": [round(float(value), 6) for value in ankle],
                "upperLength": round(upper, 6),
                "lowerLength": round(lower, 6),
                "worldKneeFlexionDegrees": round(flexion, 6),
                "footBounds": bounds,
            }
        samples[str(frame)] = sample

    delta_time = 1.0 / FPS
    for side in ("L", "R"):
        for index in range(len(frames) - 1):
            if not stance_flags[side][index] or not stance_flags[side][index + 1]:
                continue
            velocity = (
                foot_centers[side][index + 1].y - foot_centers[side][index].y
            ) * RUNTIME_SCALE / delta_time
            support_speeds[side].append(abs(float(velocity)))

    metrics: dict[str, object] = {
        "samples": samples,
        "legs": {},
    }
    for side in ("L", "R"):
        upper_values = segment_lengths[side]["upper"]
        lower_values = segment_lengths[side]["lower"]
        stance_z = [
            float(samples[str(frame)]["legs"][side]["footBounds"]["minimum"][2])
            for index, frame in enumerate(frames)
            if stance_flags[side][index]
        ]
        speeds = support_speeds[side]
        metrics["legs"][side] = {
            "kneeFlexionRangeDegrees": [
                round(min(flexions[side]), 6),
                round(max(flexions[side]), 6),
            ],
            "supportFootMinimumZRange": [round(min(stance_z), 6), round(max(stance_z), 6)],
            "swingFootClearanceRange": [
                round(min(swing_clearances[side]), 6),
                round(max(swing_clearances[side]), 6),
            ],
            "supportFootSpeedRuntimeRange": [
                round(min(speeds), 6),
                round(max(speeds), 6),
            ],
            "supportFootSpeedRuntimeMean": round(sum(speeds) / len(speeds), 6),
            "referenceSpeedErrorPercent": round(
                abs((sum(speeds) / len(speeds)) - REFERENCE_SPEED) / REFERENCE_SPEED * 100.0,
                3,
            ),
            "upperLengthRange": [round(min(upper_values), 8), round(max(upper_values), 8)],
            "lowerLengthRange": [round(min(lower_values), 8), round(max(lower_values), 8)],
        }

        leg = metrics["legs"][side]
        if leg["kneeFlexionRangeDegrees"][1] < 75.0:
            raise RuntimeError(f"{side} swing knee flexion remains too small: {leg}")
        if leg["kneeFlexionRangeDegrees"][0] < -0.5:
            raise RuntimeError(f"{side} knee hyperextends: {leg}")
        if leg["supportFootMinimumZRange"][0] < -0.01 or leg["supportFootMinimumZRange"][1] > 0.02:
            raise RuntimeError(f"{side} stance foot is not grounded: {leg}")
        if leg["swingFootClearanceRange"][0] < -0.01:
            raise RuntimeError(f"{side} swing foot penetrates the floor: {leg}")
        if leg["swingFootClearanceRange"][1] < 0.20:
            raise RuntimeError(f"{side} swing foot never clears the floor enough: {leg}")
        if leg["referenceSpeedErrorPercent"] > 12.0:
            raise RuntimeError(f"{side} stance foot speed does not match player speed: {leg}")
        if max(upper_values) - min(upper_values) > 1e-5:
            raise RuntimeError(f"{side} upper segment length changed across animation")
        if max(lower_values) - min(lower_values) > 1e-5:
            raise RuntimeError(f"{side} lower segment length changed across animation")

    return metrics


def main() -> None:
    ensure_canonical_file()
    rig = bpy.data.objects.get(RIG_NAME)
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError(f"Missing armature: {RIG_NAME}")
    if bpy.data.collections.get(MODEL_COLLECTION) is None:
        raise RuntimeError(f"Missing collection: {MODEL_COLLECTION}")

    build = build_walk(rig)
    validation = validate_walk(rig, build)
    payload = {
        "stage": "proxy_v5_ik_walk_mathematically_validated",
        "blend": str(BLEND_PATH),
        "kinematics": build,
        "validation": validation,
    }
    EVIDENCE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    rig.animation_data.action = bpy.data.actions["idle"]
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 40
    bpy.context.scene.frame_set(1)
    bpy.context.scene["cbanimal_proxy_v5_walk_stage"] = "two_bone_ik_speed_matched_walk"
    bpy.context.scene["cbanimal_proxy_v5_walk_reference_speed"] = REFERENCE_SPEED
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print("CBANIMAL_PROXY_V5_IK_WALK_RESULT", json.dumps(payload))


if __name__ == "__main__":
    main()
