# Terrace tarp continuous canvas — applied review, 2026-11-06

Accepted. User requested deletion of old asset; unused terrace_tarp_original_v1
Assets folder removed through editor after reference checks. New tarp remains active.

Fixed the shiny checkerboard appearance with continuous cloth UVs and a matte
woven canvas material using existing Riverside folded-tarp weave/normal textures,
neutral olive-grey tint and roughness .86. Existing draped geometry, position,
rail, lighting and collision retained. 2,352 original triangles removed from
Buildings render imports and replaced by the same geometry with corrected UVs.
Unrelated source records and ModelDoc physics unchanged.

Source Tools/veridant_terrace_tarp.py; east_terrace generation hook reproduces it.
New asset models/props/shared/terrace_tarp_v1/tarp.vmdl; original retained at
models/props/shared/terrace_tarp_original_v1/tarp_original.vmdl. Dedicated material
materials/veridant/terrace-tarp-v1/canvas.vmat. Native compilation/model-load
validation passed; scene saved with one Terrace woven canvas 1 object.

Preparation, original source/parent snapshots and matching actual displayed
viewport before.png/after.png: output/veridant/terrace-tarp-v1/. No offscreen
renders or changed lighting/display settings.
