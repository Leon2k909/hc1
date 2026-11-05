# Riverside camper — approved and installed

Approved 2026-11-04. The rebuilt camper is installed at world (-298, -276, 96), yaw 100, using
`models/props/riverside/camper_v2/camper.vmdl`. LODs: 33,462 / 23,816 / 6,174 triangles; twelve materials.
The whole exterior was rebuilt: formed siding/rounded shoulders, recessed windows and physical boarding,
framed door, treaded tyres/steel wheels, running gear, ladder, spare, lamps, vent and towing hardware.
The weathered finish, red bands and original blood decals were preserved.

Exactly 480 old triangles were removed from the current public pad OBJ; every other face and all
vertex/UV/normal records were retained. The ModelDoc, including physics, is byte-identical. The saved scene
has only one new renderer; existing propane cylinders, lights and gameplay objects were retained.
No full Riverside generation was run. The original RV geometry code, before/background review assets
and obsolete comparisons were deleted after verification.

`Tools/riverside_camper.py` is the pure geometry builder; `build.py` stages inputs outside Assets for
native import. `riverside_parts.rv()` now retains original collision/propane and registers one approved
instance through CAMPERS/camper_objects(). `verify.py` checks geometry, placement and source reproduction.

Native compilation and source/mesh checks passed. The exact integration receipt is
`output/riverside/camper-v2/installed-verification.json`. Native installed screenshots and validation in
`output/riverside/camper-v2/installed/` loaded no error models and preserved the active scene/play state.
No live-match or performance benchmark was run.
