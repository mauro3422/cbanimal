# CBAnimal Project State

Last updated: 2026-07-11

## Stable baseline

- `master` contains the stabilized local prototype.
- Movement by WASD and click-to-move works.
- Collision handling and blocked-target cancellation work.
- Interaction prompts and the `E` interaction path work.
- Chat, HUD, emotes, settings, toast notifications, and chat bubbles work.
- Blocking UI correctly disables player and interaction input.
- Lifecycle cleanup and Vite HMR disposal are implemented.
- The build and browser smoke test passed.
- No multiplayer synchronization exists yet.

## Tooling completed

- Bridge MCP can control Blender 5.1.2 interactively and in batch mode.
- Image assets can be saved individually or atomically in batches.
- Four character views can be normalized and aligned for Blender.
- Character reference scenes can be created with resumable loop manifests.
- Arbitrary binary files support validated direct writes and resumable chunked transfer.
- The project-specific `character-concept-blender` workflow guide is installed.
- The guide now covers the full resumable path from character brief and turnaround references through Blender blockout/model proxy, rig validation, named animations, GLB structural checks, Three.js integration, browser rendering proof, cleanup, and Git review.
- Bridge MCP `blender_review_bundle` can capture multiple orthographic views in one call and return a contact sheet plus structured geometry, materials, visibility, rig, action, warning, hash, and scene-restoration context.

## ChatGPT fox concept loop

The first concept-to-Blender loop is complete through `ready_for_blockout`.

Verified assets live under:

```text
assets/concepts/chatgpt-fox/
├── character-brief.json
├── source/
│   ├── chatgpt_fox_front.jpg
│   ├── chatgpt_fox_side.jpg
│   ├── chatgpt_fox_back.jpg
│   ├── chatgpt_fox_three_quarter.jpg
│   └── generation-manifest.json
├── prepared/
│   ├── chatgpt_fox_front.jpg
│   ├── chatgpt_fox_side.jpg
│   ├── chatgpt_fox_back.jpg
│   ├── chatgpt_fox_three-quarter.jpg
│   └── prepared-manifest.json
└── blender/
    ├── chatgpt_fox_references.blend
    ├── chatgpt_fox_references.loop.json
    ├── viewport.png
    ├── viewport_front.png
    └── viewport_side.png
```

Verified state:

- Four separate source views and a generation manifest exist.
- The prepared set is 768×960 with common baseline and scale.
- Cross-view subject-height spread is 0.0625 and has no blocking cross-view warning.
- Back and three-quarter source proxies touch the top source edge, but ears remain visible; acceptable for blockout only.
- Blender scene contains `REF_FRONT`, `REF_SIDE`, `REF_BACK`, and `REF_THREE_QUARTER`.
- All four reference objects remain preserved but are hidden in the saved working scene; the articulated `MODEL_PROXY` is visible by default.
- Blender local bridge was verified on `127.0.0.1:9877` using Blender 5.1.2.
- Orthographic front and side viewport captures exist.
- Front viewport was visually reviewed: full body, readable silhouette, and visible feet.

Important limitation:

- The repository source views are lightweight transfer proxies derived from the approved ChatGPT images. They are suitable for reference alignment and low-poly blockout.
- Replace them with high-resolution approved views before detailed retopology, UV work, texture painting, or final presentation renders.

## Articulated model-proxy checkpoint

The initial blockout has been promoted to a functional articulated proxy and integrated into the browser game. It remains a validation asset rather than final production topology.

Verified Blender state:

- `REFERENCES` remains preserved with four image objects and is hidden by default.
- `BLOCKOUT` remains preserved with 37 mesh objects, 616 vertices, and 1,084 triangles, hidden by default.
- `MODEL_PROXY` contains 37 visible `MDL_*` mesh objects using the four established materials.
- `FOX_RIG_GUIDE` contains 24 bones covering root, torso, head, ears, mirrored limbs, feet, and four tail segments.
- All 37 proxy pieces are rigidly parented to appropriate bones; this proves articulation but is not final skin weighting.
- Actions named `idle`, `walking`, `sitting`, and `wave` exist.
- Direct Blender evaluation confirmed that `walking` moves both a hand and the tail tip between keyed frames.
- The saved `.blend` opens with the model proxy visible, references and blockout hidden, no selected objects, no orange origin points, and a three-quarter model-review view.
- Clean front, side, three-quarter, and rig-guide renders exist at 700×800.
- The reproducible checkpoint is recorded in `assets/concepts/chatgpt-fox/blender/chatgpt_fox_model_proxy.json`.

Verified game export and integration:

- Blender exported `client/public/models/chatgpt-fox-proxy-v1.glb` as a valid glTF 2.0 binary.
- The GLB is 145,216 bytes and contains 62 nodes, 37 meshes, four materials, one skin, and four named animations.
- `localPlayerConfig` uses the fox proxy by default at scale `0.32`, while preserving `VITE_PLAYER_MODEL_URL` as an override.
- `CharacterModel` still retains its built-in placeholder when an external model fails to load.
- `npm run build` passed after integration.
- Browser smoke testing returned HTTP 200 for the page and GLB, with content type `model/gltf-binary`.
- The headless browser screenshot contained 24,702 teal/cyan center pixels and zero placeholder-pink pixels, confirming that the fox proxy—not the old placeholder—was rendered.

