from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector

OUTPUT_BLEND = Path(r"C:\dev\cbanimal\assets\concepts\chatgpt-fox\blender\chatgpt_fox_proxy_v2.blend")
MODEL_COLLECTION = "MODEL_PROXY"
RIG_COLLECTION = "RIG_GUIDE"
RIG_NAME = "FOX_RIG_GUIDE"


def ensure_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def clear_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is not None:
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(collection)
    return ensure_collection(name)


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def material(name: str, color: tuple[float, float, float, float], emission: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get("Principled BSDF") if mat.node_tree else None
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = 0.68
        metallic = principled.inputs.get("Metallic")
        if metallic is not None:
            metallic.default_value = 0.03
        if emission > 0.0:
            emission_color = principled.inputs.get("Emission Color")
            emission_strength = principled.inputs.get("Emission Strength")
            if emission_color is not None:
                emission_color.default_value = color
            if emission_strength is not None:
                emission_strength.default_value = emission
    return mat


def finish_object(
    obj: bpy.types.Object,
    collection: bpy.types.Collection,
    mat: bpy.types.Material,
    smooth: bool = True,
) -> bpy.types.Object:
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.color = mat.diffuse_color
    obj.show_in_front = False
    if smooth and hasattr(obj.data, "polygons"):
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    move_to_collection(obj, collection)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.select_set(False)
    obj["cbanimal_stage"] = "model_proxy_v2"
    return obj


def add_ico(name: str, location, scale, mat, collection, subdivisions: int = 2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    return finish_object(obj, collection, mat)


def add_cylinder_between(
    name: str,
    start,
    end,
    radius: float,
    mat,
    collection,
    vertices: int = 10,
):
    start_v = Vector(start)
    end_v = Vector(end)
    direction = end_v - start_v
    length = direction.length
    midpoint = (start_v + end_v) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=length,
        end_fill_type="TRIFAN",
        location=midpoint,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    obj.rotation_mode = "XYZ"
    return finish_object(obj, collection, mat)


def add_cone_between(
    name: str,
    start,
    end,
    radius_start: float,
    radius_end: float,
    mat,
    collection,
    vertices: int = 10,
):
    start_v = Vector(start)
    end_v = Vector(end)
    direction = end_v - start_v
    length = direction.length
    midpoint = (start_v + end_v) * 0.5
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius_start,
        radius2=radius_end,
        depth=length,
        end_fill_type="TRIFAN",
        location=midpoint,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    obj.rotation_mode = "XYZ"
    return finish_object(obj, collection, mat)


def reset_pose(armature: bpy.types.Object) -> None:
    armature.animation_data_create()
    armature.animation_data.action = None
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)


def update_rig_rest_pose(armature: bpy.types.Object) -> dict[str, tuple[Vector, Vector]]:
    points = {
        "root": ((0.0, 0.0, 0.05), (0.0, 0.0, 0.45)),
        "pelvis": ((0.0, 0.0, 2.02), (0.0, 0.0, 2.52)),
        "spine": ((0.0, 0.0, 2.52), (0.0, 0.0, 3.12)),
        "chest": ((0.0, 0.0, 3.12), (0.0, 0.0, 3.68)),
        "neck": ((0.0, 0.0, 3.68), (0.0, 0.0, 4.10)),
        "head": ((0.0, 0.0, 4.10), (0.0, 0.0, 5.10)),
        "ear.L": ((-0.44, 0.0, 5.18), (-0.78, 0.02, 6.02)),
        "ear.R": ((0.44, 0.0, 5.18), (0.78, 0.02, 6.02)),
        "upper_arm.L": ((-0.70, 0.0, 3.52), (-1.02, -0.01, 3.10)),
        "forearm.L": ((-1.02, -0.01, 3.10), (-1.09, -0.03, 2.54)),
        "hand.L": ((-1.09, -0.03, 2.54), (-1.08, -0.08, 2.18)),
        "upper_arm.R": ((0.70, 0.0, 3.52), (1.02, -0.01, 3.10)),
        "forearm.R": ((1.02, -0.01, 3.10), (1.09, -0.03, 2.54)),
        "hand.R": ((1.09, -0.03, 2.54), (1.08, -0.08, 2.18)),
        "thigh.L": ((-0.44, 0.0, 2.18), (-0.45, 0.0, 1.34)),
        "shin.L": ((-0.45, 0.0, 1.34), (-0.46, -0.02, 0.48)),
        "foot.L": ((-0.46, -0.02, 0.48), (-0.46, -0.72, 0.22)),
        "thigh.R": ((0.44, 0.0, 2.18), (0.45, 0.0, 1.34)),
        "shin.R": ((0.45, 0.0, 1.34), (0.46, -0.02, 0.48)),
        "foot.R": ((0.46, -0.02, 0.48), (0.46, -0.72, 0.22)),
        "tail.01": ((0.10, 0.42, 2.34), (0.40, 0.85, 2.20)),
        "tail.02": ((0.40, 0.85, 2.20), (0.82, 1.10, 1.80)),
        "tail.03": ((0.82, 1.10, 1.80), (1.16, 1.08, 1.25)),
        "tail.04": ((1.16, 1.08, 1.25), (1.30, 0.78, 0.72)),
    }

    bpy.ops.object.select_all(action="DESELECT")
    armature.hide_set(False)
    armature.hide_viewport = False
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (head, tail) in points.items():
        bone = armature.data.edit_bones.get(name)
        if bone is None:
            raise RuntimeError(f"Missing rig bone: {name}")
        bone.head = Vector(head)
        bone.tail = Vector(tail)
    bpy.ops.object.mode_set(mode="OBJECT")
    armature.select_set(False)
    return {name: (Vector(head), Vector(tail)) for name, (head, tail) in points.items()}


def parent_to_bone(obj: bpy.types.Object, armature: bpy.types.Object, bone_name: str) -> None:
    if armature.data.bones.get(bone_name) is None:
        raise RuntimeError(f"Cannot parent {obj.name}; missing bone {bone_name}")
    world_matrix = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world_matrix
    obj["cbanimal_rig_binding"] = "rigid_bone_proxy_v2"


def build_model(armature: bpy.types.Object) -> tuple[bpy.types.Collection, dict[str, str]]:
    model = clear_collection(MODEL_COLLECTION)
    teal = material("FOX_TEAL_V2", (0.055, 0.50, 0.55, 1.0))
    white = material("FOX_WHITE_V2", (0.84, 0.97, 0.96, 1.0))
    dark = material("FOX_DARK_TEAL_V2", (0.018, 0.12, 0.16, 1.0))
    cyan = material("FOX_CYAN_V2", (0.08, 0.86, 0.98, 1.0), emission=0.25)

    objects: dict[str, bpy.types.Object] = {}
    bone_map: dict[str, str] = {}

    def register(obj: bpy.types.Object, bone: str) -> bpy.types.Object:
        objects[obj.name] = obj
        bone_map[obj.name] = bone
        return obj

    # Core silhouette: slightly narrower torso and lower-volume pelvis.
    register(add_ico("MDL_PELVIS", (0.0, 0.02, 2.20), (0.68, 0.44, 0.58), teal, model), "pelvis")
    register(add_ico("MDL_TORSO", (0.0, -0.02, 3.08), (0.82, 0.48, 0.96), teal, model), "chest")
    register(add_cylinder_between("MDL_NECK", (0.0, 0.0, 3.72), (0.0, 0.0, 4.08), 0.30, teal, model), "neck")
    register(add_ico("MDL_HEAD", (0.0, 0.0, 4.76), (0.96, 0.74, 0.92), teal, model), "head")

    # Face layers create a fox mask rather than a single white blob.
    register(add_ico("MDL_CHEEK_L", (-0.36, -0.66, 4.53), (0.40, 0.13, 0.34), white, model, 1), "head")
    register(add_ico("MDL_CHEEK_R", (0.36, -0.66, 4.53), (0.40, 0.13, 0.34), white, model, 1), "head")
    register(add_ico("MDL_MUZZLE", (0.0, -0.78, 4.46), (0.48, 0.25, 0.32), white, model), "head")
    register(add_ico("MDL_NOSE", (0.0, -1.025, 4.47), (0.17, 0.10, 0.14), dark, model, 1), "head")
    register(add_ico("MDL_CHEST_PATCH", (0.0, -0.485, 3.18), (0.44, 0.10, 0.64), white, model, 1), "chest")

    for side, label, bone in ((-1.0, "L", "ear.L"), (1.0, "R", "ear.R")):
        register(
            add_cone_between(
                f"MDL_EAR_{label}",
                (0.46 * side, 0.0, 5.26),
                (0.80 * side, 0.02, 6.04),
                0.39,
                0.028,
                teal,
                model,
                vertices=8,
            ),
            bone,
        )
        register(
            add_cone_between(
                f"MDL_INNER_EAR_{label}",
                (0.49 * side, -0.18, 5.30),
                (0.76 * side, -0.17, 5.91),
                0.22,
                0.018,
                dark,
                model,
                vertices=8,
            ),
            bone,
        )
        register(
            add_cone_between(
                f"MDL_EAR_TIP_{label}",
                (0.68 * side, 0.015, 5.76),
                (0.80 * side, 0.02, 6.04),
                0.15,
                0.02,
                dark,
                model,
                vertices=8,
            ),
            bone,
        )

        register(add_ico(f"MDL_EYE_{label}", (0.31 * side, -0.727, 4.90), (0.22, 0.055, 0.27), dark, model, 1), "head")
        register(add_ico(f"MDL_PUPIL_{label}", (0.31 * side, -0.785, 4.90), (0.105, 0.035, 0.15), cyan, model, 1), "head")

    # Relaxed A-pose brought closer to the torso to match the concept silhouette.
    for side, label in ((-1.0, "L"), (1.0, "R")):
        shoulder = (0.70 * side, 0.0, 3.52)
        elbow = (1.02 * side, -0.01, 3.10)
        wrist = (1.09 * side, -0.03, 2.54)
        hand = (1.08 * side, -0.08, 2.25)
        register(add_ico(f"MDL_SHOULDER_{label}", shoulder, (0.28, 0.28, 0.28), teal, model, 1), f"upper_arm.{label}")
        register(add_cone_between(f"MDL_UPPER_ARM_{label}", shoulder, elbow, 0.24, 0.18, teal, model), f"upper_arm.{label}")
        register(add_ico(f"MDL_ELBOW_{label}", elbow, (0.22, 0.22, 0.22), teal, model, 1), f"forearm.{label}")
        register(add_cone_between(f"MDL_FOREARM_{label}", elbow, wrist, 0.19, 0.145, teal, model), f"forearm.{label}")
        register(add_ico(f"MDL_HAND_{label}", hand, (0.30, 0.25, 0.34), white, model, 1), f"hand.{label}")

        hip = (0.44 * side, 0.0, 2.18)
        knee = (0.45 * side, 0.0, 1.34)
        ankle = (0.46 * side, -0.02, 0.48)
        foot = (0.46 * side, -0.30, 0.23)
        register(add_ico(f"MDL_HIP_{label}", hip, (0.29, 0.29, 0.29), teal, model, 1), f"thigh.{label}")
        register(add_cone_between(f"MDL_THIGH_{label}", hip, knee, 0.30, 0.235, teal, model), f"thigh.{label}")
        register(add_ico(f"MDL_KNEE_{label}", knee, (0.25, 0.25, 0.25), teal, model, 1), f"shin.{label}")
        register(add_cone_between(f"MDL_SHIN_{label}", knee, ankle, 0.23, 0.17, teal, model), f"shin.{label}")
        register(add_ico(f"MDL_FOOT_{label}", foot, (0.42, 0.62, 0.25), white, model, 1), f"foot.{label}")

    # Lower, side-swept tail keeps the concept's large silhouette visible from front and side.
    tail_points = [
        (0.10, 0.42, 2.34),
        (0.40, 0.85, 2.20),
        (0.82, 1.10, 1.80),
        (1.16, 1.08, 1.25),
        (1.30, 0.78, 0.72),
    ]
    tail_radii = [0.36, 0.48, 0.52, 0.44, 0.24]
    for index in range(4):
        segment_mat = white if index == 3 else teal
        register(
            add_cone_between(
                f"MDL_TAIL_{index + 1:02d}",
                tail_points[index],
                tail_points[index + 1],
                tail_radii[index],
                tail_radii[index + 1],
                segment_mat,
                model,
                vertices=10,
            ),
            f"tail.{index + 1:02d}",
        )
    register(add_ico("MDL_TAIL_TIP", tail_points[-1], (0.28, 0.26, 0.31), white, model, 1), "tail.04")

    for name, bone_name in bone_map.items():
        parent_to_bone(objects[name], armature, bone_name)

    model.hide_viewport = False
    model.hide_render = False
    return model, bone_map


# Preserve the committed v1 source by immediately branching to a new .blend file.
OUTPUT_BLEND.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))

