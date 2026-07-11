# Phase — Blockout and model proxy

## Entry condition

Start only when the four references exist, the prepared manifest has no blocking warning, the Blender scene opens through the local bridge, and `REFERENCES` contains the named front, side, back, and three-quarter objects.

## Safety and reversibility

- Never destroy or overwrite the approved reference collection.
- Create `BLOCKOUT` as a separate collection.
- Before promotion, preserve the original blockout hidden and duplicate it into `MODEL_PROXY`.
- Keep every milestone reproducible with a Python script and a JSON checkpoint.
- Do not claim the model is visible merely because mesh objects exist. Inspect the saved viewport state and produce a render.

## Blockout requirements

Create simple mirrored geometry for:

- pelvis, torso, neck, head, muzzle, and chest patch;
- ears and ear tips;
- eyes;
- shoulders, upper arms, elbows, forearms, and hands;
- hips, thighs, knees, shins, and feet;
- segmented tail.

Use a relaxed humanoid A-pose. Evaluate silhouette, head-to-body ratio, torso width and depth, limb length, paw size, muzzle projection, ear angle, and tail volume before adding detail.

## Blender visibility rules

Reference image empties can obscure the model even when the model exists. For model review:

- hide all reference images;
- hide the original `BLOCKOUT` collection;
- show `MODEL_PROXY`;
- deselect all objects;
- disable object origins, relationship lines, and selected outlines;
- use material preview or a real Blender render;
- keep the armature evaluable when meshes are parented to bones, but hide only the bone overlay when a clean model view is required.

Never hide an armature collection if doing so also hides child meshes. Prefer hiding the armature object's visual representation or disabling the bone overlay.

## Review artifacts

Produce independent front, side, and three-quarter renders. Use Blender rendering rather than relying solely on a viewport screenshot because the bridge framebuffer may be stale or repeat an earlier view.

A model-proxy checkpoint should record:

- collection names;
- object, vertex, and triangle counts;
- materials;
- saved visibility state;
- render paths and dimensions;
- `.blend` hash;
- current stage and known limitations.

## Exit condition

This phase is complete when `MODEL_PROXY` is visible by default, references and original blockout are preserved but hidden, no orange origins obscure the view, three independent review renders exist, and the checkpoint confirms the actual Blender scene state.
