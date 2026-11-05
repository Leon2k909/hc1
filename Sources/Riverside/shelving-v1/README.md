# Lucky Stop stocked shelving v1 — installed 2026-11-04

Isolated branch `codex/riverside-shelving-v1`, worktree `C:/sbox-projects/hc1/shelving-review`. User approved replacement and old-model deletion. The public store imports all four shelves; the saved scene and original physics remain unchanged.

Four shelf boxes previously showed the same luminous window/shop atlas on six flat panels each. This candidate replaces the boxes with two-sided steel gondolas, four shelf levels, adjustable shelf supports, feet, price strips and individually modeled cans/cartons. Packaging and prices use generic printed designs with no outside branding. All eleven materials are non-emissive. No lights are added or changed.

- LODs per unit: 19,300 / 12,300 / 5,180 triangles; switches 0 / 10 / 25.
- Positions: `765,-140,20`, `875,-140,20`, `765,-270,20`, `875,-270,20`; engine yaw 90 degrees.
- Model's local length/depth/height: 70/36/56 inches, matching each original shelf's footprint after rotation. Original wood-box colliders remain in the unchanged store physics section; new renderers add no collider.
- Source removal: exactly 96 old triangles from the active store input, preserving all other geometry and LOD groups, including installed counter, register, ice cabinet and drinks fridge.

## Reproduce

Run `rtk proxy python Sources/Riverside/shelving-v1/build.py` in this worktree. It writes only private candidate resources and review copies, with source/file hashes in `output/riverside/shelving-v1/manifest.json`. `setup.py` prepares native scripts from the established register workflow; `native.py` attaches to the canonical checkout's existing editor and places C# scripts in the session exchange directory.

Import with `native.py script Sources/Riverside/shelving-v1/import.cs.txt`. The import checks current source hashes and permits only the unique `shelving-v1` resource directories. `isolated-review.cs.txt` renders the native asset/control in temporary SceneWorlds, then deletes them.

`capture.py` requires a clean stopped editor and briefly starts offline Riverside play. `runtime-review.cs.txt` swaps only the runtime store renderer and four temporary shelf renderers, copies the actual gameplay camera effects, captures before/after, then restores components. The wrapper restores scene and play state without saving scene edits. Camera settings and lights are identical; gameplay auto-exposure remains active. Output captures are not color/exposure adjusted.

`check-materials.cs.txt` verifies native materials and zero self-illumination. `verify.py` checks three native LODs/masks, valid finite geometry, unit normals within OBJ precision, nonzero triangle areas, bounds, source/import hashes, exact 96-triangle removal, preservation of other store meshes and physics, and editor restoration. It composes actual native captures into `in-game-comparison.png`.

The counter was installed and its old model deleted in the preceding work. Evidence is in the canonical checkout's `output/riverside/counter-v1/installed.json` and `docs/notes/riverside-counter-v1-20261104.md`. The old counter geometry is absent from all Riverside game OBJ sources; historical review sources outside game Assets remain as evidence.

## Installation and deletion

The installed public model was verified in actual play without renderer substitution or extra lights (`installed-runtime.json`, `in-game-installed.png`, `installed-state-restored.json`). Four unit meshes are combined per LOD, sharing eleven material batches; masks are 1/14/112 across the existing seven store LOD groups. Exactly 96 old box/panel faces were removed from each of five store source variants. The standalone old shelving asset, OBJ/MTL and sidecars were deleted through the editor. No old shelf faces remain in Riverside game OBJ sources. Existing shared materials remain for other shop windows. `Tools/riverside_shelving.py` reproduces every approved local mesh and replaces the old authoring calls while preserving all four collisions. Original review scripts/hash guards describe the pre-install baseline and may reference the now-deleted control asset.
