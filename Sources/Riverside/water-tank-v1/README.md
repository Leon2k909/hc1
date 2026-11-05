# Riverside water-tower tank v1 - installed A

The user compared both new candidates, chose A and explicitly requested B's complete deletion. A is installed. B's assets,
sources, outputs, comparison media, dedicated worktree and branch are deleted; see `deleted-b.json` in the work folder.

Built 2026-11-04 after the T2 hitch and installed following the user's selection of A.

Rebuilds the complete vessel: dished lower head and rolled knuckle, welded shell courses, rim, standing roof seams, sloped roof
access neck, gasketed/bolted hatch, hinge and grab handle, downturned open vent, ladder standoffs, rungs and safety cage. Painted
steel has authored color, roughness and subtle normal maps with restrained runoff, dirt and small corrosion flecks. Roof runoff
follows a radial map. The original RIVERSIDE / STICKS / TOGETHER atlas lettering is retained and projected onto a curved surface.

Six materials including the existing white-paint atlas. Three LODs: 11,788 / 7,288 / 3,316 triangles. Tank diameter stays 420 in;
roof top stays local Z 342. The dished underside extends to -35. Main root is engine `3600,-1688,1196`, yaw zero; plan
`1688,3600,1196`. The old finial, aviation beacon, support legs, braces, riser, catwalk, railing, floodlight fixtures and point
lights stay in the public backdrop. No new physics or runtime components. No public map regeneration.

Build: `rtk proxy python -u Sources/Riverside/water-tank-v1/build.py`. Candidate files stage in
`output/riverside/water-tank-v1/stage/Assets`; `--geometry-only` updates the candidate without rebuilding the source cutout.
`--materials-only` updates staged materials without rebuilding geometry. PNGs encode in memory and are written in one batch,
avoiding the incremental file-write stall seen during the first export.
Native import/compile: `review.py import`. Captures: `review.py isolated` and `review.py context`. Check `verify.py`; compose
`compose.py`. `prepare_review.py` records the template transformations and is not required for routine capture.

Resource `models/props/riverside/water_tank_v1/tank.vmdl`. The private review background removes exactly 224 original vessel and
lettering triangles from the current public backdrop OBJ. Selection matches the exact original material/vertex triangle set,
then extracts the actual saved triangles, UVs and normals for the legacy model. The intermediate roof radius is 115.5 inches,
matching the original generator's `210 * 0.55`. `inspect_source.py` records the source diagnostic.
Public source OBJ, public ModelDoc and saved scene are hash-protected. Native captures use isolated worlds/scenes, identical
cameras and light, and the original map lighting with exposure fixed at 3.5. Work, manifests, receipts and images:
`output/riverside/water-tank-v1/`.

Validation passes: all eight native resources compile; every LOD has zero inverted/degenerate triangles and decreasing counts.
Installation removed exactly 224 original vessel/lettering triangles from the current public backdrop and saved one native
ModelRenderer under `Water Tower Tanks / Riverside Water Tank`. All existing scene objects, the complete original backdrop
ModelDoc, retained support structure, lights and collision are preserved. The generator removes only the same old vessel and
lettering and emits A's placement; default towers remain unchanged. Actual saved-map native captures pass with no error models.
Twelve legacy/private-background comparison files were archived outside Assets and deleted through the editor. Receipts:
`installed.json`, `generator-check.json`, `native-install-compile.json`, `installed-capture.json` and `deleted-b.json`.

Do not rerun pre-install build/verify over the installed backdrop: the old-face guards intentionally reject it. B must not be
restored or installed. Shared original materials and the original structural parts remain in use and must stay.
