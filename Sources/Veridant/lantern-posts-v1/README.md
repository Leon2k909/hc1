# North terrace lantern frames — applied review, 2026-11-06

Accepted by the user. Original complete lantern is retained separately at
models/props/shared/terrace_lantern_original_v1/lantern_original.vmdl, floor-centered,
96 inches tall, with original pole, square canopy and emissive panels. The model
does not create a point-light component. Build/import preparation is
output/veridant/lantern-posts-v1/retain_original.py. Native compilation succeeded.

Added glazing bars and stepped lower steel housings to the three existing north
terrace lanterns. Existing posts, roofs, emissive panels, placement, lighting and
collision remain. Uses existing vr_steel; 540 triangles without added collision.

Source: Tools/veridant_terrace_lantern_frames.py. The lantern_post generator hook
applies this only to North terrace lantern names, using their adjusted placement.
Current scene has one dedicated North terrace lantern frames object, imported,
compiled and saved through the native editor. Model loads without error.

Matching actual displayed viewport captures: output/veridant/lantern-posts-v1/
before.png and after.png. No temporary camera or render-setting changes.
