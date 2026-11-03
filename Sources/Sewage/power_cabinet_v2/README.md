# Sewage power cabinet v2

Created and **installed 2026-10-31**, at the user's word after an in-engine before and after ("Yes, install it"). See `docs/notes/177`. Sewage is a
live Zombies map (`MapInformation.ZombiesOnly`); Refinery, the other candidate, is in `GameUtils.DisabledMaps`.

The old cabinet was a flat box with eight bars on it, three times over in `sewage_details`. This one is a motor control cabinet: bolted frame,
hazard-striped plinth, two hinged doors with pressed louvres, an instrument panel with meters and pilot lamps, a red main switch, a lock rod with a
padlock, three floor conduits up its side into the roof, and a caged green status lamp. Blue-grey enamel over red oxide over steel, with about a third
of the paint broken by rust.

- Triangles: 21,610 / 10,840 / 5,204 / 1,832 (LOD 0-3, thresholds 30, 80, 180), against about 200 for the old box and its lamp.
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
