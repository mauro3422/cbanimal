# Character Concept → Blender Skill

## Purpose

Create consistent game-character concept views, persist them safely, normalize them for 3D reference, mount them in Blender, and keep the workflow resumable.

This skill coordinates two kinds of tools:

- Chat image generation: creates or edits the visual concept.
- Bridge tools: save, validate, normalize, version, open, and inspect assets on MauroPrime.

The bridge does not generate the image itself. The chat generates it, then hands the resulting bytes to `image_asset_save`.

## Default mode

Use **quality mode** unless the user explicitly asks for speed.

### Quality mode

1. Create and approve a canonical front view.
2. Use the canonical front image plus the locked character brief as reference for the side view.
3. Repeat for the back view.
4. Repeat for the three-quarter view.
5. Regenerate only the failed view when quality control finds drift.

### Fast mode

1. Create and approve a canonical front view.
2. Generate side, back, and three-quarter views in one batch using the same canonical reference and locked brief.
3. Review all outputs before saving.

Batch generation is faster, but quality mode usually preserves proportions, markings, face, hands, feet, and tail placement more reliably.

## State machine

The loop must always finish a state by writing or updating a manifest.

```text
brief_locked
  -> canonical_front_generated
  -> views_generated
  -> views_saved
  -> views_normalized
  -> blender_scene_created
  -> blender_opened_and_verified
  -> viewport_reviewed
  -> ready_for_blockout
```

If a step fails, report the last completed state and the exact file or operation required to resume. Never end the loop with an empty response.

## Phase 1 — Lock the character brief

Create `character-brief.json` from the template. Lock these fields before producing the final views:

- species
- body proportions
- head-to-body ratio
- palette
- eye shape and color
- ear shape
- muzzle shape
- hands and feet
- tail count, size, and resting side
- markings and their exact locations
- clothing/accessories
- material style
- target game triangle budget
- rig family

Anything not locked may drift between views.

## Phase 2 — Generate images

Each final image must contain exactly one view:

- `front`
- `side`
- `back`
- `three-quarter`

Requirements:

- full body, head to feet visible
- neutral standing pose
- arms relaxed and separated from torso
- legs separated enough to read the silhouette
- clean white background
- camera at the same approximate height and focal style
- no labels, borders, props, shadows that hide the feet, or extra subjects
- same character identity and proportions in every image
- same tail count and tail base position
- same markings, colors, eyes, paws, muzzle, ears, and chest shape

For a riggable humanoid, prefer a relaxed A-pose over a strict straight-arm pose when the generator can preserve it consistently.

## Phase 3 — Visual quality control

Review each view against the canonical front and the brief.

### Identity checks

- same number and shape of ears
- same eye color and eye spacing
- same muzzle length
- same head/body proportion
- same shoulder, hip, hand, and foot proportions
- same tail count, length, volume, and tip color
- same chest and face markings
- same circuitry, tattoos, stripes, or symbols

### Modeling checks

- silhouette is readable
- limbs do not merge into torso
- hands and feet are not malformed
- no hidden second tail or extra limb
- front and side imply compatible torso depth
- back view shows shoulder blades, spine area, tail base, and leg spacing
- side view is a true profile, not a three-quarter angle
- feet are on a common baseline

Regenerate only the failing view, using the canonical front and the best matching existing view as references.

## Phase 4 — Save assets

Call `image_asset_save` with one item or a batch.

Always include:

- `outputPath`
- `role`
- `prompt`
- `source`
- useful metadata such as generation id, reference image id, character name, and mode

For a turnaround batch, also provide:

- `collectionName`
- `manifestPath`

Recommended layout:

```text
assets/concepts/<character-slug>/
  source/
    <slug>_front.png
    <slug>_side.png
    <slug>_back.png
    <slug>_three-quarter.png
    generation-manifest.json
  prepared/
    <slug>_front.jpg
    <slug>_side.jpg
    <slug>_back.jpg
    <slug>_three-quarter.jpg
    prepared-manifest.json
  blender/
    <slug>_references.blend
    <slug>_references.loop.json
    viewport.png
  character-brief.json
```

## Phase 5 — Normalize views

Call `image_character_views_prepare` after saving the source images.

The preparation stage:

- detects the mostly white background
- finds the subject bounds
- adds safe crop margin
- scales all views to the same canvas
- aligns feet to a common baseline
- exports lightweight Blender reference images
- computes hashes, dimensions, subject ratios, and warnings
- creates a resumable manifest

