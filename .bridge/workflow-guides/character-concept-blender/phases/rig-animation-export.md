# Phase — Rig, validation animations, and GLB export

## Rig strategy

Use a shared humanoid-compatible armature with additional bones for species-specific anatomy. For an anthropomorphic tailed character, the minimum guide should cover:

- root, pelvis, spine, chest, neck, and head;
- mirrored upper arm, forearm, hand, thigh, shin, and foot chains;
- optional ear bones;
- enough tail segments to preserve the intended curve.

A rigid-piece proxy may parent each mesh object directly to one bone. This is acceptable only for pipeline validation. It is not a substitute for unified production topology and deformation weights.

## Required validation clips

Create small named actions that exercise the runtime contract:

- `idle`;
- `walking`;
- `sitting`;
- `wave`.

The goal is not polished animation. The goal is to prove that the expected clip names exist, the skeleton evaluates, the body moves, and tail or ear bones survive export.

## Blender verification

Before export, verify through `blender_execute_code` or equivalent scene inspection:

- armature object exists;
- expected bone count exists;
- every model-proxy piece has the intended parent or armature relationship;
- all required actions exist by exact normalized name;
- at least one limb and one species-specific part change world position or transform between keyed frames;
- transforms and scale are suitable for export;
- hidden references and review-only helpers are excluded.

Do not infer movement from keyframes alone. Evaluate the scene at two frames and compare actual world transforms.

## GLB export

Export a versioned binary glTF into the game public asset directory. Use selection or collection filtering so only runtime assets are exported.

Recommended checks after export:

- GLB magic is `glTF`;
- version is 2;
- declared byte length matches the file;
- expected scene, nodes, meshes, materials, skins, and animations exist;
- animation names are exactly those consumed by the game;
- the file hash and size are recorded.

Use a small local parser or trusted glTF tooling to inspect the JSON chunk. A successful Blender operator result alone is insufficient.

## Production distinction

Mark the artifact clearly as one of:

- `blockout`;
- `model_proxy`;
- `rigged_proxy`;
- `production_model`.

Never describe a rigid proxy as final skinning. Production completion requires unified topology where appropriate, deformation weights, UVs, textures, deformation testing, and polished clips.

## Exit condition

This phase is complete when the `.blend` contains an evaluable armature and required actions, direct frame comparisons prove movement, the GLB parses as valid glTF 2.0, one skin and the expected animations are present, and the exported path, size, counts, and hash are written to a checkpoint.
