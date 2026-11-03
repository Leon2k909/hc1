# Riverdale's fire hose reel cabinet v2

Created 2026-11-03. **Installed 2026-11-03** in all five places at the user's word, by `install_hose.py`. See `docs/notes/191`.

The old cabinet was `riverdale_hall.hose_cabinet`: a red box 1.4 in deep, a flat dark "window" with nothing behind it, a label strip and a chrome handle. It sat in the merged `riverdale_hall_detail.obj` and `riverdale_hall_fine.obj`, five times: the deck walls at (700, ±998.5), the north wall at (1998.6, ±680) and the south wall at (-198.6, -560), each 33 x 35 in with its bottom at z 28.5.

This one has the same face, 5 in deep:

- A red steel cabinet with a glazed door in a rubber bead, hinges and a lock. The paint's mottle and roughness come from `forestbase/scans/metal_plate_02` with its plate seams filtered out, plus wear where hands and knocks go.
- Behind the glass (its own translucent material): a reel of woven red hose on an open flange, the hose run off its top to a nozzle in a clip, and the brass inlet valve with a red handwheel, piped behind the reel to its hub.
- A "FIRE HOSE REEL" band with a reel pictogram, and small print on the bottom rail. Everything printed is made up.
- Triangles, LOD 0-2: 12,790 / 2,406 / 272. LOD switches 30 and 80. One 2048 atlas.

`hose_reel.py` builds and paints it with numpy and PIL, as `Sources/Riverdale/notice-board-v2/board.py` does. `compare_hose.py` renders old and new in the real map, in an isolated editor scene. The new one is shot on the bare wall 100 in along from the old (y -580), because the old box can't be hidden there and would show through the glass.

The cabinet's back is 0.4 in off the wall, in front of the hall's dado (0.25-0.3 in).

## The install

`install_hose.py` cut each old cabinet's faces from the live hall OBJs by position: `rv_hall_red` from the detail model (10 triangles a spot); `rv_window_dark`, the `hose_label` part of `rv_hall_signs` and the `rv_hall_chrome` handle from the fine model (14 a spot). It added the five models to the scene as a "Hose Reels" group with no collider, as the old box had none. `hose_cabinet` now only records a placement in `Tools/riverdale_hose_reels.py`, so a rerun of the map keeps them. Backups are in `output/asset-improvement-20261030/hose-reel/before-install/`.

`check_installed.py` waits for the hall to recompile and renders the north wall's east cabinet as the scene stands (`installed_*.png`): the new cabinet, with no trace of the old box. The other four weren't looked at.

Not seen in a live match.
