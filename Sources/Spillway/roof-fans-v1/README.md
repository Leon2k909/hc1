# Spillway rooftop extractor fans — review, 2026-11-04

Rebuild of the seven flat fan tops on existing rooftop ventilation units: three above the west turbine hall,
four on the east service tower. The existing rectangular curbs, wall louvers and building geometry are retained.
No suitable approved extractor model existed in the local asset catalog; this is new geometry, not an imported asset.

Each replacement has seven swept, pitched and thickened blades, a spun motor boss, a folded mounting flange,
rolled barrel/throat, eight base bolts, a domed welded guard with ten rings and 24 spokes, four guard clamps and
two lifting eyes. Four private PBR materials share fine alloy, normal and roughness textures. No image generation
or external assets. The original radial footprint is preserved (47/46-inch outer radius); maximum height is
14.80 inches instead of 7.50. All fan geometry remains render-only, retaining every original collider.

**Accepted and installed.** All seven map placements and the generator now use the new fans. The guarded native
installer published the narrow splice without rebuilding the map or changing the user's scene/play state.
At the user's request, all original comparison assets remain available, with the descriptive reusable alias
`models/maps/spillway/roof-fans-v1/legacy_fan.vmdl`. The frozen `original()` generator also retains both original
sizes. `review/retained-variants.json` records old and new resource paths. Keep both versions.

`build.py` requires every original fan triangle to match the actual public OBJ by material, position, UV and normal.
West: 4,062 old triangles removed, 52,164 added, 54,678 unrelated faces preserved exactly. East: 5,416 removed,
69,552 added, 48,556 unrelated faces preserved. Full ModelDoc physics suffixes, all hull sources and the saved
scene remain byte-identical. Existing approved wall vent, service cabinets, waterline work and other props are kept.

`capture.cs.txt` renders actual before/after face samples with matched camera, framing, lighting, exposure and floor.
`context.cs.txt` clones saved Spillway visual roots and substitutes only the two candidate building render models.
It renders a close roof view, the west turbine-hall placement and the east tower placement. No changes to the user's
scene, play mode or unsaved state. Temporary scenes are destroyed in `finally`; no envmap bake or frame callback.

`verify.py` checks public/preview hashes, exact retained faces, unchanged physics and hulls, finite UVs/normals,
nondegenerate triangles, render-only geometry, original footprint and stated height. Native compilation, actual
screenshots and loaded material bindings complete the review. No FPS benchmark is claimed.

Evidence is in local `review/` on C: to avoid the project's slow offloaded `output` junction. Historical build
scripts should not be rerun after acceptance without preparing fresh guarded inputs.
