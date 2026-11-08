# Queue bars — actual textured metal revision, 2026-11-06

User clarified that the visible bar texture remained inadequate, not merely its
brightness. This separate variant adds a shaft texture set: 512x2048 colour,
normal and roughness maps with directional brushed grain, broader polishing
variation and fine relief. Fully metallic shader; neutral silver albedo. No
global chrome, lighting or render settings are changed. New black tops, weighted
bases and connectors are retained. Earlier proposals and texture drafts are kept.

Shafts now have explicit cylindrical UVs spanning their 33.15-inch height, with
continuous per-face angular coordinates at the wrap seam. This avoids the prior
atan2 discontinuity and repeating an 8-inch sample along the shaft. The base
material remains the v2 finish. `materials.py` generates the maps from seeded
procedural grain; it does not edit a supplied image or bake lighting into colour.
The initial subtler texture draft is retained under the output directory.

Geometry remains 12,376 triangles; all 89,504 unrelated source faces/indices/UVs
remain. Geometry validation and native compilation passed. Actual viewport
close-up: `output/cerroblanco/queue-posts-metal-v3/shaft-texture-closeup.png`, native
screenshot_game crop, position (1028,-180,46), angles (24,-43,0), FOV80, unchanged
scene lighting. No Computer Use, temporary camera or offscreen preview. The public
Fit-out Detail renderer was restored, leaving the original barrier active while
the texture is reviewed. All previous models/materials and generated assets stay.

User subsequently approved this version for the map. Native APIs replaced the
952 old queue triangles with 12,376 new triangles in public fitout-fine and added
the two material remaps; native compilation passed. `cerroblanco_queue_posts`
provides the generator model, called once for the two existing queue lanes.
The original lane spacing/collision are unchanged. All variants remain retained.
