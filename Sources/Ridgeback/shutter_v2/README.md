# Ridgeback town house shutter v2

Installed 2026-10-31 at the user's word after comparing both in s&box ("shutters new better"). Nothing is committed. `town_house.obj` has lost its `shutter_green` faces, and the prefab's "Shutters" group places 34 leaves with renderers only, as the old ones had no collision. `docs/notes/168-*` has how.

Why this one: Ridgeback, the battle royale map, has no truly standalone small props. Its town house is the map's one building, and its 34 shutters, all one flat box,
are the most repeated and most visible crude thing on it.

The new leaf is a louvred timber shutter in the same size and the same green: stiles and rails, 42 angled slats with a dark board behind them, two black strap hinges on
pintles, a pull ring, and a shutter dog holding it open. Old green paint, faded by the sun, is flaking off the slats and arrises to grey timber, and rust hangs below
the hinges.

- Two models, mirror images sharing one mesh's UVs and one atlas: `shutter_l` is hinged at +Y, `shutter_r` at -Y. A leaf's hinge goes on the side nearest its window.
- Triangles: 1,572 / 624 / 252 / 32 (LOD 0-3). 34 placed, against 12 each. The last LOD is a plain dark green leaf, for far off.
- Same size: the leaf is 25 x 64 x 1.5 in, standing on the wall's face at x = 0. Hinges, ring and dog stand off it: 2.3 in out from the wall, and 1.65 in past the leaf's
  free edge. The dog's foot goes 0.06 in into the wall.
- No collision, as the old shutters had none.
- One material: colour, normal and roughness at 2048, metalness and AO at 1024. About 27 px/in.

## Files

- `shutter.py` builds, bakes and exports. It began as the Belltower pew's pipeline (`Sources/Belltower/props/pew-v2/`) with its own geometry and export. `paint_shutter.py`
  paints. `render_shutter.py` and `make_sheets.py` make the sheet. `verify_shutter.py` checks the files. `finish.ps1 [-Build]` runs them in order at idle priority.
- Toolkit: `Sources/Gameplay/capture-flag-v2/`'s `build.py` and `paint.py`, imported, not edited.
- Work files, renders, the sheet and the export are in `output/asset-improvement-20261030/shutter/`. `shutter_v2/` there is laid out like Assets.
- Rerunning the build can change the unwrap, so bake and paint after it. The export refuses to run otherwise.

## Checked

Seen in s&box in an isolated editor scene of the house (`output/asset-improvement-20261030/pew-sofa-shutter-check/`): 17 of each leaf, none failing to load, hinges on the window side, and no old faces showing. Its ground and surroundings weren't loaded.

From the files, before installing: `verify_shutter.py` passes: `check_outward.py` reports 0 inside out on LOD 0 of both leaves, the leaf's height and depth fit the old one, the two are exact mirror images,
neither has physics, every texture and file the vmat and vmdl name exists, and the old model is unmodified with its 34 leaves of 1.5 x 25 x 64.

## Not checked

- Not seen in a real match, nor on Ridgeback's terrain.
- The LOD switches (25, 70, 160, about 12, 34 and 78 m) were set from the note on props at distance, and no switch has been watched.
- `shutter_r`'s mirrored normal map looked right in the engine at the distances checked, but wasn't looked at closely.

## To undo it

Git for `Tools/`, the OBJ and the scene, or the originals in `output/asset-improvement-20261030/shutter/before-install/`. The prefab's copy there also has the session's door change, so restore only its Shutters group. `install_shutters.py <root>` reports without writing, and refuses if a leaf doesn't fit.
