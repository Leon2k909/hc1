# Riverside sandbags v2 — installed

Built, checked and installed in s&box 26.11.03a on 2026-11-04 after the user approved the comparison. All 54 bags across four barricades are saved in the Riverside scene. Exactly 3,456 original bag triangles were removed from the three live zone meshes. Their collision VMDLs are byte-for-byte unchanged.

The original implementation is `Tools/riverside_parts.py`, `sandbag_wall` and `bag`. Four barricades contain 54 bags, merged into the pad (5), store (27) and dressing (22) models: two at the Lucky Stop, one on the watch deck and one across the north lane. The originals have five rings, eight sides, open ends and a rock-like `rs_sandbag` material.

The new bags are fuller near their ends and have broad compressed contact faces, local folds, a sewn closure, rolled side hems, individual close-view stitches, a two-wrap twine binding, a knot, loose cord ends and a gathered cloth mouth with thickness. Three slightly different shapes share one material. The preview alternates the direction of the tied ends, scales length to the authored bags, and darkens lower courses to suggest dampness.

Models: `models/props/riverside/sandbag_v2/sandbag_{0,1,2}.vmdl`. Each has 2,372 / 744 / 134 triangles at LOD 0–2, switching at 20 and 60 (estimates, not a performance playtest). One 2048 × 2048 atlas supplies colour, tangent normal, roughness and AO. Metalness is zero.

The woven fabric is derived from the project's existing `materials/lowtide/sacks/lt_jute_color.png` (authored by the earlier ImageGen jute pass). The original Lowtide files are untouched. The texture is sampled as a 5.25-inch field at 48 atlas px/in, with new water/mud staining and fibre-only normal relief. A cylindrical UV unwrap maintains the yarn direction around the sides; the near-seam gather compresses the weave. Vertex export uses five decimals because the map kit's usual three can flip very small folded-end triangles.

## Build and verify

1. `python Sources/Riverside/sandbag-v2/build.py <project-root>` creates only the new bag assets.
2. Historical pre-installation step: `prepare_review.py` recorded all 54 authored positions and created three render-only comparison backgrounds, hiding exactly 3,456 old bag triangles only in those new copies. Its manifest is retained; do not rerun it against the installed generator.
3. `python Sources/Riverside/sandbag-v2/native.py script Sources/Riverside/sandbag-v2/review.cs.txt` copies the script into the native session exchange directory and captures old/new walls with the same position, camera and temporary inspection light. It also captures an individual bag to show the tie, with an extra temporary fill light. The isolated scene is destroyed in `finally`; active play and scene state are preserved.
4. Historical pre-installation `verify.py` checked all nine mesh files: finite geometry, nondegenerate triangles, outward winding relative to the smooth normals, valid nondegenerate UVs and normalized normal maps. Its production hash checks describe the original review state. All checks passed.
5. `python Sources/Riverside/sandbag-v2/compose.py <project-root>` arranges the matched native screenshots into `before-after.png`; it crops/resizes them without colour or lighting edits.

Evidence: `output/asset-improvement-20261030/riverside-sandbags/`. Native checks loaded all three models without errors, and the disposable scene contained all 54 replacement instances. Captures cover the north-lane wall, its close detail, a Lucky Stop wall, and a separate tied-end detail bag. No live match or LOD transition playtest has been done.

## Installation

`install.py` cut only the old bag faces, with source snapshots and content guards. `install-editor.cs.txt` compiled the affected zone meshes, placed the new bags in the native editor, and marked the editor scene dirty before `save_scene`. `verify-install.py` checked the saved 54 centres, rotations, scales, tints and models, exact preservation of every unrelated face, and unchanged collision VMDL hashes. It passed.

The canonical generator now records `SANDBAGS` in `Tools/riverside_parts.py` and writes a `Sandbags` scene group through `Tools/riverside_map.py`. Length scales, alternating tied-end direction and damp course tints match the approved preview. Existing simple fabric collision walls are retained. Avoid regenerating the whole Riverside map; shared-kit drift can rewrite unrelated systems.

Installation evidence and backups: `output/asset-improvement-20261030/riverside-sandbags/installed/`. A fresh native capture of the saved bags is also `output/asset-improvement-20261030/riverside-ice-freezer/new_installed_sandbags.png`.

The strict full verification passed immediately after installation. A concurrent pole-transformer installation subsequently added unrelated dressing geometry; its retained source notes explicitly record rebasing around the sandbag cut. The full snapshot comparator therefore cannot be rerun against that later mesh state. `verify-install.py <project-root> --scene-only` checks the current 54 saved placements without rewriting the original installation receipt.

A subsequent approved ice-cabinet installation changed the public store render import to `models/maps/riverside/ice-cabinet-v1/store_without_ice.obj`. That private background carried 1,728 pre-installation store bag faces. `fix-store-import.cs.txt` removed only those duplicate faces through the native editor, backed up the exact source, and compiled the public store. The public ModelDoc/physics and saved scene remained unchanged; line comparison verified all unrelated lines were retained. Receipts are in `installed/store-import-reconciliation/`. Any future private zone import must preserve the installed bag cuts.

The next concurrent register installation used another background with the same old faces. The same guarded repair was applied to `register-v1/store_without_register.obj`, and the public store compiled successfully with `asset_compile full=false`. `check-store-import.cs.txt` checks every imported OBJ, compiled freshness, valid loaded store and 54 saved bag renderers. An unused `rs_sandbag` entry may remain in the compiled material table; imported face counts are the authoritative duplicate-geometry check. The full recursive compile call timed out, but the subsequent model compile and loaded checks completed.


The unused comparison background for this earlier review was archived/deleted during the approved porch-lamp retirement (2026-11-04) because it retained a cached dependency on the old lamp material. See Sources/Riverside/porch-light-v2/README.md and its installed/legacy-cleanup/ backups. Keep historical PNGs; do not rerun the original review script without rebuilding its background from current assets. The approved public model is unaffected.
