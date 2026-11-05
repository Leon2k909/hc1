# Sewage salvage drums — 2026-11-04

Six coarse rusty cylinders are replaced with detailed salvage overpacks: rolled chimes, rolling hoops, swaged
beads, a recessed head and two bungs, a welded seam and dents. The geometry adapts the existing Boxyard steel
drum v2 LOD0 mesh (6,254 triangles), frozen as `source-drum-lod0.obj`. It is rescaled to the old Sewage cover
envelope (maximum rim radius21.3, total height56), with normals transformed by the inverse scale. Existing
collision remains the original radius20, height54 cylinder. Labels deliberately omit a volume claim.

`paint_drum.py` adapts the original Boxyard painter and reuses its original position/normal/finish/AO bakes in
`output/asset-improvement-20261030/oil-drum/`. It paints new olive and oxide-brown finishes, with salvage/waste
markings, real edge wear, drips, fine scratches and dirt following the surface. No Boxyard asset was modified.
No external downloads or image generation. Private 2048px color maps and shared PBR maps are installed under
`materials/sewage/salvage-drums-v1/`. Four drums use olive, two use oxide, with varied orientations.

`build.py` stages review resources. The old drum's faces are matched against the public asset before replacing
anything, then translated with their original UVs, normals and materials retained. Native `capture.cs.txt`
renders before/after with identical camera, lighting and exposure. `context.cs.txt` renders saved Sewage visual
roots in a temporary isolated scene, with no scene switch, save or play control. The old standalone drum stays
available as the inactive `models/maps/sewage/salvage-drums-v1/before.vmdl` alternate.

`prepare_install.py` snapshots inputs and stages a targeted face splice. Native `install.cs.txt` refuses changed
inputs and publishes only details OBJ/MTL/ModelDoc and two offline generator files. Exactly9,984 old triangles
are removed,37,524 added and55,350 unrelated faces retained, including all26,900 approved crane-block faces.
Full ModelDoc physics, all hull sources and saved scene stay unchanged. `Tools/sewage_salvage_drums.py` emits
the detailed mesh and copies exactly the original cylinder collision; `sewage_map.build` calls this helper.
Do not run a full map rebuild to apply this revision.

Evidence, snapshots and native logs: `output/sewage/salvage-drums-v1/`. `before.png`/`after.png` are actual engine
renders; `context/drum-installed.png` and `location-installed.png` show placement in the map. `verify.py` checks
hashes, exact retained faces, approved cranes, physics/scene/hulls, source mesh hash, nondegenerate finite mesh
data and generated geometry/collision. `check_public.cs.txt` confirms the compiled public model, both private
drum materials and old alternate. The public model was fully compiled. No gameplay/light changes or frame-time
benchmark. Never rerun the historical build/import after installation without reviewing the staged outputs.

`inspection.cs.txt` adds one temporary fill light only inside the isolated capture scene. Its views in
`inspection/` clarify placement beside the green maintenance tunnel. These are labelled inspection lighting;
the map's saved lighting and scene remain unchanged. The capture scene is destroyed on completion.
