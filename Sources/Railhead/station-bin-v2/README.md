# Railhead station bin v2

Created 2026-10-30. **Installed on the user's word the same day**, after seeing both side by side in s&box: all 29 of Railhead's bins. See `docs/notes/164-station-bin-v2-models-props-railhead-station-bin-v2-sources-railhead-station-bin-v2.md`.

The three-bay recycling bin on Railhead's platforms, concourse, booking hall and cab rank. The old one (`bin` in `Tools/railhead_furniture.py`, 280 triangles) is three boxes
with its door seams and slots drawn on as flat black strips. This keeps its size and hood line, so its collision box still fits, and builds them: doors in real pockets with a shadow
line round them, slots that go in, with a collar and a rubber flap cut into strips, triangular-key locks, hinges, riveted colour plates, a toe kick on a bolted flange, rails across the
back and a proper ashtray. The plates say what the old ones said (Papier, Verpackung, Restabfall). A cleaning label reads "RHD 0412", which is invented. No brands.

- Triangles: 7,628 / 2,723 / 1,138 / 435 (LOD 0-3), against the old 280 with no LODs. One material, one 2048 atlas, about 16 px/in.
- That's softer than the old stainless's 21 px/in, which tiles every 24 inches. This one doesn't repeat, and its wear is worked out for the shape.
- `station_bin.py` builds, bakes and exports. `paint_bin.py` paints. `render_bin.py` renders. `verify_bin.py` checks. `read_old.py` makes the old bin from the map's own code.
  `finish.ps1 -Old -Build` runs it all at idle priority and stops at the first step that fails.
- Work files and sheets are in `output/asset-improvement-20261030/station-bin/`. The fair comparison is `ingame/old-left-new-right.png` and `ingame/old-left-new-right-close.png`.

## Checked

- From the files, by `verify_bin.py`: 0 of 99 solid pieces inside out on LOD 0, within 0.05 of the old bounds, normals, UVs in range, every texture and mesh named exists, and no map asks for it.
- Railhead's scene has no material overrides and its dress models name the same `rw_stainless` the "before" render used, so that render has the right materials.
- Compiled by the editor on 2026-10-30 with no errors reported, and seen there beside an old bin on the island platform, placed by hand before the install.
- 29 bins found, each with exactly the old model's 280 triangles. The scene's diff adds 29 objects and only removes blank lines.
- Installed and seen in the editor on 2026-10-30: all 29 load, and on both island platforms, a third platform spot and the east footbridge the new bin stands in the old one's place, facing the right way, with no old one left inside it.

## Not checked

- Seen only in the editor, without the match camera's finish. Not seen in a match. Only four of the 29 were looked at, none in the booking hall or on the cab rank.
- LODs 1-3 haven't been seen in s&box. `switch_threshold`s (30, 90, 220) are estimates.

## How it was installed

`install_bins.py` cut the old bins out of `railhead_dress_centre`, `_east` and `_west` and added the scene's "Station Bins" group. But the `_east` and `_west` vmdls build from
`extinguisher-v2/east-base.obj` and `west-base.obj`, so `install_bins_published.py` made the same cut there, and that's what took effect. `railhead_props.bin` now keeps only the collision box
and records a placement in `Tools/railhead_bins.py`, so a full map run makes the same group. No full map run has tested that yet.

## Known weaknesses

- Full metal drew near black in s&box and 0.35 read as white paint, so the map is scaled to 0.68 at the end of `paint_bin.py`. It reads paler and less like stainless than the old bin.
- Its metal was tuned in sun on this one platform. Under the shed's shade or in the hall it may sit differently.
- Its collision box is the old one, 24.4 wide against the bin's 40.2, so bullets and players go through about 8 at each end, as they did with the old bin.
