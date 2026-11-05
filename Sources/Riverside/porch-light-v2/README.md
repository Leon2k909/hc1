# Riverside porch bulkhead lamp v2 — installed

Approved and installed on 2026-11-04. **All 26 fixtures are saved**: 24 trailers, the office and Lucky Stop. The storefront fitting is scaled to its original 8 × 6 × 5-inch envelope; the others keep the reviewed 5 × 4 × 6-inch envelope. Existing point lights and physics are unchanged. The original `rs_porch_light.vmat`, compiled file and metadata were deleted through the native editor after a zero-dependant audit.

The original porch fixture is a fully emissive 5 × 4 × 6-inch box (`P.trailer`, `rs_porch_light`). The replacement fits the same envelope: oval cast housing and removable rim, a rubber gasket, two side mounting ears with slotted screws, a domed frosted/fluted lens, an oval guard ring and three arched cage rods. The frosted lens is opaque with a restricted warm emission mask; it does not use a transparency/refraction pass or add a point light. Existing porch illumination is retained. The housing has restrained coating/zinc wear and film; all new textures are procedural, with no external assets or ImageGen.

Model: `models/props/riverside/porch_light_v2/porch_light.vmdl`. Three LODs: **5,396 / 2,192 / 908 triangles**, switches at 18 and 50. One 1024 × 1024 atlas supplies colour, normal, roughness, metalness and glow; one shared material. These are authored budgets, not measured frame-time results. Canonical front is engine +X, origin at the fixture centre, back at X=-2 inches. Bounds: `-2,-2.475,-2.856` to `1.8048,2.475,2.856`.

The office fixture centre is engine `-578,670.767076,208`, yaw 0. This is reproduced from the seeded office `P.trailer` call, then checked against the published pad's exact 12 lamp faces. Only those faces are hidden in a private render-only background; every other lamp remains original during the review. No whole-map regeneration.

## Historical review recipe

The following describes the approved pre-installation preview. Its original material and five old comparison backgrounds have since been retired; do not rerun the original preparation, comparison or production-hash checks against installed sources. The build recipe and retained PNGs remain available.

Prefix shell commands with `rtk` in this repository.

1. `python Sources/Riverside/porch-light-v2/build.py <project-root>` creates only the private candidate model/materials.
2. `python Sources/Riverside/porch-light-v2/prepare_review.py <project-root>` records the office transform, creates the private pad comparison background and snapshots the production pad OBJ/VMDL and saved scene hashes.
3. `python Sources/Riverside/porch-light-v2/native.py script Sources/Riverside/porch-light-v2/review.cs.txt` compiles/loads both review models and captures matched old/new angle, front and porch-context views. Existing map lighting, locked exposure and an identical temporary inspection light are used. The disposable scene is destroyed in `finally`, preserving active scene/play state. It also captures the saved installed speed sign, without inserting a duplicate.
4. `python Sources/Riverside/porch-light-v2/verify.py <project-root>` checks all three meshes for finite/nondegenerate geometry, outward winding relative to the shading normals, bounded nondegenerate UVs, normalized normal-map vectors and unchanged protected public hashes. Passed.
5. `python Sources/Riverside/porch-light-v2/compose.py <project-root>` arranges the native screenshots without colour/exposure edits.

## Installation and retirement

`prepare_install.py` audited all 26 actual published boxes against the authored centres/facings, including the raised trailer's lift. `install.cs.txt` checked hashes, published narrow cuts through the native editor, inserted the `Porch Lights` group and marked the scene dirty. Native `save_scene` persisted it and all five public zone models compiled successfully. Exactly 312 active box faces were removed, plus the inactive canonical store copy.

Strict `verify-install.py` passed immediately after installation: saved transforms/scales/models correct, every unrelated OBJ line retained, physics unchanged and all existing point/spot-light data identical. A concurrent counter installation then removed unrelated counter faces from shared store sources. Use `verify-install.py <project-root> --current` for current placements, lights, physics and absence of old fixture faces in all current imports; the strict initial receipt remains in `installed/verification.json`.

`prepare_retirement.py` and `retire-legacy.cs.txt` removed old lamp faces, unused material aliases and remaps from retained Riverside comparison assets. All unrelated geometry and physics were preserved. Five unused backgrounds still held cached dependencies after compilation; each had zero dependants and was archived/deleted through `Editor.Asset.Delete()`: the previous speed-sign, sandbag pad/store, crate and lantern backgrounds. Historical PNGs and source snapshots remain. The old material's native audit then reached zero, and `delete-legacy.cs.txt` deleted its source, compiled file and metadata. The material generator no longer creates it. Backups and exact plans: `installed/legacy-cleanup/`.

The retained generator records `PORCH_FIXTURES`, carries them through trailer/stilt transforms and emits the saved group. A partial in-memory authoring check reproduced all 26 saved transforms, scales and GUIDs and generated no old lamp geometry (`installed/generator-verification.json`). No whole-map regeneration. `capture-installed.cs.txt` renders the saved office, raised-trailer and larger store fittings with actual world geometry, without adding replacement lamps. Captures are in `output/asset-improvement-20261030/riverside-street-lamp/`. No gameplay or LOD-transition playtest.

After the captures, another chat moved the unrelated `fridge 77` light from X=534 to X=598. Its component data is otherwise identical. The current verifier preserves that independent change and checks porch anchors specifically; the original full-light preservation receipt describes the installation itself.

That independent fridge placement fix also shifted its single 30 × 28 × 72-inch collider from X=560 to X=624. The current check verifies that this is the sole physics delta against the lamp installation baseline and preserves it. The lamp group itself has no colliders or added lights; native final checks confirm 26 valid fittings, five valid public zones and no legacy material source/compiled/meta files.
