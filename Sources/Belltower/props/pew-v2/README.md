# Belltower church pew v2

Installed 2026-10-31 at the user's word after comparing both in s&box ("pew new better"). Nothing is committed. The old pews' faces are cut from the two OBJs `belltower_centre.vmdl` builds from, and the scene's "Church Pews" group places 12 models with renderers only. The old boxes stay in the merged model as their collision. `docs/notes/166-*` has how.

Why this one: each old pew is two boxes, a solid seat block and a slab, with plank scans laid across them. There are twelve in the church, which links the square
to the terrace, and the map script counts them as cover.

The new one is a panelled oak box pew: a framed front and back with fielded panels, a seat board with a rounded front edge, shaped bench ends with a boss, a moulded
top rail, tongue-and-groove on the seat side of the back, two hymn racks with books in them, two red seat pads and small brass plates. The front stays closed so
that what you see is still what the old collision blocks.

- Triangles: 5,000 / 2,500 / 964 / 366 (LOD 0-3). Twelve placed. Each old pew is 24 triangles.
- Same footprint: 100 long, 18 deep, 38 high. Three things stand outside the old boxes, with no collision: the hymn racks hang 3.3 in behind the back, the pads rise
  1.6 in above the seat, and the end bosses stand 0.5 in out from the ends.
- Collision is the old two boxes: the seat 18 x 100 x 18 and the back 3 x 100 x 20, surface `wood`.
- One material: colour, normal and roughness at 2048, metalness and AO at 1024. About 13 px/in.
- No lettering. The brass plates are blank.

## Files

- `pew.py` builds, bakes and exports. It began as the Veridant sofa's pipeline (`Sources/Veridant/sofa-v2/`) with its own geometry. `paint_pew.py` paints.
  `render_pew.py` and `make_sheets.py` make the sheet. `verify_pew.py` checks the files. `finish.ps1 [-Build]` runs them in order at idle priority.
- Toolkit: `Sources/Gameplay/capture-flag-v2/`'s `build.py` and `paint.py`, imported, not edited.
- Work files, renders, the sheet and the export are in `output/asset-improvement-20261030/pew/`. `pew_v2/` there is laid out like Assets.
- Rerunning the build can change the unwrap, so bake and paint after it. The export refuses to run otherwise.

## Checked

Seen in s&box in an isolated editor scene of the church (`output/asset-improvement-20261030/pew-sofa-shutter-check/`): 12 pews in their rows facing the altar, none failing to load, and no old faces showing. Rays in that scene stop on the old faces with surface wood (seat at X -458, back at X -443), and one down the aisle passes.

From the files, before installing: `verify_pew.py` passes: `check_outward.py` reports 0 inside out on LOD 0, bounds fit, the collision boxes are the old ones, every texture and file the vmat and vmdl name
exists, and the old merged model is unmodified with the twelve old pews' 288 faces in it. That model is in git LFS, so it's checked with `git status`, not against a
committed copy.

## Not checked

- Not seen or walked into in a real match. Rays are the only collision test.
- The LOD switches (30, 80, 180, about 14, 39 and 87 m) were set from the note on props at distance, and no switch has been watched.
- The hymn racks and seat pads stand outside the old boxes, with no collision of their own.

## To undo it

Git for `Tools/`, the two OBJs and the scene, or the originals in `output/asset-improvement-20261030/pew/before-install/`. `install_pews.py <root>` reports without writing, and refuses if any corner or count doesn't match.
