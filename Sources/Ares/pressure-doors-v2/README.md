# Ares pressure doors, 26 October 2026

The three sealed hatches now use blue-grey coated leaves, recessed light panels,
continuous seals, chamfered frames, six cam dogs and linked locking rods, a solid
manual release wheel, a compact control panel, an analogue pressure gauge,
fasteners, warning plates and a grooved threshold. Private PBR maps and lettering
live in `Assets/materials/ares/pressure-doors-v2`.

Geometry is in `Tools/ares_pressure_door.py`; `Tools/ares_airlock.py` exports it
for future map generation. `ares_map.configure` retains its explicit private
material overrides. The former construction is preserved in `previous-airlock.py`.
Do not run the full map generator just to update these assets: it rewrites scenes.

The installed `ares_hall.vmdl` references `hall_base.obj` plus `wing_west.obj`,
`wing_east.obj` and `cargo.obj` in its private import directory. The base is an
exact byte prefix of the original canonical hall OBJ, containing all 23,700
unrelated triangles. The original canonical hall OBJ and MTL are retained.
The three original hatches contained 3,954 triangles; their replacements contain
25,472. The complete hall now renders 49,172 triangles. Every byte from the
PhysicsShapeList to the end of the original ModelDoc is preserved.

The first attempted import failed and temporarily hid the building. Restoring
the backed-up ModelDoc and recompiling restored it. Source 2's importer rejected
the removed doors' unused trailing vertex/UV/normal tables, and the initial wing
node names contained hyphens. The corrected import removes only the unused
suffix and uses underscore names. `trial_hall.vmdl` compiled and was captured
with a temporary, restored renderer override before the live hall was updated.

Native receipts, input hashes and backups are in
`output/ares/airlock-door-v1/stage-v3`, with the first working ModelDoc backup in
`stage-v1/before`. The native import script defaults to preview mode and checks
source hashes, protected inputs, the trial, physics and editor state before
publishing. Do not republish a stale manifest after shared source edits.

`verify.py` checks installed hashes, retained geometry, physics, 14 compiled
assets, all 27 matching collision rays and capture restoration receipts.
Editor captures are under `output/ares/quality/pressure-door-v2-installed-v3`.
No scene save was performed by this task. Another save occurred in the shared
editor during final checks; both scene hashes are recorded in `installed.json`.
The current editor pose, active document and stopped play state were preserved.
