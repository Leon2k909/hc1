# Sewage power cabinet v2

Created and **installed 2026-10-31**, at the user's word after an in-engine before and after ("Yes, install it"). See `docs/notes/177`. Sewage is a
live Zombies map (`MapInformation.ZombiesOnly`); Refinery, the other candidate, is in `GameUtils.DisabledMaps`.

The old cabinet was a flat box with eight bars on it, three times over in `sewage_details`. This one is a motor control cabinet: bolted frame,
hazard-striped plinth, two hinged doors with pressed louvres, an instrument panel with meters and pilot lamps, a red main switch, a lock rod with a
padlock, three floor conduits up its side into the roof, and a caged green status lamp. Blue-grey enamel over red oxide over steel, with about a third
of the paint broken by rust.

- Triangles after the 2026-11-04 instrument pass: 21,982 / 11,022 / 5,324 / 1,882 (LOD 0-3, thresholds 30, 80, 180), previously 21,610 / 10,840 / 5,204 / 1,832.
- One material. Painted at 3072 (13.5 px/in, doors 16); colour and normal are saved at 4096, the rest at 2048, as the engine can't filter a
  normal map that isn't a power of two. About 14 MB compiled for colour and normal together.
- The carcass fills the old box (X +-18, Y +-38, Z 0..115), so its old hull in `sewage_details.vmdl` still serves it. This model's only collision is a
  box round the conduits (to Y -44), which stand outside that hull. Handles and the lamp don't collide: they're above a player's height or
  within an inch or two of the door.
- `check_outward.py` flags one piece, the header. It's an open shell with its hidden faces removed, so its volume means nothing.

## The files

- `cabinet.py` builds, bakes and exports; `paint_cabinet.py` paints; `cycle.ps1` runs them, then compiles and renders.
- `install.py` did the install, and refuses to run once the cabinets are in. It cut 594 triangles from `sewage_details.obj` (the cabinets, their
  lamps and 18 triangles of rubble hidden inside them), added three objects to `sewage.scene` and moved Work lights 37-39 to the new lamps.
- `check_installed.py` and `check_installed.cs.txt` check the real scene in an isolated editor scene: renderers, lights, rays and pictures.
- `compare.py` and `capture_engine.cs.txt` made the before and after. Their "before" needs the old OBJ, so they no longer show the old cabinet unless it's
  restored from commit 5c80147c.
- `Tools/sewage_map.py` now keeps only the cabinets' collision and lights. Run into a scratch folder, it matches the live OBJ apart from those 18 hidden rubble
  triangles, and its collision block is identical.

Not done: not seen in a live match, as the editor is shared. The rubble round the first two is still plain boxes, and some sits against the plinth.

## Approved instrument details (2026-11-04)

- A folded steel rain hood protects the control panel, with a sloped top, downturned drip lip, side cheeks, mounting strip and bolts.
- Both meters have raised, tapered pointers beneath the centre bosses. Numbered scales and A/V unit markings replace the generic unnumbered faces.
  These are static decorative instruments; the voltage pointer reads about 440 on a 0-500 scale.
- One material and the existing atlas sizes are retained. The installed ModelDoc, material resource, conduit collider, map collision and three placements are retained.
  The `export-meshes` stage writes only the four OBJ mesh inputs while the editor is open.
- `run.ps1` builds and bakes in a hidden, idle-priority Blender process using two threads. Current work: `output/cabinet-instruments-20261104/work`.
  Paint with `paint_cabinet.py <work> <installed materials folder> cabinet`, then compile the installed material and model through the native editor.
- `verify_detail.py` checks every LOD's bounds, normals and UVs, all closed shells' outward winding, texture sizes, asset references and the three scene placements.
  Open shells with intentionally removed hidden faces are excluded from signed-volume checks. The current LOD 0 has 263 closed outward pieces and 23 open shells.
- Approved isolated engine views use identical cameras, light and texture-streaming settling to the original comparison. Current work and captures: `output/cabinet-instruments-20261104/work` and `after`.
  This pass has not been checked in live gameplay or benchmarked.
- Native full model/material compilation passed. An isolated load of the actual Sewage scene found all three cabinets with no error models; all nine door/conduit/clearance
  rays matched their expected results. Two map views confirm the hood under the existing lighting, including the catwalk location. The active Riverside scene and play
  state were preserved. Receipts and map captures: `output/cabinet-instruments-20261104/map-check/`.
- The user accepted this modest improvement and asked for more substantial changes to future models. The improved cabinet remains installed at the existing path for all
  three placements. Superseded original build files and the current before/comparison files were removed; the approved model and current build inputs were retained.