Do not silently ignore warnings. Regenerate a source view when the subject is clipped, too small, or inconsistent in scale.

## Phase 6 — Blender setup

Call `blender_setup_character_references` with the prepared views.

Expected result:

- a saved `.blend`
- named reference objects
- front and side visible by default
- back and three-quarter retained as hidden review references
- a `.loop.json` checkpoint
- Blender opened on a free local port
- bridge connection verified before returning

Then capture a viewport image and inspect alignment before beginning geometry.

## Phase 7 — Iteration loop

```text
Generate or edit one view
  -> save source
  -> normalize all four views
  -> rebuild/update Blender references
  -> capture viewport
  -> inspect
  -> regenerate only the inconsistent view
```

Preserve approved images. Never overwrite them without `overwrite: true` and an explicit reason in metadata.

## Prompt structure

Every view prompt should contain four sections:

1. **Identity lock** — immutable character traits from the brief.
2. **View instruction** — front, true side, back, or three-quarter.
3. **Modeling constraints** — neutral pose, separated limbs, full body, white background.
4. **Negative constraints** — no extra limbs, no alternate outfit, no text, no props, no crop, no perspective distortion.

Use the prompt templates in `prompts/`.

## Completion rule

A concept loop is complete only when all are true:

- four source images exist
- generation manifest exists
- four prepared images exist
- prepared manifest has no blocking warning
- Blender reference scene exists
- Blender connection was verified
- viewport screenshot exists and was reviewed

Otherwise report the current state and continue from the next unfinished phase.


## Extended pipeline — Blender to browser game

The original concept loop ends at `ready_for_blockout`. For CBAnimal, continue with the following resumable states:

```text
ready_for_blockout
  -> blockout_created
  -> blockout_reviewed
  -> model_proxy_created
  -> rig_guide_created
  -> validation_actions_created
  -> rigged_proxy_exported
  -> glb_structurally_verified
  -> game_config_integrated
  -> client_build_passed
  -> browser_model_smoke_passed
  -> ready_for_production_topology
```

Load the dedicated phase document that matches the current state:

- `blockout-model-proxy`
- `rig-animation-export`
- `game-integration-verify`

### Artifact classes

Use these names precisely:

- **Reference scene:** image planes or empties only.
- **Blockout:** cheap geometry for silhouette and proportion decisions.
- **Model proxy:** duplicated and reviewable geometry prepared for pipeline testing.
- **Rigged proxy:** articulated validation asset, possibly made from rigid pieces.
- **Production model:** unified or intentionally segmented topology with real deformation weights, UVs, textures, tested rigging, and polished animations.

Never call a blockout or rigid proxy a finished model.

### Mandatory Blender review rule

A scene containing meshes does not prove the user can see the model. Before reporting success:

1. Inspect collection and object visibility.
2. Hide reference images that cover geometry.
3. Deselect objects and disable object-origin overlays.
4. Keep an armature evaluable when child meshes depend on it.
5. Produce real front, side, and three-quarter renders.
6. Confirm the renders differ and record their hashes or dimensions.

### Mandatory export rule

A Blender export operator returning `FINISHED` does not prove a usable GLB. Parse the GLB and verify its header, declared length, mesh count, skin count, and exact animation names.

### Mandatory runtime rule

A successful HTTP request does not prove Three.js rendered the exported character. Build the client, serve it, load it in a browser, and distinguish the real model from the placeholder through runtime diagnostics or deterministic screenshot evidence.

### Resume rule

At the end of every stage, update both:

- a machine-readable JSON checkpoint inside the character's Blender asset directory;
- `.bridge/PROJECT_STATE.md` with the verified stage, limitations, and next milestone.

Preserve the reference collection, original blockout, scripts, exported asset, and verification evidence. Stop temporary servers and do not create a Git commit unless requested.

## Full completion rule

The end-to-end proxy pipeline is complete only when:

- the original four references remain preserved;
- a visible blockout or model proxy exists;
- clean independent Blender renders exist;
- an armature and expected actions exist;
- actual frame evaluation proves movement;
- the exported GLB parses as glTF 2.0 and contains the expected skin and clips;
- the client build passes;
- the GLB is served successfully;
- a browser renders the exported character instead of the fallback placeholder;
- temporary processes are stopped;
- project state and Git status are reviewed.

Production art remains a separate milestone requiring high-resolution references, final topology, deformation weights, UVs, textures, and animation polish.
