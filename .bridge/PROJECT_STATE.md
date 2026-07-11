# CBAnimal Project State

Last updated: 2026-07-11

## Stable application baseline

- `master` contains the local Three.js/Vite/TypeScript prototype.
- WASD and click-to-move, collision handling, interactions, chat, HUD, emotes, settings, notifications, input blocking, lifecycle cleanup, and HMR disposal are implemented.
- The application remains local-only; multiplayer synchronization is not implemented yet.
- The active application lives under `client/`.

## Tooling

- Bridge MCP controls Blender 5.1.2 in batch and interactive modes.
- `blender_review_bundle` provides multiview contact sheets plus geometry, material, rig, animation, warning, hash, and scene-restoration evidence.
- The project workflow guide is `.bridge/workflow-guides/character-concept-blender/`.

## Approved character sources retained

The approved source and prepared turnaround inputs remain under:

```text
assets/concepts/chatgpt-fox/
├── character-brief.json
├── source/
├── prepared/
└── blender/
    ├── chatgpt_fox_references.blend
    ├── chatgpt_fox_references.loop.json
    ├── viewport.png
    ├── viewport_front.png
    └── viewport_side.png
```

These files are the preserved source/reference basis. Old generated proxy checkpoints are intentionally not retained.

## Canonical fox v5

`chatgpt_fox_proxy_v5.blend` is the only active Blender character checkpoint and `chatgpt-fox-proxy-v5.glb` is the only runtime fox model.

Verified model state:

- Canonical Blender file: `assets/concepts/chatgpt-fox/blender/chatgpt_fox_proxy_v5.blend`.
- Runtime GLB: `client/public/models/chatgpt-fox-proxy-v5.glb`.
- `MODEL_PROXY` contains 47 visible meshes, 994 vertices, 1,404 polygons, and 1,780 triangles.
- The rig is `FOX_RIG_GUIDE` with 24 bones.
- `MDL_V5_BODY` is a continuous deforming shell weighted to pelvis, spine, chest, and neck.
- `MDL_V5_TAIL_ROOT` is weighted between pelvis and `tail.01`.
- Face, ears, paws, hands, segmented tail curve, white tail tip, and teal/cyan/white palette remain preserved.
- The internal `V3_RIGID_BODY_ARCHIVE` and its torso/pelvis/neck objects were purged from the canonical blend.
- Blender opens on `idle`, frame 1, with zero objects selected.

Verified animations:

- Actions: `idle`, `walking`, `sitting`, and `wave`.
- Walking alternates feet, swings hands and tail, and deforms the tail root.
- Sitting deforms the continuous body correctly.
- Wave reaches head height, oscillates, and returns to rest.
- Minimum validated floor position is `-0.0215`, within the accepted tolerance.
- Evidence: `assets/concepts/chatgpt-fox/blender/proxy-v5-animation-validation.json`.

Verified export and browser integration:

- GLB size: 189,924 bytes.
- Structure: 72 nodes, 47 meshes, four materials, one skin, four named animations, one scene.
- `client/src/game/config/localPlayerConfig.ts` uses `/models/chatgpt-fox-proxy-v5.glb` by default at scale `0.32`.
- `VITE_PLAYER_MODEL_URL` and the built-in placeholder fallback remain available.
- Browser smoke returned HTTP 200 for the page and GLB with MIME `model/gltf-binary`.
- The 1280×720 screenshot contains 23,491 teal pixels, 1,474 cyan pixels, and zero placeholder-pink pixels.
- Evidence: `proxy-v5-game-smoke.json`, `game_smoke_proxy_v5.png`, and `proxy-v5-review/`.
- Checkpoint manifest: `chatgpt_fox_proxy_v5.json`.
- Independent verifier: `scripts/verify_proxy_v5_checkpoint.py`.

## Cleanup policy

- Generated fox versions v1, v2, v3, and v4, their GLBs, Blender backups, validation JSON, screenshots, review bundles, and version-specific scripts were deleted on explicit user request.
- Only `master` exists locally and remotely. There are no obsolete branches to delete.
- Git history remains untouched; do not rewrite or force-push `master`.
- The canonical v5 blend, v5 GLB, v5 evidence, and approved source/reference inputs must be preserved.

## Current character asset tree

```text
assets/concepts/chatgpt-fox/blender/
├── chatgpt_fox_proxy_v5.blend
├── chatgpt_fox_proxy_v5.json
├── chatgpt_fox_references.blend
├── chatgpt_fox_references.loop.json
├── game_smoke_proxy_v5.png
├── proxy-v5-animation-validation.json
├── proxy-v5-game-smoke.json
├── proxy-v5-review/
└── scripts/
    ├── export_proxy_v5_glb.py
    ├── finalize_proxy_v5_checkpoint.py
    ├── record_proxy_v5_game_smoke.py
    ├── validate_proxy_v5_animations.py
    └── verify_proxy_v5_checkpoint.py

client/public/models/
└── chatgpt-fox-proxy-v5.glb
```

## Limitations and next milestone

- v5 is a validated hybrid gameplay proxy, not a final unified 8,000–12,000 triangle production mesh.
- Face, limbs, paws, ears, and most tail segments remain separate rigid low-poly pieces.
- UVs, a 1024 texture set, final production weights, richer controls, and presentation-quality deformation remain incomplete.
- The next milestone is production topology and texturing only when normal gameplay review or close-up presentation requires it.

Update this file whenever the verified milestone changes.
