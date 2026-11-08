# Map-wide framed lantern family

User approved the east terrace fixtures and requested the same new design everywhere on Veridant while retaining the original assets. All 32 lanterns now use the framed head and tapered shaft: 5 already installed on the east terrace, plus 27 replacements (north terrace 3, garden terrace 3, promenade 8, south gardens 6, gate piers 4, forecourt 3). Fixture positions, heights, light components and original collision remain unchanged. The 30-inch gate fixtures use a proportionally shortened shaft.

Remaining-fixture render model: models/props/shared/veridant_framed_lanterns_v1/lanterns.vmdl. Scene object 45a3bc80-535f-4433-8147-cf75899f4c24 at origin. The old North terrace lantern frames and three separate forecourt shaft render objects are disabled to avoid overlapping geometry. Their resources remain available; the five approved east fixtures remain active separately.

Reusable legacy fixtures are retained as models/props/shared/veridant_lantern_original_h30/lantern.vmdl, h96, h120 and h140, along with the previously retained east_terrace_lantern_original_v1. No reusable assets were deleted. The generator now uses the framed family in veridant_parts.lantern_post.

Exact removal checks: Buildings 462 triangles, Dressing 3564; both PhysicsShapeList sections unchanged. Before model/source snapshots and guarded import are under output/veridant/all-lanterns-v1. The first OBJ records needed repacking after accumulated mesh removals; fix-empty-materials.py retains all referenced positions, UVs, normals and face/material assignments and discards only unused records.
