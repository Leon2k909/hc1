# Riverside pole transformers — 2026-11-04

Replaced the three plain twelve-sided steel cans on the utility poles with formed transformer tanks, rolled
seams and separate domed lids, lid clamps/fasteners, lifting eyes, ribbed glazed bushings, primary and secondary
terminals, service leads, ground lugs, drain plugs, curved equipment plates and bolted pole saddles. The lead
on each installed unit reaches that pole's existing first crossarm insulator. Existing wires and poles remain.
The finish uses private authored coating/roughness/normal maps, with fine grain, restrained runoff and edge wear.
No external downloads or image generation were used.

`build.py` stages private preview resources. The original can in `before.png` is verified against the published
geometry and translated to the origin with its original UVs, normals and material preserved. `after.png` renders
the9,620-triangle replacement. `capture.cs.txt` uses identical native camera, floor, light and exposure settings
for both variants. The before/after are actual engine renders. The standalone preview omits the long lead to
the existing crossarm; `context/*-installed.png` shows the installed public model, connected and mounted in the
map's original night lighting. Temporary capture scenes are destroyed and editor/play state is preserved.

`prepare_install.py` stages a narrow patch against the current public dressing OBJ. It removes exactly132 old
can triangles and adds29,568 triangles for the three assemblies with their connected leads. The complete public
ModelDoc physics suffix, all hull sources and scene are unchanged. All10,482 other published faces are retained
exactly. A concurrent sandbag installation removed1,408 unrelated triangles while this work was in progress;
the initial guard correctly refused installation, and `--rebase` prepared a fresh snapshot preserving that change.
Both snapshots remain in the output folder; the plan's `baseline` identifies the accepted input.

`install.cs.txt` publishes only the dressing OBJ/MTL/ModelDoc and the two offline generator files through the
native editor. The public dressing model was fully compiled, and `check_public.cs.txt` confirms all seven
private material bindings on the loaded resource. `verify.py` checks installed hashes, exact retained faces,
byte-identical physics, unchanged collision/scene, generator syntax and finite mesh data. `riverside_parts.pole`
calls the retained `Tools/riverside_pole_transformer.py` helper for future generation. Do not run a whole-map
regeneration: the map notes document unrelated shared-kit changes.

Evidence, public-input snapshots and exact plans: `output/riverside/pole-transformer-v1/`.
`preview-compilation.json`, `capture-report.json`, `installed.json` and `verification.json` record the completed
checks. Native context capture results are in the timestamped tool logs. All compiled models are valid; no new
lights, scene objects, gameplay code or collision changes were introduced. No frame-time benchmark was run.

The user confirmed: "i meant use the new and delete old". All three new transformers are retained. The old
132 triangles had already been removed from the public mesh; `retire_before.cs.txt` subsequently removed all
six unused `before.*` preview/source/cache files from the Assets folder, archiving them outside the game under
`output/riverside/pole-transformer-v1/retired-before/`. `retirement.json` records their hashes. `verify.py` passed
again after retirement. The before/after PNGs and rollback input snapshots remain available. Do not rerun the
historical preview import, which would restore that retired comparison asset. Later searchlight work changes
the same public dressing mesh; its verification separately confirms all29,568 transformer faces are retained.
