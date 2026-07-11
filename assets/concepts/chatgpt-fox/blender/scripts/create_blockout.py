import bpy
import math
from mathutils import Vector

BLOCKOUT_COLLECTION = "BLOCKOUT"
REFERENCES_COLLECTION = "REFERENCES"


def ensure_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def clear_collection(collection: bpy.types.Collection) -> None:
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get("Principled BSDF") if mat.node_tree else None
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = 0.72
    return mat


def finish_object(obj: bpy.types.Object, collection: bpy.types.Collection, mat: bpy.types.Material) -> bpy.types.Object:
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.color = mat.diffuse_color
    obj.show_in_front = True
    if hasattr(obj.data, "polygons"):
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    move_to_collection(obj, collection)
    return obj


def add_ico(name: str, location, scale, mat, collection, subdivisions: int = 2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    return finish_object(obj, collection, mat)


def add_cylinder_between(name: str, start, end, radius: float, mat, collection, vertices: int = 8):
    start_v = Vector(start)
    end_v = Vector(end)
    direction = end_v - start_v
    length = direction.length
    midpoint = (start_v + end_v) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=length, location=midpoint)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    obj.rotation_mode = "XYZ"
    return finish_object(obj, collection, mat)


def add_cone_between(name: str, start, end, radius_start: float, radius_end: float, mat, collection, vertices: int = 8):
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
        location=midpoint,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    obj.rotation_mode = "XYZ"
    return finish_object(obj, collection, mat)


