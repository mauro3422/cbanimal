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
- Front and side are visible in the saved working scene; back and three-quarter are retained hidden for review.
- Blender local bridge was verified on `127.0.0.1:9877` using Blender 5.1.2.
- Orthographic front and side viewport captures exist.
- Front viewport was visually reviewed: full body, readable silhouette, and visible feet.

Important limitation:

- The repository source views are lightweight transfer proxies derived from the approved ChatGPT images. They are suitable for reference alignment and low-poly blockout.
- Replace them with high-resolution approved views before detailed retopology, UV work, texture painting, or final presentation renders.

## Next milestone

Create the first low-poly blockout in the existing Blender file:

1. Preserve the `REFERENCES` collection.
2. Create a separate `BLOCKOUT` collection.
3. Block head, torso, pelvis, limbs, ears, muzzle, paws, and tail with simple mirrored primitives.
4. Keep a humanoid rig-compatible relaxed A-pose.
5. Target the silhouette first; do not model fur strands or small circuitry details.
6. Capture front, side, and three-quarter blockout screenshots for review.
7. Only after approval, continue to topology cleanup, shared rig, weights, animations, and GLB export.

Update this file whenever the milestone or verified state changes.
