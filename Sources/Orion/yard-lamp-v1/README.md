# Orion yard lamp — 2026-11-04

Replaced the plain box head on the yard's single pole light, beside the forklift and case stack near the service
tunnel, with an oval cast housing, fitted convex diffuser, gasket, upper cooling ribs, hex fasteners/washers,
hinge/latch hardware and three bent guard supports attached to the bezel. Three private materials use authored
fine coating/normal/roughness maps. The diffuser reuses the existing `oa_lamp_warm` material. No image generation
or external assets. The original pole, anchor and point light (position, color, radius420 and shadows=false) remain.

The head stays inside the original10×12×8-inch plan envelope except for the thin guard extending0.095in below
the former glass plane. The diffuser's lowest emitting point remains at world z91.9. No gameplay/collision or
saved-scene changes. The accepted new head is active. On user approval, the old `before.*` alternate was removed
from game Assets; a rollback copy and deletion receipt live under `retirement/`. The installed map retains the complete original pole.

`build.py` stages review resources and verifies the old head against published faces. Its original UVs, normals
and materials are preserved in the comparison. Native `capture.cs.txt` renders before/after using identical
camera, lighting, exposure and the same short pole section. `context.cs.txt` renders saved Orion visual roots
inside a temporary isolated scene, showing the fixture and the full pole's placement. It does not switch/save
the user's document or control play state; temporary capture scenes are destroyed.

`prepare_install.py` snapshots shared inputs and stages a narrow face splice. Native `install.cs.txt` refuses
changed inputs and publishes only props OBJ/MTL/ModelDoc and two offline generator files. Exactly14 old head
triangles are removed,2,984 added and102,866 unrelated faces retained exactly, including the complete pole.
Full ModelDoc physics, all hull sources, source point-light declaration and saved scene stay unchanged.
`orion_map.yard_props` calls `Tools/orion_yard_lamp.py` for the head. No complete map rebuild is needed.

Evidence, snapshots and native receipts: `output/orion/yard-lamp-v1/`. `before.png`/`after.png` are real engine
renders; `context/location-installed.png` shows the lamp beside the forklift, crates and service-tunnel entrance.
`verify.py` checks installed hashes, exact retained faces, physics/scene/hulls, point light, finite/nondegenerate
mesh data, head envelope and matching generator output. `check_public.cs.txt` validates the loaded public model,
all three private material bindings and absence of the old review alternate. No frame-time benchmark was run. Do not rerun
historical build/import scripts after installation without reviewing their staged results.
