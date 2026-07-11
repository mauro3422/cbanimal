import bpy
from mathutils import Vector
from pathlib import Path

OUTPUT_DIR = Path(r"C:\dev\cbanimal\assets\concepts\chatgpt-fox\blender")
REVIEW_COLLECTION = "REVIEW_RENDER"
RIG_MARKERS_COLLECTION = "REVIEW_RIG_MARKERS"


def remove_collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        return
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(collection)


def ensure_collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, target):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    target.objects.link(obj)


def make_material(name, color, metallic=0.0, roughness=0.55, emission=None):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if emission is not None:
            emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
            if emission_input is not None:
                emission_input.default_value = (*emission, 1.0)
            strength_input = bsdf.inputs.get("Emission Strength")
            if strength_input is not None:
                strength_input.default_value = 2.0
    return material


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_area_light(collection, name, location, energy, size, target=(0, 0, 3)):
    data = bpy.data.lights.new(name + "_DATA", type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


def add_camera(collection):
    data = bpy.data.cameras.new("FOX_REVIEW_CAMERA_DATA")
    camera = bpy.data.objects.new("FOX_REVIEW_CAMERA", data)
    collection.objects.link(camera)
    bpy.context.scene.camera = camera
    data.lens = 62
    data.clip_start = 0.05
    data.clip_end = 100
    return camera


def add_floor(collection):
    bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "FOX_REVIEW_FLOOR"
    move_to_collection(floor, collection)
    floor.data.materials.append(make_material("FOX_REVIEW_FLOOR_MAT", (0.075, 0.09, 0.11), roughness=0.82))
    return floor


def render_view(camera, name, location, target=(0, 0, 3.0), orthographic=True, scale=7.2):
    camera.location = location
    look_at(camera, target)
    camera.data.type = "ORTHO" if orthographic else "PERSP"
    if orthographic:
        camera.data.ortho_scale = scale
    bpy.context.scene.render.filepath = str(OUTPUT_DIR / name)
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    path = OUTPUT_DIR / name
    return {"path": str(path), "bytes": path.stat().st_size}


def create_rig_markers(armature):
    remove_collection(RIG_MARKERS_COLLECTION)
    collection = ensure_collection(RIG_MARKERS_COLLECTION)
    material = make_material("FOX_RIG_MARKER_MAT", (1.0, 0.3, 0.04), roughness=0.25, emission=(1.0, 0.12, 0.01))
    marker_count = 0

    for bone in armature.data.bones:
        head = armature.matrix_world @ bone.head_local
        tail = armature.matrix_world @ bone.tail_local
        # Offset toward the front review camera so markers remain readable over the mesh.
        head.y -= 0.95
        tail.y -= 0.95
        delta = tail - head
        length = delta.length
        if length <= 1e-5:
            continue
        midpoint = (head + tail) * 0.5
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.035, depth=length, location=midpoint)
        marker = bpy.context.object
        marker.name = "RIG_MARKER_" + bone.name
        move_to_collection(marker, collection)
        marker.rotation_euler = delta.to_track_quat("Z", "Y").to_euler()
        marker.data.materials.append(material)
        marker_count += 1

        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.075, location=head)
        joint = bpy.context.object
        joint.name = "RIG_JOINT_" + bone.name
        move_to_collection(joint, collection)
        joint.data.materials.append(material)
        marker_count += 1

    return collection, marker_count


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
remove_collection(REVIEW_COLLECTION)
remove_collection(RIG_MARKERS_COLLECTION)
review = ensure_collection(REVIEW_COLLECTION)

for name in ("REF_FRONT", "REF_SIDE", "REF_BACK", "REF_THREE_QUARTER"):
    obj = bpy.data.objects.get(name)
    if obj is not None:
        obj.hide_render = True
        obj.hide_viewport = True

blockout = bpy.data.collections.get("BLOCKOUT")
if blockout is not None:
    blockout.hide_render = True
    blockout.hide_viewport = True

model = bpy.data.collections.get("MODEL_PROXY")
armature = bpy.data.objects.get("FOX_RIG_GUIDE")
if model is None or armature is None:
    raise RuntimeError("MODEL_PROXY and FOX_RIG_GUIDE are required")
model.hide_render = False
model.hide_viewport = False
for obj in model.objects:
    obj.hide_render = False
    obj.hide_viewport = False
    obj.hide_set(False)

rig_collection = bpy.data.collections.get("RIG_GUIDE")
if rig_collection is not None:
    rig_collection.hide_viewport = False
armature.hide_set(False)
armature.hide_viewport = False
armature.hide_render = True
armature.animation_data.action = bpy.data.actions.get("idle")
bpy.context.scene.frame_set(1)

camera = add_camera(review)
add_floor(review)
add_area_light(review, "FOX_KEY", (4.5, -6.5, 8.0), 950, 5.0)
add_area_light(review, "FOX_FILL", (-4.0, -3.0, 5.0), 520, 4.0)
add_area_light(review, "FOX_RIM", (1.0, 5.5, 7.0), 760, 3.5)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 700
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.render.use_file_extension = True
if scene.world is None:
    scene.world = bpy.data.worlds.new("FOX_REVIEW_WORLD")
scene.world.color = (0.025, 0.035, 0.045)
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background")
if background is not None:
    background.inputs["Color"].default_value = (0.025, 0.035, 0.045, 1.0)
    background.inputs["Strength"].default_value = 0.35

renders = []
renders.append(render_view(camera, "model_front.png", (0, -11.5, 3.0), orthographic=True))
renders.append(render_view(camera, "model_side.png", (11.5, 0, 3.0), orthographic=True))
renders.append(render_view(camera, "model_three_quarter.png", (8.2, -8.2, 3.55), target=(0, 0, 3.0), orthographic=False))

markers, marker_count = create_rig_markers(armature)
markers.hide_render = False
renders.append(render_view(camera, "rig_guide_front.png", (0, -11.5, 3.0), orthographic=True))
markers.hide_render = True

remove_collection(RIG_MARKERS_COLLECTION)
remove_collection(REVIEW_COLLECTION)
scene["cbanimal_review_renders"] = ",".join(Path(item["path"]).name for item in renders)
scene["cbanimal_rig_marker_count"] = marker_count
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

print("CBANIMAL_RENDER_REVIEW_RESULT", {"renders": renders, "rig_markers": marker_count})
