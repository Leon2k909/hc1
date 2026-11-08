# Courtyard stair handrail

Reuses the approved reception rail's smooth tube/capped-end helpers on the courtyard stair. The top and middle rail keep their original path, diameter and height. Five supports now attach through small steel plates to the stair's outer side, with post feet and anchors following the actual 17-tread profile. End supports move inward 3.5 inches so their mounting plates fit the stone. The stair itself and all player clipping remain unchanged.

New model: models/props/shared/veridant_court_stair_rail_v1/rail.vmdl, 2352 render triangles. Saved scene object 45a33723-b97f-4de1-b188-27f8dd0eb1d6 (Courtyard stair smooth mounted handrail) at world origin. Original reusable rail model: models/props/shared/veridant_court_stair_rail_original_v1/rail_original.vmdl. No reusable assets deleted.

Removed 94 original render triangles: the 82-triangle stair rail plus a 12-triangle duplicate support shared with the landing rail. PhysicsShapeList is unchanged. The generator skips that duplicate landing support and uses Tools/veridant_court_stair_rail.py for the stair rail, retaining the same clip bounds. Guarded parent/source snapshots, geometry matching checks and scripts are under output/veridant/court-stair-rail-v1. The edited OBJ was repacked without altering the remaining faces' positions, UVs, normals or material assignments.

Before and after are native captures of the actual Veridant editor viewport at camera (10,-565,90), angles (0,180,0), FOV80. No new camera, temporary render, lighting or display changes. Images: output/veridant/court-stair-rail-v1/before.png (18.53.00) and after.png (18.56.07). Approved by the user on 2026-11-06; original asset retained.
