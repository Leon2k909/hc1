# Approved Riverdale emergency phones

Installed on 2026-10-31 after the user approved the right-hand native preview. All eight wall phones
are shared instances of the exact approved model, with a matching static ModelCollider on each.
Exactly 80 body triangles and 928 fine-detail triangles were removed from the two packed hall OBJs.
Every unrelated OBJ line is byte identical; the only scene change is the Emergency Phones group.
Original mounting positions and facing are preserved, and desk phones are unchanged.

The editor closed before installation, so the saved-file installation did not reopen it. The shared
phone asset had already compiled and passed all seven native collision tests. Fresh native validation
of the placed scene remains pending. The two packed hall models need compilation after the removed
faces; their unchanged ModelDocs were timestamped newer than their compiled caches to trigger a stale
check. Use native asset_compile (or compile-stale.cs.txt) on the next editor session before validating.

Current receipt: installed.json. Verification: verify_install.py checks all transforms, model/collider
bindings, UUID uniqueness, exact face removal, preserved scene content and matching regeneration.
Tools/riverdale_emergency_phones.py records the original hall placements and emits shared scene objects;
riverdale_hall.wall_phone records each placement, and riverdale_map.write_scene authors the group.
Rollback and stage: output/riverdale-emergency-phone-installed-20261031/.

The following describes the historical preview.

# Riverdale emergency phone proposal

The yellow wall phone in the user's screenshot is `riverdale_hall.wall_phone`. This private proposal keeps
the published phone and all map sources untouched until approval. The baseline combines the actual saved
10 detail triangles and 116 fine triangles at plan `(1000,340,45)`, retaining their UVs. Re-exported normals
are checked against the saved normals with the OBJ writer's quantization tolerance.

The new 45,140-triangle hero model has a rounded cast housing/backplate, gasket and hinges, fasteners,
continuous smooth receiver, separate cradle arms and receiver grilles, physical numbered keypad buttons,
readable instruction/identification plates, a coiled flexible cord with glands, and a ribbed red beacon
with a protective cage. Five matched 2048-square PBR material sets supply restrained paint relief,
localized edge wear, roughness and metalness; a sixth atlas supplies the printed legends. Printed labels
are prepared at physical aspect ratios before atlas packing. No broad random dark blotches are used.

Collision uses a close-fitting 24-vertex shell hull, three 16-vertex receiver/beacon hulls and one grip
box. The receiver gap stays open; the flexible cord has no blocking rectangle. All seven native physics
probes pass. Production LODs and a frame-time benchmark are still future installation work.

The native comparison shows original left and proposed right at scale one in a single shared camera.
It uses Riverdale's wall materials and controlled identical native lighting, in an isolated scene rather
than the active match. Native 3840x2160 images resolve to 1920x1080. Both views were inspected; the
temporary scene was destroyed and the active runtime scene/play state were preserved.

A published hall edit occurred during authoring. `finish_build.py` rechecks the selected original
phone against current saved triangles and UVs; `review.json` records concurrent source changes separately.
This task writes only private preview resources through native editor scripts. It does not rebuild the map.

Sources: `build.py`, `finish_build.py`, `prepare_wall.py`, `publish-preview.cs.txt`, `capture.cs.txt`.
Evidence: `output/riverdale-emergency-phone-review-20261031/`. `finalize_review.py` verifies current native
compilation, image dimensions/hashes, resource hashes, runtime collision results and preserved editor state.
The existing `Sources/Collider/tool-cabinet-trial-v1/native_cli.py` supplies the shared native transport;
the local wrapper uses its own output directory and cleans its owned MCP exchange scripts.
