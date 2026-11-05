# Belltower doorway lantern v2 — pending review, 2026-11-04

After installing all seven approved café tables, the wall fixture from the original lamp-overlap
screenshot was rebuilt for review at plan anchor `(-1850,475,126)`, yaw 180. The complete bracket,
glass enclosure, stepped ogee roof, vent, hanging hardware and lampholder were rebuilt using
existing materials. Original reach/scale and collision are preserved; no light changes are saved.

`Sources/Belltower/wall-lantern-v2/` owns the build, placement, receipts and native review helpers.
`models/maps/belltower/wall-lantern-v2/wall_lantern.vmdl` has 5,680 / 3,744 / 1,788 LOD triangles.
The private review variant removes precisely 960 original fixture triangles. All three VMDLs
compiled successfully. Warm matched before/after native views preserve editor/camera/tone/object
state and all saved scene/shared-source hashes. Evidence: `output/belltower/wall-lantern-v2/`.

The user approved the new lantern and explicitly asked to KEEP the original asset because its shape was useful.
Installed all 24 matching fixtures (12 west, 12 east) through the editor, replacing 23,040 old baked triangles
across twelve mesh sources. Seven affected map VMDLs compiled. Scene save, preserved physics/object IDs,
mirrored generator placements, editor state and matched saved after screenshots were verified.

KEEP `models/maps/belltower/wall-lantern-original/wall_lantern_original.vmdl`: this is the full original
960-triangle bracket and lantern as a reusable standalone resource, not just a screenshot or temporary backup.
Its OBJ/MTL, compiled resource and procedural source remain available; native compilation/loading passed.
No old asset files were deleted. `Sources/Belltower/wall-lantern-v2/installed.json` records the checks.
The new accepted build remains under `wall-lantern-v2`; `Tools/belltower_wall_lanterns.py` emits stable scene IDs.
`belltower_map._legacy_wall_lantern` preserves the old procedural authoring and custom scale/reach behavior.
