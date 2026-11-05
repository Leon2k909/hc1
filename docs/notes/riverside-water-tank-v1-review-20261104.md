# Riverside water-tower tank v1 - installed A

Built after the T2 hitch; installed after the user chose A over B on 2026-11-04. Source/workflow:
`Sources/Riverside/water-tank-v1/README.md`. Resource `models/props/riverside/water_tank_v1/tank.vmdl`.

Complete vessel rebuild: dished head, welded courses, rim/roof seams, access hatch with gasket, bolts, hinge/handle, downturned
vent, ladder and safety cage. Authored runoff and restrained wear maps. Original atlas lettering now follows the curved shell.
Six materials; 11,788 / 7,288 / 3,316 triangles; no new physics or runtime component. Engine `3600,-1688,1196`, yaw zero.

Keeps the existing legs, braces, riser, catwalk/railing, finial, beacon and floodlights. Private comparison removes 224 actual
saved triangles for the vessel and lettering. Legacy model uses the saved source's own triangle splits, UVs and normals.
Public backdrop source/ModelDoc and saved scene are hash-protected. Native studio/map review uses isolated worlds/scenes with
matching camera, lighting and exposure. Work and receipts: `output/riverside/water-tank-v1/`.
All eight native resources compile. Every LOD passes winding and degeneracy checks; native studio and map captures preserve
the source editor scene/play state and report no error models. Public source/ModelDoc and scene hashes remain unchanged.

Installed one native renderer, removed exactly 224 old triangles and retained all existing scene data, public ModelDoc, support
geometry, collision and lights. Narrow generator comparison and native saved-map captures pass. Twelve comparison files were
retired from Assets. The user rejected B and requested complete deletion: B assets/source/output, its dedicated worktree/branch
and the two-candidate comparison media were removed. Receipts: installed.json, generator-check.json and deleted-b.json.
