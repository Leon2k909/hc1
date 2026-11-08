# Churchyard gate pier v2 — review only

Selected pier: plan `(-459,-405,0)`, height 64, shaft width 18. The new model has a moulded foot,
slightly tapered dressed shaft, bevelled panels, stepped capital and turned stone finial. Original
scene geometry, collision and lighting remain saved as before. Source LODs: 2,136 / 1,480 / 824
triangles; selected original pier: 116 triangles. Existing photographed cut-stone material is reused.
The finial has authored UVs sampled within one stone, avoiding mortar streaks around the curved body.

The private west variant removes only those 116 original faces. All three VMDLs compiled. Fresh
baseline/candidate definitions are warmed before the final matched pair. The current final evidence
is `before-preview.png` and `after-preview.png` under `output/belltower/gate-pier-v2/`.
Initial final.png renders show the earlier UV draft and are not the current review evidence.

During live play the editor's normal camera became unavailable. `capture_preview.py` creates an
ephemeral editor-scene camera, renders synchronously and removes it. Final capture receipts verify
camera/tone/model/object and editor/play state restoration. No camera or model is saved, and no
frame callback is installed. Effective GPU exposure was not independently measured.
`review.json` verifies matched parameters, successful compilation and saved shared-source guards.

The approved well frame is installed separately; its old geometry and obsolete review assets were
removed. This gate pier is NOT installed and awaits user visual approval.

The live-play background is animated: 2.09% of pixels outside the pier inspection region differ by more than 5/255 between views, mainly in foliage/shadows. Camera, lighting and tone parameters match; do not claim a pixel-identical background.