def build_blockout() -> dict:
    blockout = ensure_collection(BLOCKOUT_COLLECTION)
    clear_collection(blockout)

    teal = material("FOX_TEAL_BLOCKOUT", (0.08, 0.58, 0.62, 1.0))
    white = material("FOX_WHITE_BLOCKOUT", (0.84, 0.96, 0.95, 1.0))
    dark = material("FOX_DARK_TEAL_BLOCKOUT", (0.025, 0.19, 0.23, 1.0))
    cyan = material("FOX_CYAN_BLOCKOUT", (0.12, 0.88, 0.96, 1.0))

    # Central masses: overall height approximately six Blender units.
    add_ico("BLK_PELVIS", (0.0, 0.0, 2.25), (0.74, 0.48, 0.58), teal, blockout)
    add_ico("BLK_TORSO", (0.0, 0.0, 3.10), (0.92, 0.54, 0.98), teal, blockout)
    add_cylinder_between("BLK_NECK", (0.0, 0.0, 3.75), (0.0, 0.0, 4.05), 0.34, teal, blockout)
    add_ico("BLK_HEAD", (0.0, 0.0, 4.75), (1.02, 0.82, 0.98), teal, blockout, subdivisions=2)
    add_ico("BLK_MUZZLE", (0.0, -0.74, 4.48), (0.54, 0.30, 0.38), white, blockout)
    add_ico("BLK_CHEST_PATCH", (0.0, -0.49, 3.18), (0.48, 0.11, 0.66), white, blockout, subdivisions=1)

    # Large pointed fox ears with compact dark tips.
    for side, label in ((-1.0, "L"), (1.0, "R")):
        add_cone_between(
            f"BLK_EAR_{label}",
            (0.48 * side, 0.0, 5.28),
            (0.72 * side, 0.02, 5.98),
            0.40,
            0.035,
            teal,
            blockout,
            vertices=6,
        )
        add_cone_between(
            f"BLK_EAR_TIP_{label}",
            (0.64 * side, 0.015, 5.72),
            (0.72 * side, 0.02, 5.98),
            0.16,
            0.025,
            dark,
            blockout,
            vertices=6,
        )

    # Friendly oversized eye placeholders.
    for side, label in ((-1.0, "L"), (1.0, "R")):
        add_ico(f"BLK_EYE_{label}", (0.32 * side, -0.755, 4.88), (0.19, 0.085, 0.25), cyan, blockout, subdivisions=1)

    # Relaxed humanoid A-pose. Both sides share identical dimensions.
    for side, label in ((-1.0, "L"), (1.0, "R")):
        shoulder = (0.78 * side, 0.0, 3.58)
        elbow = (1.24 * side, -0.01, 3.02)
        wrist = (1.42 * side, -0.03, 2.43)
        hand = (1.48 * side, -0.06, 2.22)
        add_ico(f"BLK_SHOULDER_{label}", shoulder, (0.34, 0.34, 0.34), teal, blockout, subdivisions=1)
        add_cylinder_between(f"BLK_UPPER_ARM_{label}", shoulder, elbow, 0.25, teal, blockout)
        add_ico(f"BLK_ELBOW_{label}", elbow, (0.27, 0.27, 0.27), teal, blockout, subdivisions=1)
        add_cylinder_between(f"BLK_FOREARM_{label}", elbow, wrist, 0.22, teal, blockout)
        add_ico(f"BLK_HAND_{label}", hand, (0.31, 0.27, 0.34), white, blockout, subdivisions=1)

        hip = (0.47 * side, 0.0, 2.23)
        knee = (0.48 * side, 0.0, 1.32)
        ankle = (0.49 * side, -0.01, 0.48)
        foot = (0.49 * side, -0.20, 0.22)
        add_ico(f"BLK_HIP_{label}", hip, (0.32, 0.32, 0.32), teal, blockout, subdivisions=1)
        add_cylinder_between(f"BLK_THIGH_{label}", hip, knee, 0.30, teal, blockout)
        add_ico(f"BLK_KNEE_{label}", knee, (0.29, 0.29, 0.29), teal, blockout, subdivisions=1)
        add_cylinder_between(f"BLK_SHIN_{label}", knee, ankle, 0.25, teal, blockout)
        add_ico(f"BLK_FOOT_{label}", foot, (0.40, 0.58, 0.25), white, blockout, subdivisions=1)

    # One large tapered tail. Character faces -Y, so +Y is behind the body.
    tail_points = [
        (0.12, 0.38, 2.38),
        (0.38, 0.86, 2.58),
        (0.68, 1.18, 3.02),
        (0.92, 1.20, 3.52),
        (1.02, 0.98, 3.92),
    ]
    tail_radii = [0.38, 0.48, 0.52, 0.43, 0.22]
    for index in range(len(tail_points) - 1):
        segment_mat = white if index == len(tail_points) - 2 else teal
        add_cone_between(
            f"BLK_TAIL_{index + 1:02d}",
            tail_points[index],
            tail_points[index + 1],
            tail_radii[index],
            tail_radii[index + 1],
            segment_mat,
            blockout,
            vertices=8,
        )
    add_ico("BLK_TAIL_TIP", tail_points[-1], (0.25, 0.25, 0.32), white, blockout, subdivisions=1)

    # Keep references untouched and make the blockout easy to isolate.
    references = bpy.data.collections.get(REFERENCES_COLLECTION)
    if references is not None:
        references.hide_viewport = False
        references.hide_render = True

    blockout.hide_viewport = False
    blockout.hide_render = False

    scene = bpy.context.scene
    scene["cbanimal_character"] = "chatgpt-fox"
    scene["cbanimal_blockout_stage"] = "first_low_poly_blockout"
    scene["cbanimal_blockout_notes"] = "Silhouette-first mirrored primitives; no fur strands or circuit detail."

    bpy.ops.object.select_all(action="DESELECT")
    for obj in blockout.objects:
        obj.select_set(True)
    if blockout.objects:
        bpy.context.view_layer.objects.active = blockout.objects[0]

    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

    mesh_objects = [obj for obj in blockout.objects if obj.type == "MESH"]
    triangles = sum(len(obj.data.loop_triangles) for obj in mesh_objects)
    # Ensure triangle caches are populated for reliable totals.
    triangles = 0
    vertices = 0
    for obj in mesh_objects:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
        vertices += len(obj.data.vertices)

    return {
        "collection": blockout.name,
        "objects": len(blockout.objects),
        "mesh_objects": len(mesh_objects),
        "vertices": vertices,
        "triangles": triangles,
        "blend_file": bpy.data.filepath,
    }


result = build_blockout()
print("CBANIMAL_BLOCKOUT_RESULT", result)
