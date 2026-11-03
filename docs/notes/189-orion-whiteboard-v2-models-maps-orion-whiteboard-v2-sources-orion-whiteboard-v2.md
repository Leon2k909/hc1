## Orion's whiteboard v2 (`models/maps/orion/whiteboard_v2`, `Sources/Orion/whiteboard-v2/`, 2026-11-03)
- Replaced the OPS room's whiteboard at the user's word after they saw both side by side ("ye install it").
- The old board was one picture on a quad (`OP.plate( m, "whiteboard", ... )`). The new one is a framed board with marker writing over the ghosts of wiped writing, a tray of markers and an eraser, and three sheets held by magnets. Everything written is made up.
- `orion_map.py` no longer draws the plate. `WHITEBOARDS` and `whiteboard_object` place the model, and `write_scene` adds it to the "Orion" object: a renderer only, as the old plate had no collision.
- Installed with `install_whiteboard.py`. It cuts the plate's two triangles from the live `orion_fuel.obj` and inserts the scene object into the text, so the map isn't rerun (see note 171). Backups are in `output/asset-improvement-20261030/whiteboard/before-install/`.
- Seen in s&box after `orion_fuel` recompiled (`check_installed.py`): the new board shows and the old picture is gone. Not seen in a live match.
