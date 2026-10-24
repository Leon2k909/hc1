# Garden table planter shrub

The planter at plan (-470, 740, 148) uses the installed beech shrub's native
LOD0 mesh and default material group, scaled to 0.43 and rotated 24 degrees.
Its base is embedded one inch below the former soil level. A slightly mounded
soil surface, its own PBR texture and small mulch pieces cover the root contact.
`Tools/veridant_planter_shrub.py` supplies this one placement during regeneration;
all other olive calls retain their original implementation.

The 466 old triangles were removed exactly from both the canonical foliage OBJ
and the active `pergola-flowers-v2/foliage-base.obj`. The replacement adds 2,972
triangles. All retained OBJ bytes and original index mappings are preserved;
the flower import, scene and physics are unchanged. The foliage model keeps its
render imports and gains two material mappings.

Final active publication: `output/veridant/olive-v2/stage-v4-active/manifest.json`.
Canonical publication: `output/veridant/olive-v2/stage-v3/manifest.json`.
Native material inspection, compilation and matched captures are recorded in
`output/veridant/olive-v2/validation.json`. The final image is
`output/veridant/quality/planter-shrub-final/planter.png`.
