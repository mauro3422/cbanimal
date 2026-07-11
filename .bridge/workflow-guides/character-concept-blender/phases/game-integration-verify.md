# Phase — Game integration and end-to-end verification

## Integration contract

Place the versioned GLB under the client public asset directory and configure the local player through the existing model-loading abstraction. Preserve two fallbacks:

- an environment-variable URL override for alternate models;
- the built-in placeholder when the GLB fails to load.

Do not hardwire the model directly into scene construction when a repository-level model configuration already exists.

## Scale and orientation

Set runtime scale, Y rotation, and vertical offset through configuration. Validate these in the actual game because Blender dimensions alone do not prove appropriate player scale or facing direction.

## Static verification

Run the repository's normal typecheck and production build. Confirm:

- the model URL is valid from the built or development client;
- no TypeScript error was introduced;
- the existing movement, collision, interactions, HUD, and lifecycle code remain unchanged unless modification is required;
- chunk-size warnings are reported separately from build failures.

## Runtime smoke test

Start a temporary local server on a known or discovered free port. Verify:

- the page returns HTTP 200;
- the GLB returns HTTP 200;
- content type is `model/gltf-binary` or another accepted glTF binary type;
- the returned model byte count matches the exported file.

Then launch a headless browser with WebGL software fallback when necessary and capture the actual game viewport after enough virtual time for model loading.

## Proving that the real model rendered

A successful network request is not enough. Distinguish the exported character from the placeholder through one or more of:

- browser console and loader diagnostics;
- a deterministic screenshot check for model-specific palette or silhouette;
- absence of the known placeholder color;
- Three.js scene inspection when browser automation exposes it.

Record the evidence and its limitations. Pixel analysis is a smoke check, not a substitute for visual review.

## Cleanup

Stop temporary development servers and remove disposable logs or analysis scripts. Keep only useful review captures, reproducible pipeline scripts, versioned runtime assets, and state manifests.

## Project state update

Update `.bridge/PROJECT_STATE.md` with:

- current artifact class;
- Blender scene state;
- mesh, rig, skin, and animation counts;
- GLB path, size, and validation result;
- build and browser smoke results;
- explicit limitations;
- the next production milestone.

Do not commit automatically unless the user asked for a commit.

## Exit condition

The pipeline checkpoint is complete only when the client builds, the server delivers the model, a browser renders the exported character instead of the placeholder, temporary processes are stopped, the project state is updated, and Git status is reviewed.
