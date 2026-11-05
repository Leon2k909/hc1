# Riverside cobra-head streetlight v2 — installed

Approved and installed on 2026-11-04 after the porch fittings. All four sodium heads are saved in the public Riverside scene, at their original arm anchors. Exactly 56 old head faces were removed from the shared dressing mesh; every unrelated mesh line, the complete ModelDoc/physics and existing point lights were preserved.

The original is a 22 × 10 × 5-inch rectangular housing with a flat bright lens beneath it (14 triangles). The replacement has a shaped casting, hollow slip-fitter collar, mounting bolts, separate lower service rim/gasket, rear hinges, nose latches, domed amber prismatic refractor and photocell. Original procedural aluminium/weathering and refractor maps; no external assets or ImageGen. Opaque frosted lens with a restricted warm emission mask, no transparency/refraction or added point lights.

Model: `models/props/riverside/street_lamp_v2/street_lamp.vmdl`. Three LODs: **2,268 / 1,548 / 732 triangles**, switches at 22 and 55. One shared 1k colour/normal/roughness/metalness/glow atlas and material. Authored budgets, not measured frame times. Canonical +X follows the arm away from the pole, origin at the original head. Bounds `-11.5,-5,-3` to `11,5,4.04`: lens and photocell extend beyond the old vertical envelope. The hollow collar surrounds the existing 1.2-inch-radius arm at its original attachment.

Test placement: engine `1061.570555,262.862964,368`, yaw `-81.469234`, third west-side pole. Actual published arm and point light remain. A later approved installation should audit all four sodium heads and preserve poles, arms, light anchors and collision; no full-map regeneration.

## Historical review recipe

The comparison steps below describe the pre-installation baseline; their original face counts and protected hashes no longer match the installed map. Keep the retained before/after PNGs rather than rerunning the old preparation/capture scripts.

Prefix shell commands with `rtk`. Pass the project root as the final argument to each Python script.

1. `build.py` creates only private candidate assets.
2. `prepare_review.py` verifies and hides exactly 14 old head faces only in a private render-only dressing copy. Existing transformer/searchlight material bindings are retained. Public dressing OBJ/ModelDoc and scene hashes are recorded.
3. `native.py script Sources/Riverside/street-lamp-v2/review.cs.txt` compiles/loads both models, then captures matched underside/top/context views with identical cameras, locked exposure and temporary inspection light. The disposable scene is destroyed in `finally`. An actual saved office porch lamp is also captured without adding a replacement.
4. `verify.py` checks finite/nondegenerate geometry, winding relative to shading normals, bounded nondegenerate UVs, normalized normal-map vectors and protected public hashes. All three LODs passed.
5. `compose.py` arranges the native screenshots without colour/exposure edits.

Evidence: `output/asset-improvement-20261030/riverside-street-lamp/`. Both models load without errors in s&box 26.11.03a. No gameplay or LOD-transition playtest.

The protected hashes passed when the matched captures were made. A later independent edit moved the store fridge light, changing the saved scene hash; the public dressing OBJ/ModelDoc remain at the recorded hashes. The historical full-hash verifier correctly rejects that later scene state. The candidate did not edit or restore the shared scene.

## Installation

`prepare_install.py` reproduced all four authored anchors and staged a guarded 56-face cut against the latest public mesh. `install.cs.txt` published only that cut through the native editor and inserted the `Streetlight Heads` group, with no added lights or colliders. A temporary engine stall delayed saving; native inspection confirmed all four valid instances remained in the active scene, and native `save_scene` then persisted them. The compiled dressing resource is newer than the edited source.

`verify-install.py` passed: four correct saved transforms/models, exactly 56 old faces removed, every unrelated mesh line and the full ModelDoc/collision byte-for-byte unchanged, existing point/spot lights identical, and all 26 porch lamps retained. Backups and receipts: `output/asset-improvement-20261030/riverside-street-lamp/installed/`.

The canonical generator records `STREET_LIGHTS` in `P.pole`, retains existing arm construction and light-return anchors, carries placements through owner transforms and emits the same scene group. The unused cool-head fallback is retained; shared aluminium and sodium materials remain used by other fixtures. No whole-map regeneration or gameplay/frame-time benchmark.

A fresh capture from the saved scene, without adding replacement heads, is `output/asset-improvement-20261030/riverside-pole-insulator/new_installed_street.png`.
