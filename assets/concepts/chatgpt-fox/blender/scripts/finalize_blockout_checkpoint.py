import bpy

visibility = {
    "REF_FRONT": True,
    "REF_SIDE": True,
    "REF_BACK": False,
    "REF_THREE_QUARTER": False,
}
for name, visible in visibility.items():
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
        obj.select_set(True)
if blockout.objects:
    bpy.context.view_layer.objects.active = blockout.objects[0]

configured = False
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type != "VIEW_3D":
            continue
        region = next((item for item in area.regions if item.type == "WINDOW"), None)
        if region is None:
            continue
        space = area.spaces.active
        with bpy.context.temp_override(window=window, screen=window.screen, area=area, region=region, space_data=space):
            bpy.ops.view3d.view_axis(type="FRONT", align_active=False)
            bpy.ops.view3d.view_selected(use_all_regions=False)
            space.region_3d.view_distance *= 1.18
            space.region_3d.view_perspective = "ORTHO"
            space.shading.type = "MATERIAL"
            space.shading.color_type = "MATERIAL"
            space.shading.show_shadows = True
            space.shading.show_cavity = True
            space.overlay.show_relationship_lines = False
        configured = True
        break
    if configured:
        break

bpy.context.scene["cbanimal_blockout_review"] = "awaiting_user_approval"
bpy.context.scene["cbanimal_review_view"] = "FRONT_WORKING"
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

result = {
    "saved": bpy.data.filepath,
    "front_visible": not bpy.data.objects["REF_FRONT"].hide_viewport,
    "side_visible": not bpy.data.objects["REF_SIDE"].hide_viewport,
    "back_visible": not bpy.data.objects["REF_BACK"].hide_viewport,
    "three_quarter_visible": not bpy.data.objects["REF_THREE_QUARTER"].hide_viewport,
    "blockout_objects": len(blockout.objects),
}
print("CBANIMAL_BLOCKOUT_CHECKPOINT", result)
