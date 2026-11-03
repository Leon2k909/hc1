# Riverdale's notice board v2

Created 2026-10-31 after the user pointed at the old one in s&box: "this needs to look better". **Installed on all 5 boards** at the user's word after comparing both ("Yes, install it"): see `docs/notes/185`. Nothing is committed.

The old board is a flat picture on a box: `riverdale_hall.notice_board` puts one 512 x 256 atlas image of plain rectangles on the front of a 36 x 24 x 1.2 in box.

This one has the same footprint, in real parts:

- An aluminium frame with a shaped profile and mitred bars, under moulded plastic corner keys.
- Cork made of grains and dark flecks, recessed behind the frame, with old pin holes and the pale ghosts of sheets long gone.
- 12 sheets that lift, curl and overlap, each its own grid with its own page in the atlas at 100 px/in, so the print can be read up close.
- Real push pins and brass tacks. A car-share flyer with tear-off tabs as separate strips, two already gone. Sticky notes held by their top strip. Two laminated signs that catch the light.
- Everything printed is made up, and the Open Day poster and toolbox talk use the map's own picture.
- Triangles, LOD 0-2: 3,818 / 142 / 10, against 14. LOD 1 and 2 use one 1008 x 672 picture of the whole board. LOD switches are 30 and 90, about 14 and 43 m.
- 4096 colour and normal, 2048 roughness, metal and AO.

`board.py` does all of it, with no Blender: the board is nearly flat, so its shadows come from a height field worked out in the script. `compare_board.py` renders old and new in the real map, in an isolated editor scene.

The cork is procedural, not a scan, because the project has no cork scan and agglomerated cork suits grains made this way.

## How it's installed

`install_board.py` cut the old faces from the live `riverdale_hall_detail.obj` (5 quads a board) and `riverdale_hall_fine.obj` (1 quad), and added the "Notice Boards" group to the scene: renderers only, as the old box had no collision. `Tools/riverdale_hall.py`'s `notice_board` now only records a placement in `Tools/riverdale_notice_boards.py`, so a rebuild keeps it.

| Engine position of the bottom centre | Yaw |
|---|---|
| (1205, 1000, 46) | -90 |
| (1205, -1000, 46) | 90 |
| (2000, -95, 46) | 180 |
| (1200, 670, 346) | 0 |
| (1200, -670, 346) | 0 |

Rollback: `output/asset-improvement-20261030/notice-board/before-install/` holds the two OBJs and the scene as they were, but other sessions change those same files, so check first. The script's edits are in `notice_board` and `write_scene`.

## Checked and not checked

The model was seen in s&box in an isolated copy of the real map, beside the old board, before the install (`compare_board.py`).

The install itself is checked from the files only (`verify_board.py`), because s&box had closed by then: the old faces are gone and nothing else changed, the OBJs are whole, the scene holds five boards at the old spots with the right yaw and no repeated ids.

**Not checked:** the hall's models hadn't recompiled, as that needs s&box open. Run `check_installed.py` with it open, which waits for the recompile and renders all five where the scene puts them. Not seen in a live match.
