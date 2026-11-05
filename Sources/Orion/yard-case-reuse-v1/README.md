# Orion central-yard equipment case — approved-model reuse preview

**User decision (2026-11-04): keep both versions.** Retain the original Orion case and the shared
upgraded Collider case, plus this reuse comparison. The original remains active in Orion; the user's
retention request did not request installation. Do not delete either model.

The user's priority was a model visible up close, after checking for an existing better version.
The audit found the already approved Collider equipment case, so this proposal reuses it directly.
It adds no duplicate upgraded mesh or materials. Acceptance is recorded in
`Sources/Collider/equipment-case-trial-v1/installed.json`; the model is
`models/props/collider/equipment-case-trial-v1/after.vmdl`.

Selected Orion's single large case on a pallet beside the central playable yard route (source
`orion_map.yard_props`, `case_block((-17,581), ..., size=(70,40,46), seed=10)`). It is a close-range
cover prop. The model has recessed folding handles, butterfly latches, lid seals, edge rails, corner
guards, hinges, stacking pads and an identification plate. This is an existing accepted design,
not newly authored geometry.

**Preview only; the saved map still uses the original.** The isolated review removes exactly 568
matched original case faces from a private copy of `orion_props.obj` and places the shared 15,568-triangle
model at world `600.564985,-17.337997,5.7`, yaw 0, scale `0.7142857,0.7,0.7076923`. It fits the original
70x40x46 body proportions. The original pallet stays. The renderer adds no collider; authored Orion
physics remain unchanged. Shared Collider model/material source files and the public Orion scene,
props OBJ/MTL and ModelDoc retain their original SHA256 hashes.

`prepare.py` matches the current baked case by material and rounded positions, then preserves exact
saved positions, UVs and normals in a compact baseline. The private whole-yard preview changes only
the selected render faces and its render-file reference; its physics are identical to the current
props ModelDoc. Inputs are staged outside Assets and imported using `import.cs.txt` through native
`run_csharp`. Both private ModelDocs and the shared model compiled successfully. The first standalone
baseline contained empty material groups; it was compacted without changing selected face attributes
and then compiled successfully.

`capture.cs.txt` loads the saved map's visual roots in an isolated editor scene, swaps the private
props renderer and enables the shared case only for the after views. Both columns use the same map
lighting, cameras, fixed ACES exposure compensation +1 and texture settling. Top view: 64-inch player
eye height; a native floor ray hits the yard floor at z0. Bottom view: closer hardware inspection.
No additional review lights. The capture destroys its isolated scene and preserves the user's active
scene/play state. `compose.py` only resizes matching views and adds labels.

`verify.py` independently checks unchanged protected/shared files, imported hashes, exact selected
face attributes, all other face lines and original attribute tables, unchanged physics, valid mesh,
scaled bounds, compilation receipts, floor hit, zero added colliders and unchanged editor state.
Evidence and matching images: `output/orion/yard-case-reuse-v1/`.

No live match or frame-time benchmark. The existing case has one LOD; this preview covers one close-range
instance. No installation or retirement is pending. A future explicit installation request should
retain both designs and the original pallet/physics. Do not regenerate the whole map or change shared
Collider assets.
