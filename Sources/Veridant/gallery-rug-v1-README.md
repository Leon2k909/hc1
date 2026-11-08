# Gallery rug — applied review, 2026-11-06

Replaced the plain brown card with a matte woven rug, tonal stripes and a
three-inch bound border. Same 340x240-inch footprint and furniture layout;
no collision or light changes. Reuses existing Riverside weave/normal textures
with dedicated rug materials. Source Tools/veridant_gallery_rug.py and lounge
generation hook. New model models/props/shared/gallery_rug_v1/rug.vmdl; original
retained at models/props/shared/gallery_rug_original_v1/rug_original.vmdl.

Removed exactly two original Buildings render triangles, preserving unrelated
records and physics. Current scene uses one Gallery woven rug 1 object; native
compilation/model checks passed, saved without unsaved changes. Matching actual
displayed viewport captures are output/veridant/gallery-rug-v1/before.png and
after.png. No temporary rendering or changed lighting/display settings.
Initial source OBJ backups remain; before/parent.vmdl was refreshed during
refinement and is the post-replacement parent, not a restoration snapshot.
