# Riverside glazed pole insulator v2 — installed

Installed on user approval on 2026-11-04: **48 crossarm insulators**, comprising 36 wired pins with ties and 12 unused pins with the same body and no tie. The native editor saved the `Pole Insulators` group in Riverside. Removed precisely 768 old cylinder faces from the published dressing mesh; all other OBJ lines, the complete dressing ModelDoc/physics, existing lights, poles/crossarms, wire endpoints and transformer bushings were preserved.

The original is a six-sided 1.4-inch-radius cylinder, five inches high, with a top cap and open underside (16 triangles), using the shared `rs_glass` material. The new model has three rain-shedding porcelain skirts, a glazed neck/crown, zinc mounting pin/washer/hex nut and a metal wire tie. Brown glaze, restrained film and zinc textures are procedural; no external assets or ImageGen. Shading normals blend around the circumference and across porcelain profile transitions; metal fittings retain crisp edges.

Model: `models/props/riverside/pole_insulator_v2/pole_insulator.vmdl`. Three LODs: **3,156 / 1,568 / 652 triangles**, switches at 18 and 45. `pole_insulator_bare.vmdl` omits the tie, with **1,512 / 720 / 288 triangles**. Both share one 1k colour/normal/roughness/metalness atlas and material. These are authored budgets, not measured frame times. Tied bounds are `-1.66,-1.66,0` to `1.66,1.66,5.458` inches. The skirts extend slightly beyond the original radius, and the tie extends above its crown.

Origin is the original insulator's base. The ceramic crown is Z=4.65, supporting the existing 0.35-inch-radius wire at its unchanged Z=5 centre. The tie loops around the neck and over that wire. Canonical +X follows the first connected span. All 48 placements were audited against actual wire endpoints; 12 spare lower-crossarm pins have no span. Detail position: engine `1007.511912,330.726253,418.3`; contact centre `1007.511912,330.726253,423.3`.

## Original review recipe

Prefix shell commands with `rtk`. Pass the project root to the Python scripts.

1. `build.py` creates only private model/material assets.
2. `prepare_review.py` locates the exact 16 published faces and hides only those in a separate render-only dressing copy. Actual crossarm/wire and all approved transformer/searchlight geometry are retained. Public dressing OBJ/ModelDoc and saved-scene hashes are recorded.
3. `native.py script Sources/Riverside/pole-insulator-v2/review.cs.txt` compiles/loads both models and captures matched whole, wire-tie detail and context views with identical cameras, locked exposure and temporary inspection light. The scene is destroyed in `finally`, preserving the active editor/play state. The saved installed streetlight is also rendered without inserting replacement heads. `refresh-new.cs.txt` repeats only the new views after the porcelain shading refinement.
4. `verify.py` checks all three meshes for finite/nondegenerate triangles, outward winding relative to shading normals, bounded nondegenerate UVs, unit tangent-normal vectors and protected production hashes. Passed.
5. `compose.py` arranges native screenshots without colour/exposure edits.

These comparison scripts and their protected hashes describe the pre-installation review. Do not rerun them against the installed map.

## Installation and verification

`build-bare.py` creates the untied LODs from the same body recipe. `prepare_install.py` evaluates only dressing in memory, records the real wire graph and stages the narrow 48 × 16-face cut, with original backups/hashes under `output/asset-improvement-20261030/riverside-pole-insulator/installed/`. `install.cs.txt` applies the guarded cut and deserializes the deterministic group through the native editor. Native `save_scene` and `asset_compile` succeeded.

`verify-install.py .` passed saved group counts, models, positions, rotations, contact heights, exact unrelated mesh-line preservation, unchanged complete ModelDoc/physics and unchanged lights. `verify.py . --mesh-only` passed geometry, UVs and normal-map checks for all six meshes. `capture-installed.cs.txt` rendered the saved group, actual dressing/wires, a wired pin, an untied spare and a complete crossarm assembly in a disposable scene with temporary inspection light. Native models load without errors; final editor is clean, out of play, with zero compile errors. No gameplay or LOD-transition playtest.

Retained generation: `Tools/riverside_parts.py` records `PIN_INSULATORS` and resolves heading on the first matching `wire` endpoint; `Tools/riverside_map.py` emits the tied/bare model group. Shared `rs_glass` remains for other uses. Do not regenerate the whole map to apply this change.
