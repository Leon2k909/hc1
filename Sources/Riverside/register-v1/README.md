# Lucky Stop cash register v1 — installed 2026-11-04

Branch `codex/riverside-register-v1`, isolated worktree `C:/sbox-projects/hc1/register-review`. User approved installation. The public store ModelDoc now imports the register, preserving the ice cabinet and drinks fridge. The saved scene and complete physics section remain unchanged.

The original register was a plain 12-triangle dark box at engine position `935,-120,66`, 16×12×12 inches, with no collider. The new register's origin is at its base: `935,-120,60`. It includes a sloped 24-key deck with individual legends, green total display, receipt printer and curled thermal paper, cash drawer, key lock, feet and side vent details. The printed receipt totals match the displayed 12.50. All markings are generic; no outside brand names or logos.

Three native LODs: 2,720 / 2,328 / 1,716 triangles, thresholds 0 / 10 / 25. No collision is added. Painted housing has color/normal/roughness textures; the display uses restrained self-illumination.

## Reproduce and verify

1. Run `rtk proxy python Sources/Riverside/register-v1/build.py` in this worktree. It finds and removes exactly 12 original register triangles from a private review copy of the active store mesh. It preserves the installed ice cabinet, drinks fridge and complete original physics section.
2. `setup.py` prepares native import and isolated review scripts using the existing ice-cabinet workflow.
3. `native.py script Sources/Riverside/register-v1/import.cs.txt` imports only the unique candidate assets through the running editor, guarded by source hashes.
4. `native.py script Sources/Riverside/register-v1/isolated-review.cs.txt` renders the candidate and original in identical temporary native SceneWorlds, then deletes them.
5. `capture.py` requires a clean stopped editor, temporarily starts offline Riverside play, swaps only runtime renderers for before/after, copies the gameplay camera effects and adds no lights. The script restores the renderer/cameras and editor scene/play state. It never saves scene changes.
6. `verify.py` checks all three meshes, native LOD counts/masks, 12-triangle removal, preservation of other meshes/physics, source/import hashes, error models and editor restoration. It composes actual native play captures without color or exposure adjustment.

Preview resources live under `models/maps/riverside/register-v1` and `materials/riverside/register-v1`. Receipts and native images are in `output/riverside/register-v1`; `in-game-comparison.png` is the review image. The ice cabinet is already installed and is documented separately in the canonical checkout's `docs/notes/riverside-ice-cabinet-v1-20261104.md`.

## Installed verification

`installed-runtime.json` and `in-game-installed.png` verify the public model in offline Riverside play, without runtime substitution or added lights. `installed-state-restored.json` records editor restoration. All three approved local OBJ meshes match `Tools/riverside_register.py` exactly. The authoring hook replaces only the original register box; no full-map regeneration was run. The public store uses the union of existing ice and register switch distances (0/10/20/25/45); its shared meshes remain visible in every group. Original review/build scripts target the pre-install baseline and intentionally guard against applying the replacement twice.