## Refined proxy v2 checkpoint

The v1 articulated proxy remains committed as a rollback baseline. A separate evidence-driven v2 blend and GLB are now the default validation assets in the browser game.

Verified v2 model state:

- `chatgpt_fox_proxy_v2.blend` preserves the same 24-bone humanoid/tail rig and the hidden reference collections while rebuilding the visible proxy as 44 rigid bone-parented pieces.
- The visible proxy contains 814 vertices, 1,274 polygons, and 1,452 triangles across 44 mesh objects and four materials.
- Geometry review reports no n-gons, missing materials, non-unit scales, negative scales, or warnings.
- The silhouette pass narrows the relaxed A-pose, lowers and side-sweeps the tail, enlarges the paws, and adds layered cheeks, muzzle, nose, inner ears, dark eyes, and cyan pupils.
- Front/side silhouette comparison reduced combined normalized width error from `0.2140` to `0.0881`, a relative reduction of `58.83%`.
- Multi-view review bundles were generated for seven neutral views plus walking frames 1/17, sitting frame 12, and wave frame 20; every bundle confirmed scene restoration and returned no warnings.

Verified v2 animation state:

- Actions remain named `idle`, `walking`, `sitting`, and `wave`.
- Local rig axes were measured before rebuilding the clips: pelvis local Y controls world vertical movement, leg swing uses local X, and the wave pose uses measured upper-arm/forearm rotations.
- `walking` moves both hands, alternating feet, and the tail; full-mesh floor minima stay between `-0.0193` and `-0.0083`.
- `sitting` lowers the pelvis by `0.65`, keeps both paws flat, raises the tail clear of the floor, and reaches a full-mesh minimum of `-0.0071`.
- `wave` raises the right hand to approximately world `z=4.78`, oscillates the wrist, and returns to the rest pose at frame 48.
- The reproducible animation evidence is stored in `proxy-v2-animation-validation.json`.

Verified v2 game export and integration:

- `client/public/models/chatgpt-fox-proxy-v2.glb` is a valid 173,376-byte glTF 2.0 binary containing 69 nodes, 44 meshes, four materials, one skin, and four named animations.
- `localPlayerConfig` now uses `/models/chatgpt-fox-proxy-v2.glb` by default at scale `0.32`; the v1 GLB and environment override remain available for rollback.
- `npm run build` passes after the v2 switch.
- Vite preview smoke returned HTTP 200 for both page and v2 GLB, with `model/gltf-binary` and the exact 173,376-byte file length.
- The 1280×720 headless Chrome screenshot contains 23,365 teal pixels, 1,365 cyan pixels, and zero placeholder-pink pixels in the central analysis region.
- The complete checkpoint is recorded in `chatgpt_fox_proxy_v2.json`; compact comparison and pose sheets live in `proxy-v2-review/`.

Review and runtime assets:

```text
assets/concepts/chatgpt-fox/blender/
├── chatgpt_fox_references.blend              # committed v1 rollback source
├── chatgpt_fox_proxy_v2.blend                 # active refined proxy
├── chatgpt_fox_model_proxy.json               # v1 checkpoint
├── chatgpt_fox_proxy_v2.json                  # v2 checkpoint and hashes
├── proxy-v2-animation-validation.json
├── proxy-v2-game-smoke.json
├── game_smoke_proxy_v2.png
├── proxy-v2-review/
│   ├── baseline-v1-contact.jpg
│   ├── model-v2-contact.jpg
│   ├── walk-frame-1-contact.jpg
│   ├── walk-frame-17-contact.jpg
│   ├── sit-frame-12-contact.jpg
│   ├── wave-frame-20-contact.jpg
│   ├── baseline-v1-metrics.json
│   └── model-v2-metrics.json
└── scripts/
    ├── build_proxy_v2.py
    ├── analyze_reference_metrics.py
    ├── refine_proxy_v2_animations.py
    ├── export_proxy_v2_glb.py
    ├── finalize_proxy_v2_checkpoint.py
    ├── record_proxy_v2_game_smoke.py
    └── verify_proxy_v2_checkpoint.py

client/public/models/
├── chatgpt-fox-proxy-v1.glb
└── chatgpt-fox-proxy-v2.glb
```

Important limitations:

- The active v2 proxy still uses 44 separate rigid pieces instead of one deforming production mesh.
- It has 1,452 triangles, intentionally far below the intended 8,000–12,000 triangle production target.
- The four animations are validated gameplay/pipeline clips, not polished final character animation.
- High-resolution approved references are still required before production topology, UVs, skin weights, textures, or close-up presentation work.

## Next milestone

1. Replace the lightweight reference proxies with high-resolution approved views.
2. Build unified production topology targeting approximately 8,000–12,000 triangles while preserving the validated v2 silhouette.
3. Create real deformation weights, UVs, and the first 1024×1024 texture.
4. Refine humanoid controls, tail controls, and animation clips on the deforming mesh.
5. Export a production-candidate versioned GLB and rerun structural, browser, movement, and performance smoke tests.

Update this file whenever the milestone or verified state changes.
