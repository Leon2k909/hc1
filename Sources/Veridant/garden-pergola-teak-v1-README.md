# South garden teak pergola — applied review, 2026-11-06

Unrelated to the colonnade planter. Reuses approved veridant_bench.rounded_member
geometry helper and existing bench-v2 teak/endgrain textures for the south
garden pergola. Timber grain follows each member; beam ends use end grain;
edges eased by .15 inch. Same dimensions, posts, beam arrangement and collision.
No new raster imagery or materials. Model is 22,968 triangles; original 240
render triangles removed from Dressing imports while retaining unrelated
records and physics. Original asset retained at
models/props/shared/garden_pergola_teak_original_v1/pergola_original.vmdl.
New model models/props/shared/garden_pergola_teak_v1/pergola.vmdl.

Source Tools/veridant_garden_pergola.py and gardens generation hook. One South
garden teak pergola 1 scene object, native compilation/model checks passed;
scene saved. Actual matching viewport captures and prior source snapshots:
output/veridant/garden-pergola-teak-v1/. No offscreen rendering or changed settings.
