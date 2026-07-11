import bpy
import math

mode = globals().get("VIEW_MODE", "THREE_QUARTER").upper()
show_rig = bool(globals().get("SHOW_RIG", False))
if mode not in {"FRONT", "SIDE", "THREE_QUARTER"}:
    raise ValueError(f"Unsupported VIEW_MODE: {mode}")

for name in ("REF_FRONT", "REF_SIDE", "REF_BACK", "REF_THREE_QUARTER"):
    obj = bpy.data.objects.get(name)
    if obj is not None:
        obj.hide_set(True)
        obj.hide_viewport = True
        obj.select_set(False)

blockout = bpy.data.collections.get("BLOCKOUT")
if blockout is not None:
    blockout.hide_viewport = True
    for obj in blockout.objects:
        obj.hide_set(True)
        obj.select_set(False)

model = bpy.data.collections.get("MODEL_PROXY")
if model is None:
    raise RuntimeError("MODEL_PROXY collection does not exist")
model.hide_viewport = False
model_objects = [obj for obj in model.objects if obj.type == "MESH"]
for obj in model_objects:
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.display_type = "TEXTURED"

rig = bpy.data.collections.get("RIG_GUIDE")
if rig is not None:
    # The model pieces are bone-parented to the armature. Hiding the armature
    # collection also hides its children, so keep the parent evaluable and
    # control only the bone drawing through the viewport overlay below.
    rig.hide_viewport = False
    for obj in rig.objects:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.select_set(False)

bpy.ops.object.select_all(action="DESELECT")
for obj in model_objects:
    obj.select_set(True)
if model_objects:
    bpy.context.view_layer.objects.active = model_objects[0]

configured = False
for window in bpy.context.window_manager.windows:
    screen = window.screen
    for area in screen.areas:
        if area.type != "VIEW_3D":
            continue
        region = next((item for item in area.regions if item.type == "WINDOW"), None)
        space = area.spaces.active
        if region is None or space.type != "VIEW_3D":
            continue
        with bpy.context.temp_override(window=window, screen=screen, area=area, region=region, space_data=space):
            if mode == "FRONT":
                bpy.ops.view3d.view_axis(type="FRONT", align_active=False)
            elif mode == "SIDE":
                bpy.ops.view3d.view_axis(type="RIGHT", align_active=False)
            else:
                bpy.ops.view3d.view_axis(type="FRONT", align_active=False)
                bpy.ops.view3d.view_orbit(type="ORBITLEFT", angle=math.radians(38.0))
                bpy.ops.view3d.view_orbit(type="ORBITUP", angle=math.radians(6.0))

            bpy.ops.view3d.view_selected(use_all_regions=False)
            space.region_3d.view_distance *= 1.14
            space.region_3d.view_perspective = "ORTHO" if mode != "THREE_QUARTER" else "PERSP"
            space.shading.type = "MATERIAL"
            space.shading.color_type = "MATERIAL"
            space.shading.light = "STUDIO"
            space.shading.show_shadows = True
            space.shading.show_cavity = True
            space.shading.cavity_type = "WORLD"
            space.overlay.show_object_origins = False
            space.overlay.show_relationship_lines = False
            space.overlay.show_outline_selected = False
            space.overlay.show_floor = True
            space.overlay.show_axis_x = True
            space.overlay.show_axis_y = True
            space.overlay.show_bones = show_rig
        configured = True
        break
    if configured:
        break

bpy.ops.object.select_all(action="DESELECT")
if not configured:
    raise RuntimeError("No VIEW_3D area found")

bpy.context.scene["cbanimal_model_review_view"] = mode
bpy.context.scene["cbanimal_model_review_rig_visible"] = show_rig
result = {
    "mode": mode,
    "model_objects": len(model_objects),
    "rig_visible": show_rig,
    "selected_after_frame": len(bpy.context.selected_objects),
    "references_visible": False,
}
print("CBANIMAL_MODEL_REVIEW_VIEW", result)
