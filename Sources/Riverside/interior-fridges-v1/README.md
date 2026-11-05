# Riverside interior fridges - three installed

Player-visible improvement: three glass-door drinks fridges beside the Lucky Stop aisle. The originals are plain boxes with
illuminated product-picture cards (14 triangles each). Reuses the already approved porch cabinet rather than building a duplicate:
32 separate drinks, four wire shelves, recessed liner, clear glass, door gasket/hinges, pull handle and compressor grille.
The model and all ten materials are reused without redesign or new textures. Local mesh is an exact translation of the installed
34,152-triangle approved cabinet. One shared model, three instances; this model has the same single detail level as the original
approved porch resource. No performance benchmark or new LOD pass is claimed.

Checked CLAUDE.md, existing approved models, pending sources and active model chats before selection. Porch cabinet upgrade is
explicitly documented as porch-only; the three interior units remain crude. Other active work includes roof ladder, shed light,
Riverdale sand bin, Boxyard pallet stack, Reef Hall coral and Belltower well/sacks; none duplicates these interior fridges.

Resource: models/props/riverside/interior_fridges_v1/fridge.vmdl. Engine positions 760,-348,20; 794,-348,20; 828,-348,20;
yaw -90. Existing 30 x 28 x 72-inch cabinet envelopes retained. No new physics or lights. Private store copy removes exactly 42
fingerprint-matched original triangles while retaining every other public ModelDoc mesh/material/physics section, including
the installed porch fridge, counter, shelving, register, ice cabinet and shop sign. Saved map and public store are untouched.

Reproduce: build.py stages outside Assets; prepare_review.py prepares the known disposable-scene render workflow; review.py import
uses native editor scripts and compiles three resources; verify.py checks protected/imported hashes and exact approved geometry;
review.py context renders matching player-height before/after views; compose.py pairs native images without retouching them.
Approved and installed on 2026-11-04. Three native renderers are saved under Interior Drinks Fridges; exactly 42 original
triangles removed from the active public store input. The public store ModelDoc, all original colliders, point lights and other
upgrades are preserved. A narrow generator hook emits the three cabinets and retains the old collider/light authoring. The
private whole-store comparison was never installed. All 12 legacy/private comparison files were removed from Assets; receipts
and a retired-review archive remain in output/riverside/interior-fridges-v1/. installed.json records saved-map verification.

Final native captures use separate disposable scenes for before and after, preventing variant visibility from leaking between
views. Both report no error models and preserve the active Riverside editor/play state. Player-height wide/detail images were
inspected. All protected public-resource hashes still match after capture. Final comparison: player-height-comparison.png.
