import bpy
import math

mode = globals().get("VIEW_MODE", "FRONT").upper()
if mode not in {"FRONT", "SIDE", "THREE_QUARTER"}:
    raise ValueError(f"Unsupported VIEW_MODE: {mode}")

reference_visibility = {
    "REF_FRONT": mode == "FRONT",
    "REF_SIDE": mode == "SIDE",
    "REF_BACK": False,
    "REF_THREE_QUARTER": False,
}
for name, visible in reference_visibility.items():
    obj = bpy.data.objects.get(name)
    if obj is not None:
        obj.hide_set(not visible)
        obj.hide_viewport = not visible

blockout = bpy.data.collections.get("BLOCKOUT")
if blockout is None:
    raise RuntimeError("BLOCKOUT collection does not exist")

bpy.ops.object.select_all(action="DESELECT")
for obj in blockout.objects:
    if obj.type == "MESH":
        obj.hide_set(False)
        obj.select_set(True)
if blockout.objects:
    bpy.context.view_layer.objects.active = blockout.objects[0]

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
                bpy.ops.view3d.view_orbit(type="ORBITLEFT", angle=math.radians(42.0))
                bpy.ops.view3d.view_orbit(type="ORBITUP", angle=math.radians(7.0))

            bpy.ops.view3d.view_selected(use_all_regions=False)
            space.region_3d.view_distance *= 1.18
            space.region_3d.view_perspective = "ORTHO" if mode != "THREE_QUARTER" else "PERSP"
            space.shading.type = "MATERIAL"
            space.shading.color_type = "MATERIAL"
            space.shading.light = "STUDIO"
            space.shading.show_shadows = True
            space.shading.show_cavity = True
            space.shading.cavity_type = "WORLD"
            space.overlay.show_relationship_lines = False
            space.overlay.show_outline_selected = True
            space.overlay.show_floor = True
            space.overlay.show_axis_x = True
            space.overlay.show_axis_y = True
        configured = True
        break
    if configured:
        break

if not configured:
    raise RuntimeError("No VIEW_3D area found")

bpy.context.scene["cbanimal_review_view"] = mode
result = {
    "mode": mode,
    "selected": len(bpy.context.selected_objects),
    "front_reference": reference_visibility["REF_FRONT"],
    "side_reference": reference_visibility["REF_SIDE"],
}
print("CBANIMAL_REVIEW_VIEW", result)
