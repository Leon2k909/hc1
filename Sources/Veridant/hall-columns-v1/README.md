# Operations hall columns

Replaced the three coarse 16-sided render cylinders with 96-sided columns, a quarter-inch eased end, and continuous cylindrical UVs for the existing vr_stone material. Positions, diameter 28 inches, height 112 inches and original gameplay hulls remain unchanged. The source generator separates render geometry from the retained collision hull.

New model: models/props/shared/veridant_hall_columns_v1/columns.vmdl, 1728 triangles for all three. Scene object e6b03661-5770-45d2-a5ff-2d0de8110c9b at origin. Original reusable model: models/props/shared/veridant_hall_column_original_v1/column_original.vmdl. Exactly 96 render triangles removed from Buildings; PhysicsShapeList unchanged.

Native viewport comparison camera (-445,-285,62), angles (0,-140,0), FOV80. No temporary render/camera or lighting changes. Before image: output/veridant/hall-columns-v1/before.png. Approved by the user on 2026-11-06.

Verified after capture: output/veridant/hall-columns-v1/after.png, native frame 18.48.03. Both shared parent models and both new render models load with IsError=false after recompilation. The live viewport State camera was set directly through the native editor to match framing; no new camera or render path was created.
