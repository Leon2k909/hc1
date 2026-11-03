# Orion's whiteboard v2

Created 2026-11-03. **Installed 2026-11-03** at the user's word, by `install_whiteboard.py`. See `docs/notes/189`.

The old board is one picture on a quad: `OP.plate( m, "whiteboard", ... )` in `Tools/orion_map.py`, 105 x 60 in, in `orion_fuel.obj`, a few abstract lines and a circle on a grey border, 0.5 in off the north wall.

This one fits inside that footprint (104 x 58 in):

- A glossy board in an aluminium frame with plastic corner keys.
- Marker writing: the launch countdown, a go/no-go poll, an orbit sketch and notes, never quite solid, over the faint ghosts of wiped writing and eraser swirls.
- A marker tray holding four markers and an eraser.
- A ground-track printout, a checklist and a photo held by magnets. Everything written is made up, and the photo is the map's own picture.
- Triangles, LOD 0-2: 1,762 / 850 / 2. LOD switches 36 and 100. One 4096 colour and normal set, 2048 roughness, metal and AO.

`whiteboard.py` builds and paints it all with numpy and PIL, as `Sources/Riverdale/notice-board-v2/board.py` does. `compare_whiteboard.py` renders old and new in the real map, in an isolated editor scene. The new face stands 0.62 in off the wall, so it covers the old quad there.

## The install

Stopped `orion_map.py` drawing the `whiteboard` plate, and placed the model in the scene with no collider: engine position (823, -900, 340), yaw 180, the wall's face at x 823. The plate is in `orion_fuel.obj`, so its two triangles were cut from the live file rather than rerunning the map (see `docs/notes/171` on Orion's reruns).

Seen in s&box after the install (`check_installed.py`). Not seen in a live match.
