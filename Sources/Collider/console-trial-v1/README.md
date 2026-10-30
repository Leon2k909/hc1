# Collider control console — accepted and installed, 2026-10-30

The user approved the second proposal and requested the old asset removed. Exactly
688 old render triangles at the reviewed station are removed from the saved
structure mesh and 27,334 approved triangles inserted. Structure: 223,235 → 249,881.
The fourteen private material bindings, positions, UVs and normals match the review.
All unrelated original face lines and attribute tables, original material bindings,
full ModelDoc physics and the saved scene are preserved. This includes the approved
chair and monitor; detail/machine/glass sources and other approved private assets
are byte identical. `Tools/collider_console.py` and the selected control-desk branch
retain the exact result on regeneration; other stations are unchanged.

The unused standalone `before.obj/.mtl/.vmdl` are removed from Assets. Rollback and
scope/geometry evidence are outside Assets at `output/collider-console-accepted-20261030/`.
Matching primary staged sources are synchronized. `installed.json` and
`verify_accepted.py` record/prove this installation. Earlier structure hashes in
chair/monitor/valve receipts are historical; this receipt supersedes them and
proves retention. No editor used; native compilation, appearance, LOD/performance
and final collision fit are still pending.

The remaining text describes the historical proposal workflow.

The user requested another detailed model improvement with actual before/after
images, preserving the original until approval and avoiding the s&box editor
while they play another game.

This proposal isolates the **desk only** at east control-room station
`side=1, north=-55, floor=256`. It does not include or modify the previously
approved chair, wall monitor, valves, equipment case or server cabinet.

`build.py` identifies all **688** legacy console triangles in the saved
`collider_structure.obj`, then copies their positions, UVs, materials and normals
into the standalone before model. It fails if the expected original is absent.
The after is independently authored in a private material/model directory.
The current candidate has **27,334 triangles** and 15 material bindings; it is
intended for one reviewed station, with native LOD/performance work still pending.

The replacement preserves the 100 × 48-inch active display, its existing atlas
quadrant and position, the broad console footprint and the original desk clip.
It adds closed rounded sheet-metal parts, split service fronts, recessed vent
slots, handles, slotted screws, a proper keyboard and mouse, rotary trim controls,
an emergency stop, status lenses, identification plates, a tilt stand and cable
loops. New coating and work-surface textures contain physical grain, scratches,
contact polish and local grime rather than a uniform smooth finish.

An internal first pass left too much uninterrupted deck surface. The second pass
adds three separately fitted deck plates with real gaps, two auxiliary telemetry
displays, selector switches, a side service/louvre panel and subtle edge chips.
The first pass is archived outside Assets under `revisions/first-pass/` in the
evidence directory. The reviewed after image is `after-panel-v2.png`; both meshes
have the same 60 mm camera. The existing before render is reused only after its
source hash, image hash, camera and render settings have been verified unchanged.

Nothing is installed in the saved scene or packed map models. The original is
retained. `candidate.json` and the output manifest protect the four packed model
source sets, the scene, and all prior approved private models/materials by SHA256.

Run in order, with `rtk proxy python -X utf8`:

1. `Sources/Collider/console-trial-v1/build.py`
2. `Sources/Collider/console-trial-v1/verify.py`
3. `Sources/Collider/console-trial-v1/prepare_render.py`
4. `Sources/Collider/console-trial-v1/render_low_impact.py`

The render wrapper launches one Blender process at Windows **idle priority**,
confined to two logical CPUs, with two Cycles CPU threads and no GPU rendering.
The wrapper waits for the child to exit and records the process result. There is
no editor, browser, development server or background asset compiler in this task.
This limits interference; it is not a guarantee of zero effect on game latency.

Evidence lives in `output/asset-improvement-20261030/console/`. The actual-mesh
images use identical camera, model scale, exposure, light rig, samples and render
settings. These are source-mesh previews, **not s&box screenshots**. Engine import,
final engine appearance, collision fit, LODs and performance are still pending.
Do not remove the original or integrate this candidate without user approval.
