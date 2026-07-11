import bpy
from mathutils import Vector

BLOCKOUT_COLLECTION = "BLOCKOUT"
MODEL_COLLECTION = "MODEL_PROXY"
RIG_COLLECTION = "RIG_GUIDE"
MODEL_PREFIX = "MDL_"
RIG_NAME = "FOX_RIG_GUIDE"


def ensure_collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def clear_collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        return
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(collection)


def set_reference_display():
    for name in ("REF_FRONT", "REF_SIDE", "REF_BACK", "REF_THREE_QUARTER"):
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        obj.hide_set(True)
        obj.hide_viewport = True
        obj.hide_render = True
        obj.select_set(False)
        if obj.type == "EMPTY":
            try:
                obj.empty_display_type = "IMAGE"
                obj.empty_image_depth = "BACK"
            except Exception:
                pass
            try:
                obj.color[3] = 0.18
            except Exception:
                pass


def duplicate_blockout_to_model():
    source = bpy.data.collections.get(BLOCKOUT_COLLECTION)
    if source is None:
        raise RuntimeError("BLOCKOUT collection does not exist")

    clear_collection(MODEL_COLLECTION)
    target = ensure_collection(MODEL_COLLECTION)
    duplicates = []

    for obj in source.objects:
        if obj.type != "MESH":
            continue
        dup = obj.copy()
        dup.data = obj.data.copy()
        dup.animation_data_clear()
        dup.name = MODEL_PREFIX + obj.name.removeprefix("BLK_")
        target.objects.link(dup)
        dup.hide_set(False)
        dup.hide_viewport = False
        dup.hide_render = False
        dup.display_type = "TEXTURED"
        dup.show_in_front = False
        for polygon in dup.data.polygons:
            polygon.use_smooth = True
        dup["cbanimal_stage"] = "model_proxy"
        duplicates.append(dup)

    source.hide_viewport = True
    source.hide_render = True
    for obj in source.objects:
        obj.hide_set(True)
        obj.select_set(False)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in duplicates:
        obj.select_set(True)
    if duplicates:
        bpy.context.view_layer.objects.active = duplicates[0]
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.select_all(action="DESELECT")
    return target, duplicates


def create_rig_guide():
    clear_collection(RIG_COLLECTION)
    rig_collection = ensure_collection(RIG_COLLECTION)

    armature_data = bpy.data.armatures.new(RIG_NAME + "_DATA")
    armature_obj = bpy.data.objects.new(RIG_NAME, armature_data)
    rig_collection.objects.link(armature_obj)
    armature_obj.show_in_front = True
    armature_obj.display_type = "WIRE"
    armature_obj.hide_render = True
    armature_obj["cbanimal_stage"] = "rig_proportion_guide"

    bpy.ops.object.select_all(action="DESELECT")
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="EDIT")

    bones = {}

    def add_bone(name, head, tail, parent=None, connected=False):
        bone = armature_data.edit_bones.new(name)
        bone.head = Vector(head)
        bone.tail = Vector(tail)
        if parent:
            bone.parent = bones[parent]
            bone.use_connect = connected
        bones[name] = bone
        return bone

    add_bone("root", (0, 0, 0.05), (0, 0, 0.45))
    add_bone("pelvis", (0, 0, 2.05), (0, 0, 2.55), "root")
    add_bone("spine", (0, 0, 2.55), (0, 0, 3.15), "pelvis", True)
    add_bone("chest", (0, 0, 3.15), (0, 0, 3.72), "spine", True)
    add_bone("neck", (0, 0, 3.72), (0, 0, 4.12), "chest", True)
    add_bone("head", (0, 0, 4.12), (0, 0, 5.12), "neck", True)

    for side, sign in (("L", -1.0), ("R", 1.0)):
        add_bone(f"ear.{side}", (0.42 * sign, 0, 5.20), (0.66 * sign, 0, 5.95), "head")
        add_bone(f"upper_arm.{side}", (0.68 * sign, 0, 3.55), (1.24 * sign, 0, 3.02), "chest")
        add_bone(f"forearm.{side}", (1.24 * sign, 0, 3.02), (1.45 * sign, -0.03, 2.38), f"upper_arm.{side}", True)
        add_bone(f"hand.{side}", (1.45 * sign, -0.03, 2.38), (1.52 * sign, -0.09, 2.05), f"forearm.{side}", True)
        add_bone(f"thigh.{side}", (0.47 * sign, 0, 2.20), (0.48 * sign, 0, 1.32), "pelvis")
        add_bone(f"shin.{side}", (0.48 * sign, 0, 1.32), (0.49 * sign, -0.03, 0.48), f"thigh.{side}", True)
        add_bone(f"foot.{side}", (0.49 * sign, -0.03, 0.48), (0.49 * sign, -0.68, 0.22), f"shin.{side}", True)

    add_bone("tail.01", (0, 0.42, 2.35), (0.25, 0.78, 2.62), "pelvis")
    add_bone("tail.02", (0.25, 0.78, 2.62), (0.55, 1.10, 2.98), "tail.01", True)
    add_bone("tail.03", (0.55, 1.10, 2.98), (0.82, 1.22, 3.43), "tail.02", True)
    add_bone("tail.04", (0.82, 1.22, 3.43), (1.02, 1.02, 3.92), "tail.03", True)

    bpy.ops.object.mode_set(mode="OBJECT")
    armature_obj.select_set(False)
    rig_collection.hide_render = True
    return rig_collection, armature_obj, len(bones)


def configure_viewport():
    configured = 0
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            if space.type != "VIEW_3D":
                continue
            space.shading.type = "MATERIAL"
            space.shading.color_type = "MATERIAL"
            space.shading.light = "STUDIO"
            space.shading.show_shadows = True
            space.shading.show_cavity = True
            space.shading.cavity_type = "WORLD"
            space.overlay.show_object_origins = False
            space.overlay.show_relationship_lines = False
            space.overlay.show_outline_selected = False
            space.overlay.show_bones = True
            space.overlay.show_floor = True
            space.overlay.show_axis_x = True
            space.overlay.show_axis_y = True
            configured += 1
    return configured


set_reference_display()
model_collection, model_objects = duplicate_blockout_to_model()
rig_collection, rig_object, bone_count = create_rig_guide()
rig_collection.hide_viewport = True
model_collection.hide_viewport = False
configured_views = configure_viewport()

bpy.ops.object.select_all(action="DESELECT")
bpy.context.scene["cbanimal_character_stage"] = "model_proxy_with_rig_guide"
bpy.context.scene["cbanimal_model_proxy_objects"] = len(model_objects)
bpy.context.scene["cbanimal_rig_guide_bones"] = bone_count
bpy.context.scene["cbanimal_references_hidden_for_model_review"] = True
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

result = {
    "file": bpy.data.filepath,
    "model_collection": model_collection.name,
    "model_objects": len(model_objects),
    "rig_collection": rig_collection.name,
    "rig_object": rig_object.name,
    "rig_bones": bone_count,
    "viewport_areas_configured": configured_views,
    "references_hidden": True,
    "blockout_preserved_hidden": True,
}
print("CBANIMAL_MODEL_PROXY_RESULT", result)
