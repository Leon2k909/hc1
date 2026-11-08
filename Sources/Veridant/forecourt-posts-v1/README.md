# Forecourt tapered lamp posts — applied review, 2026-11-06

Accepted. User subsequently requested deletion of the old asset. The unused
forecourt_lamp_post_original_v1 folder and compiled assets were deleted through
the native editor script after checking scene/prefab/model references. New posts
remain active. Historical staging below is not an instruction to restore it.

Rebuilt the three forecourt poles with smooth tapered shafts and shaped plinths.
Existing lantern heads, positions, height, lighting and collision retained.
Removed exactly 132 original render triangles from Dressing imports, preserving
unrelated source records and ModelDoc physics. New model is 1,932 triangles,
existing vr_steel, no added collision. Original complete lantern retained at
models/props/shared/forecourt_lamp_post_original_v1/post_original.vmdl.
New post-only asset: models/props/shared/forecourt_lamp_post_v1/post.vmdl.

Source Tools/veridant_forecourt_post.py. lantern_post generation hook affects
only Forecourt lamp names and retains original hulls/boxes. Current scene has
three dedicated Forecourt tapered lamp post objects. Native compilation passed;
scene saved. Matching displayed viewport before.png and after.png are under
output/veridant/forecourt-posts-v1/, alongside staging and prior source snapshots.
No temporary rendering or changed lighting/display settings.
