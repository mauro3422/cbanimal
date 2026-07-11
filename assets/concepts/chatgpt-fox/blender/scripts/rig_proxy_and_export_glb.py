import bpy
from math import radians
from pathlib import Path

MODEL_COLLECTION = "MODEL_PROXY"
RIG_COLLECTION = "RIG_GUIDE"
RIG_NAME = "FOX_RIG_GUIDE"
EXPORT_PATH = Path(r"C:\dev\cbanimal\client\public\models\chatgpt-fox-proxy-v1.glb")

model = bpy.data.collections.get(MODEL_COLLECTION)
rig_collection = bpy.data.collections.get(RIG_COLLECTION)
armature = bpy.data.objects.get(RIG_NAME)
if model is None or armature is None or rig_collection is None:
    raise RuntimeError("MODEL_PROXY and FOX_RIG_GUIDE must exist before rigging")

bone_map = {
    "MDL_PELVIS": "pelvis",
    "MDL_TORSO": "chest",
    "MDL_NECK": "neck",
    "MDL_HEAD": "head",
    "MDL_MUZZLE": "head",
    "MDL_CHEST_PATCH": "chest",
    "MDL_EAR_L": "ear.L",
    "MDL_EAR_TIP_L": "ear.L",
    "MDL_EAR_R": "ear.R",
    "MDL_EAR_TIP_R": "ear.R",
    "MDL_EYE_L": "head",
    "MDL_EYE_R": "head",
    "MDL_SHOULDER_L": "upper_arm.L",
    "MDL_UPPER_ARM_L": "upper_arm.L",
    "MDL_ELBOW_L": "forearm.L",
    "MDL_FOREARM_L": "forearm.L",
    "MDL_HAND_L": "hand.L",
    "MDL_HIP_L": "thigh.L",
    "MDL_THIGH_L": "thigh.L",
    "MDL_KNEE_L": "shin.L",
    "MDL_SHIN_L": "shin.L",
    "MDL_FOOT_L": "foot.L",
    "MDL_SHOULDER_R": "upper_arm.R",
    "MDL_UPPER_ARM_R": "upper_arm.R",
    "MDL_ELBOW_R": "forearm.R",
    "MDL_FOREARM_R": "forearm.R",
    "MDL_HAND_R": "hand.R",
    "MDL_HIP_R": "thigh.R",
    "MDL_THIGH_R": "thigh.R",
    "MDL_KNEE_R": "shin.R",
    "MDL_SHIN_R": "shin.R",
    "MDL_FOOT_R": "foot.R",
    "MDL_TAIL_01": "tail.01",
    "MDL_TAIL_02": "tail.02",
    "MDL_TAIL_03": "tail.03",
    "MDL_TAIL_04": "tail.04",
    "MDL_TAIL_TIP": "tail.04",
}

missing_objects = sorted(name for name in bone_map if bpy.data.objects.get(name) is None)
missing_bones = sorted({bone for bone in bone_map.values() if armature.data.bones.get(bone) is None})
if missing_objects or missing_bones:
    raise RuntimeError(f"Rig map invalid: missing objects={missing_objects}, missing bones={missing_bones}")

for object_name, bone_name in bone_map.items():
    obj = bpy.data.objects[object_name]
    world_matrix = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world_matrix
    obj["cbanimal_rig_binding"] = "rigid_bone_proxy"

armature.animation_data_create()
for name in ("idle", "walking", "sitting", "wave"):
    existing = bpy.data.actions.get(name)
    if existing is not None:
        bpy.data.actions.remove(existing)


def reset_pose():
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)


def key_pose(frame, rotations=None, locations=None):
    rotations = rotations or {}
    locations = locations or {}
    bpy.context.scene.frame_set(frame)
    for bone_name, values in rotations.items():
        bone = armature.pose.bones[bone_name]
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = tuple(radians(value) for value in values)
        bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone_name)
    for bone_name, values in locations.items():
        bone = armature.pose.bones[bone_name]
        bone.location = values
        bone.keyframe_insert(data_path="location", frame=frame, group=bone_name)


def make_action(name, frame_end, keyframes, cyclic=False):
    action = bpy.data.actions.new(name=name)
    action.use_fake_user = True
    armature.animation_data.action = action
    reset_pose()
    for keyframe in keyframes:
        key_pose(*keyframe)
    # Blender 5 uses layered/slotted Actions instead of exposing action.fcurves.
    # Matching first/end poses provide clean looping in Three.js without adding
    # Blender-side cycle modifiers.
    try:
        action.use_frame_range = True
        action.frame_start = 1
        action.frame_end = frame_end
    except Exception:
        pass
    armature.animation_data.action = None
    return action


idle = make_action(
    "idle",
    40,
    [
        (1, {"chest": (0, 0, 0), "head": (0, 0, -1.5), "tail.01": (0, 0, -4), "tail.02": (0, 0, -3), "tail.03": (0, 0, -2), "tail.04": (0, 0, -1)}, {"pelvis": (0, 0, 0)}),
        (20, {"chest": (1.4, 0, 0), "head": (0, 0, 1.5), "tail.01": (0, 0, 5), "tail.02": (0, 0, 4), "tail.03": (0, 0, 3), "tail.04": (0, 0, 2)}, {"pelvis": (0, 0, 0.025)}),
        (40, {"chest": (0, 0, 0), "head": (0, 0, -1.5), "tail.01": (0, 0, -4), "tail.02": (0, 0, -3), "tail.03": (0, 0, -2), "tail.04": (0, 0, -1)}, {"pelvis": (0, 0, 0)}),
    ],
    cyclic=True,
)

