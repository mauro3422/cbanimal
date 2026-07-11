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

Review and runtime assets:

```text
assets/concepts/chatgpt-fox/blender/
├── chatgpt_fox_references.blend
├── chatgpt_fox_blockout.json
├── chatgpt_fox_model_proxy.json
├── model_front.png
├── model_side.png
├── model_three_quarter.png
├── rig_guide_front.png
├── model_review_contact.jpg
├── game_smoke_proxy.png
└── scripts/
    ├── create_blockout.py
    ├── prepare_model_proxy_and_rig_guide.py
    ├── rig_proxy_and_export_glb.py
    ├── render_model_review.py
    └── set_model_review_view.py

client/public/models/
└── chatgpt-fox-proxy-v1.glb
```

Important limitations:

- The visible proxy uses separate rigid pieces instead of a unified deforming mesh.
- It has 1,084 triangles, well below the intended 8,000–12,000 triangle production target.
- Its animations are pipeline-validation clips, not polished final animation.
- High-resolution approved references are still required before production topology, UVs, skin weights, textures, or close-up presentation work.

## Next milestone

1. Review the articulated proxy in Blender and in the game for overall proportions, readability, scale, facing direction, and movement feel.
2. Replace the lightweight reference proxies with high-resolution approved views.
3. Build unified production topology targeting approximately 8,000–12,000 triangles.
4. Create real deformation weights, UVs, and the first 1024×1024 texture.
5. Refine the shared humanoid rig, tail controls, animation clips, and final versioned GLB.

Update this file whenever the milestone or verified state changes.
