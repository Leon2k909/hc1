# Café planter — existing Reef Hall asset reused, 2026-11-06

## Correction after user review

User rejected both the old cubes and bronze fit and identified intersection with
the pier. Active model now uses the existing Veridant stone materials and a
smaller fitted shell. Rim bounds plan E=-255..-211, N=-12..37; adjacent pier
E=-218..-202, N=41..59, giving four inches of separation. Glazing E=-260 leaves
five inches clearance. Tree/uplight unchanged; soil remains at Z=22.
Replaced exactly four original collision boxes with one fitted stone box at
plan E=-254..-212,N=-11..36,Z=0..24 through a guarded native import. Other physics
nodes retained. Generator collision and geometry match. Model validation passed.
Actual displayed corrected capture: output/veridant/colonnade-planter-reuse-v1/corrected-stone.png.
Historical bronze description below is superseded; do not reinstall it.

Replaced the olive's four plain black cubes with the approved Reef Hall fluted
bronze planter shell and its existing material textures/UVs. Extracts only rhp_
shell faces from models/maps/reefhall/bronze-planter-v1/planter.obj; foliage and
soil from that asset are excluded. Refits shell to 42x62x24 inches, preserving
the old planting footprint. Continuous soil remains at original Z=22. Original
olive, uplight, four box collisions and route widths retained.

Source Tools/veridant_colonnade_planter.py; cafe generation hook reproduces it.
Reused shell plus soil is 5,986 triangles. Exactly 48 original cube render faces
removed from Buildings imports; unrelated records and ModelDoc physics retained.
Original assembly retained at models/props/shared/colonnade_planter_original_v1/planter_original.vmdl.
Derived fitted model models/props/shared/colonnade_planter_v1/planter.vmdl.
Native compilation/model checks passed; one Colonnade bronze planter 1 object,
scene saved without unsaved changes. No generated imagery or new texture maps.

Matching actual displayed viewport captures and original source/parent snapshots
are under output/veridant/colonnade-planter-reuse-v1/. Existing selected collision
box outlines remain visible as editor gizmos in both captures. No offscreen
rendering or altered lighting/display settings.
