# CBAnimal Project State

Last updated: 2026-07-10

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
- The project-specific `character-concept-blender` workflow guide is installed.

## Current character experiment

A teal/cyan anthropomorphic fox mascot concept was generated with separate front, side, back, and three-quarter views. The images still need to be persisted into this repository, normalized, loaded into Blender, and visually reviewed.

## Next milestone

Complete the first end-to-end character loop:

1. Persist the four approved fox views.
2. Create the generation manifest.
3. Normalize the reference set.
4. Open the references in Blender.
5. Capture and inspect the viewport.
6. Begin a low-poly blockout only after alignment is accepted.

Update this file whenever the milestone or verified state changes.
