# CBAnimal Project Context

## Product direction

CBAnimal is a social browser game prototype built with Three.js. The intended direction is a stylized low-poly world populated by anthropomorphic creatures. Species, elemental identity, nation, visual customization, chat, emotes, interactions, and multiplayer should remain separate concepts in the architecture.

## Repository layout

```text
C:\dev\cbanimal
└── client/
    ├── src/core/
    ├── src/game/
    │   ├── config/
    │   ├── core/
    │   ├── entities/
    │   ├── input/
    │   ├── scenes/
    │   └── systems/
    └── src/ui/
        ├── core/
        ├── components/
        ├── state/
        └── styles/
```

## Current architectural decisions

- The game is currently local-only; multiple browser sessions are independent.
- `Game` owns the main lifecycle and disposal chain.
- `MainScene` owns scene-generated objects and interaction systems.
- `Player` separates locomotion state from active emotes.
- UI emits a combined blocking state so chat and menus disable game input.
- Dynamic user-facing strings are rendered safely instead of interpolated into HTML.
- The local player model is configured through `localPlayerConfig` and an optional environment model URL.
- The built-in placeholder remains the fallback until a versioned GLB is available.

## Character production policy

Use the project workflow guide:

```text
.bridge/workflow-guides/character-concept-blender/
```

Default to quality mode:

1. Lock a character brief.
2. Generate one canonical front image.
3. Derive side, back, and three-quarter views from the approved front.
4. Regenerate only inconsistent views.
5. Save source images and a generation manifest.
6. Normalize scale and baseline.
7. Create a resumable Blender reference scene.
8. Capture and review the viewport before modeling.

Initial game target:

- humanoid shared rig where practical;
- low-poly readable silhouette;
- approximately 8,000–12,000 triangles for the main character;
- one 1024×1024 texture initially;
- one or two materials;
- root motion disabled because movement is code-driven;
- animation clips named consistently with game states.

## Tool relationship

- ChatGPT image generation creates or edits concept images.
- Bridge MCP persists images, prepares reference sets, controls Blender, validates outputs, and updates the repository.
- Arbitrary binary assets must use `binary_file_write` for small payloads or the resumable `binary_upload_begin` → `binary_upload_append` → `binary_upload_status` → `binary_upload_finish` flow for large payloads. Do not route image/model base64 through `write_text_file`.
- Verify completed transfers with `binary_file_info`, including expected byte count and SHA-256 when known.
- Workflow guides define when and how those tools should be used.
- `AGENTS.md` is also available for Codex and other coding agents, but ChatGPT web should load this project through `project_context_load`.
- A conversation may retain an older cached connector catalog after the Bridge is upgraded. If a runtime tool is missing from the chat catalog, reopen the connector or continue in a new Project chat before inventing a manual transport workaround.

## Stable validation commands

```powershell
cd C:\dev\cbanimal\client
npm ci
npm run build
npm run dev -- --host 0.0.0.0 --port 4173
```

Do not assume the dev server is running. Verify it before reporting a test URL.