walking = make_action(
    "walking",
    32,
    [
        (1, {"upper_arm.L": (0, 24, 0), "upper_arm.R": (0, -24, 0), "thigh.L": (0, -27, 0), "thigh.R": (0, 27, 0), "tail.01": (0, 0, -7)}, {"pelvis": (0, 0, 0.02)}),
        (9, {"upper_arm.L": (0, 0, 0), "upper_arm.R": (0, 0, 0), "thigh.L": (0, 0, 0), "thigh.R": (0, 0, 0), "tail.01": (0, 0, 0)}, {"pelvis": (0, 0, 0.07)}),
        (17, {"upper_arm.L": (0, -24, 0), "upper_arm.R": (0, 24, 0), "thigh.L": (0, 27, 0), "thigh.R": (0, -27, 0), "tail.01": (0, 0, 7)}, {"pelvis": (0, 0, 0.02)}),
        (25, {"upper_arm.L": (0, 0, 0), "upper_arm.R": (0, 0, 0), "thigh.L": (0, 0, 0), "thigh.R": (0, 0, 0), "tail.01": (0, 0, 0)}, {"pelvis": (0, 0, 0.07)}),
        (32, {"upper_arm.L": (0, 24, 0), "upper_arm.R": (0, -24, 0), "thigh.L": (0, -27, 0), "thigh.R": (0, 27, 0), "tail.01": (0, 0, -7)}, {"pelvis": (0, 0, 0.02)}),
    ],
    cyclic=True,
)

sitting = make_action(
    "sitting",
    24,
    [
        (1, {"thigh.L": (0, 0, 0), "thigh.R": (0, 0, 0), "shin.L": (0, 0, 0), "shin.R": (0, 0, 0)}, {"pelvis": (0, 0, 0)}),
        (12, {"thigh.L": (0, -32, 0), "thigh.R": (0, 32, 0), "shin.L": (0, 28, 0), "shin.R": (0, -28, 0), "tail.01": (12, 0, 0)}, {"pelvis": (0, 0, -0.45)}),
        (24, {"thigh.L": (0, -32, 0), "thigh.R": (0, 32, 0), "shin.L": (0, 28, 0), "shin.R": (0, -28, 0), "tail.01": (12, 0, 0)}, {"pelvis": (0, 0, -0.45)}),
    ],
)

wave = make_action(
    "wave",
    48,
    [
        (1, {"upper_arm.R": (0, 0, 0), "forearm.R": (0, 0, 0), "hand.R": (0, 0, 0)}, {}),
        (10, {"upper_arm.R": (0, -58, 12), "forearm.R": (0, -72, 0), "hand.R": (0, 0, -12)}, {}),
        (20, {"upper_arm.R": (0, -58, 12), "forearm.R": (0, -72, 0), "hand.R": (0, 0, 18)}, {}),
        (30, {"upper_arm.R": (0, -58, 12), "forearm.R": (0, -72, 0), "hand.R": (0, 0, -18)}, {}),
        (40, {"upper_arm.R": (0, -58, 12), "forearm.R": (0, -72, 0), "hand.R": (0, 0, 12)}, {}),
        (48, {"upper_arm.R": (0, 0, 0), "forearm.R": (0, 0, 0), "hand.R": (0, 0, 0)}, {}),
    ],
)

reset_pose()
armature.animation_data.action = idle
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 40
bpy.context.scene.frame_set(1)

model.hide_viewport = False
model.hide_render = False
rig_collection.hide_viewport = False
rig_collection.hide_render = False
armature.hide_set(False)
armature.hide_viewport = False

bpy.ops.object.select_all(action="DESELECT")
armature.select_set(True)
for obj in model.objects:
    if obj.type == "MESH":
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
bpy.context.view_layer.objects.active = armature

EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
result = bpy.ops.export_scene.gltf(
    filepath=str(EXPORT_PATH),
    export_format="GLB",
    use_selection=True,
    export_yup=True,
    export_apply=False,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_anim_single_armature=True,
    export_force_sampling=True,
    export_optimize_animation_size=True,
    export_optimize_animation_keep_anim_armature=True,
    export_skins=True,
    export_morph=False,
    export_cameras=False,
    export_lights=False,
    export_extras=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
)
if "FINISHED" not in result:
    raise RuntimeError(f"glTF export failed: {result}")

for collection_name in ("REFERENCES", "BLOCKOUT"):
    collection = bpy.data.collections.get(collection_name)
    if collection is not None:
        collection.hide_viewport = True
        collection.hide_render = True
# Keep the armature evaluable because the rigid proxy pieces are bone-parented
# to it. The review script hides only the bone overlay, not the parent object.
rig_collection.hide_viewport = False
rig_collection.hide_render = True
armature.hide_set(False)
armature.hide_viewport = False
model.hide_viewport = False
bpy.ops.object.select_all(action="DESELECT")

bpy.context.scene["cbanimal_character_stage"] = "rigged_model_proxy_exported"
bpy.context.scene["cbanimal_proxy_actions"] = ",".join(action.name for action in (idle, walking, sitting, wave))
bpy.context.scene["cbanimal_proxy_glb"] = str(EXPORT_PATH)
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)

print(
    "CBANIMAL_PROXY_EXPORT_RESULT",
    {
        "glb": str(EXPORT_PATH),
        "bytes": EXPORT_PATH.stat().st_size,
        "objects_bound": len(bone_map),
        "bones": len(armature.data.bones),
        "actions": [idle.name, walking.name, sitting.name, wave.name],
        "export_result": sorted(result),
    },
)