armature = bpy.data.objects.get(RIG_NAME)
rig_collection = bpy.data.collections.get(RIG_COLLECTION)
if armature is None or rig_collection is None:
    raise RuntimeError("FOX_RIG_GUIDE and RIG_GUIDE must exist before building proxy v2")

reset_pose(armature)
update_rig_rest_pose(armature)
model, bone_map = build_model(armature)

for collection_name in ("REFERENCES", "BLOCKOUT"):
    collection = bpy.data.collections.get(collection_name)
    if collection is not None:
        collection.hide_viewport = True
        collection.hide_render = True
rig_collection.hide_viewport = False
rig_collection.hide_render = True
armature.hide_set(False)
armature.hide_viewport = False

idle = bpy.data.actions.get("idle")
armature.animation_data_create()
armature.animation_data.action = idle
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 40
bpy.context.scene.frame_set(1)

bpy.context.scene["cbanimal_character_stage"] = "model_proxy_v2_silhouette_refined"
bpy.context.scene["cbanimal_proxy_v2_objects"] = len(model.objects)
bpy.context.scene["cbanimal_proxy_v2_notes"] = (
    "Evidence-driven silhouette pass: narrower A-pose, lower side-swept tail, larger paws, layered fox face."
)
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))

triangles = 0
vertices = 0
for obj in model.objects:
    if obj.type != "MESH":
        continue
    obj.data.calc_loop_triangles()
    triangles += len(obj.data.loop_triangles)
    vertices += len(obj.data.vertices)

print(
    "CBANIMAL_PROXY_V2_RESULT",
    {
        "blend": str(OUTPUT_BLEND),
        "objects": len(model.objects),
        "vertices": vertices,
        "triangles": triangles,
        "bones": len(armature.data.bones),
        "actions": sorted(action.name for action in bpy.data.actions),
        "bone_map_objects": len(bone_map),
    },
)
