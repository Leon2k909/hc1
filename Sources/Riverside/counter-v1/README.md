# Lucky Stop checkout counter v1 — installed 2026-11-04

Isolated branch/worktree: `codex/riverside-counter-v1`, `C:/sbox-projects/hc1/counter-review`. User approved replacement and deletion of the old counter. The public store imports the new counter; the saved scene and physics section are unchanged.

The original was a single 110×30×40-inch block, with a tiled concrete top and a wood side material. This candidate has a laminate worktop with restrained scratches and a cup ring, a separate dark edge band, framed oak front/end panels, a recessed toe kick, four rear storage doors with pulls and hinges, and a tubular steel foot rail. The rail stays within the original collision envelope. Three small decorative edge chips extend only 0.02 inch beyond the original front plane.

- LODs: 5,296 / 3,436 / 1,628 triangles, switch thresholds 0 / 15 / 35.
- Local base origin at `0,0,0`; engine placement `935,-135,20`.
- Top remains exactly at local Z=40 / world Z=60, preserving contact with the installed register.
- Original 110×30×40-inch collision is retained in the store ModelDoc. The standalone counter renderer adds no collision.
- Existing oak color/normal/roughness assets from `materials/gunsmith_range` are reused and checked by hash; they are unchanged. Laminate textures are private 2048×512 assets. No lights or emission are added.

## Reproduce

Run `rtk proxy python Sources/Riverside/counter-v1/build.py` in this worktree. It writes private resources and a review-only copy of the active store input with exactly the old counter's 12 triangles removed. All other geometry, material groups, current ice/register LOD groups and physics are preserved. It does not regenerate Riverside.

`setup.py` prepares the native import and capture scripts from the installed register workflow. `native.py` attaches to the canonical checkout's existing editor; scripts are copied into the native session exchange directory. `import.cs.txt` checks source/file hashes and imports only unique `counter-v1` resources through the editor.

`isolated-review.cs.txt` renders native models in temporary SceneWorlds and deletes them. `capture.py` requires a clean stopped editor, briefly starts offline Riverside play, substitutes only runtime renderers for review, copies the gameplay camera effects and adds no lights. It restores the original renderer/cameras, scene and play state without saving edits. Gameplay review captures use clear aisle and operator-side positions; shelving is retained.

`check-materials.cs.txt` verifies every native material and the compiled laminate texture dimensions/mips. `prepare_verification.py` creates `verify.py`, which checks finite geometry, nonzero triangle areas, indices, normal lengths, native LOD counts/masks, bounds, source/import hashes, external texture hashes, exact removal of 12 triangles, preservation of other store upgrades and physics, and editor restoration. It composes `in-game-comparison.png` directly from native captures without color/exposure adjustments.

Receipts and images: `output/riverside/counter-v1`. The ice cabinet and cash register are already installed; this counter remains a separate review candidate.

The final comparison uses the completed matching aisle pair. A later operator-side recapture was interrupted by an external scene switch after the aisle pair completed; see `capture-audit.json`. The mismatched operator before image is excluded. The editor is now in a separate Belltower play session, which this task leaves untouched. The latest repeatable capture script records only the aisle pair.

## Installed and old version deleted

Actual public-model play verification: `in-game-front-installed.png`, `installed-runtime.json`, `installed-state-restored.json`, `installed.json`. No runtime substitution or added lights. The old standalone counter asset, OBJ/MTL and sidecars were deleted from game Assets through the editor; its 12 old faces were removed from four remaining store source variants. `cleanup-plan.json`/`cleanup.json` record exact targets. Shared store materials remain. The approved geometry is reproduced by `Tools/riverside_counter.py`; the old authoring box was replaced without regenerating the map. An intervening 12-triangle porch-light removal was preserved (`integration-baseline.json`). Historical review/build scripts target the pre-install baseline and may reference the deleted comparison asset; retain them as evidence rather than re-importing the old asset.
