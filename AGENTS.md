# AGENTS.md

Project instructions for coding agents working on CBAnimal.

## Project

CBAnimal is a browser-based Three.js/Vite/TypeScript game prototype that will grow into a social low-poly creature game with species, elemental nations, interactions, chat, emotes, and eventually multiplayer.

The active application lives in `client/`.

## Required context

Before substantial work:

1. Read `.bridge/PROJECT_CONTEXT.md`.
2. Read `.bridge/PROJECT_STATE.md` for current progress and the next milestone.
3. Load the relevant guide under `.bridge/workflow-guides/` when the task matches one.
4. Inspect the current Git status before editing.

## Engineering rules

- Preserve the separation between game core, scenes, entities, systems, UI, state, and styles.
- Keep game input blocked while chat or blocking menus are open.
- Use removable event handlers and implement cleanup for long-lived objects.
- Treat player locomotion and emotes as separate state.
- Do not hardcode nonexistent model URLs; retain the placeholder fallback.
- Avoid unsafe dynamic HTML. User-controlled strings must use `textContent` or equivalent safe rendering.
- Prefer small, typed TypeScript changes over broad rewrites.
- Do not add production dependencies without a clear need.
- Do not modify generated assets destructively without preserving the approved source or manifest.

## Character asset workflow

For character concept, image consistency, Blender references, low-poly preparation, rigging, animation, and GLB export, use:

```text
.bridge/workflow-guides/character-concept-blender/
```

Generated assets belong under:

```text
assets/concepts/<character-slug>/
```

Keep source images, prepared references, Blender files, manifests, and exported game assets separated.

## Validation

From `client/`, run at minimum:

```powershell
npm run build
```

For runtime changes, also start Vite and perform a browser smoke test. Check movement, collisions, UI input blocking, interaction prompts, chat safety, emotes, and cleanup after reload.

## Git

- Work from a clean tree when possible.
- Keep commits focused and descriptive.
- Do not force-push or rewrite `master` history.
- Update `.bridge/PROJECT_STATE.md` after meaningful milestones so future agents can resume accurately.

## Verification rule

Never claim that a build, file, image, Blender scene, server, commit, push, or runtime behavior exists until it has been verified through an appropriate tool or direct test.
