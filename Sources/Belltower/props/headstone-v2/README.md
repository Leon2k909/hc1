# Belltower churchyard headstones v2

Not installed. The export is outside Assets, nothing is committed, and it has never been compiled: there are no `_c` files. The sheets are Blender renders, not s&box.

Why this one: Belltower's churchyard has 38 stones, 19 in the west half and the same 19 mirrored in the east. Each old one is a plain box, or two boxes for a cross, in `compiler-safe/west/west_001_ashlar_grey.obj`, with a wall texture stretched across it and no lettering. 14 of the 19 are slabs of 26 to 31.5 in, and 5 are crosses.

The new set is four limestone stones in one atlas, with weathered edges, cut lettering, pale and ochre lichen in patches, and moss low down:

| Model | Height | Triangles, LOD 0-3 | Lettering |
|---|---|---|---|
| `headstone_arched` | 32 in, on a footing | 236 / 96 / 50 / 25 | IN LOVING MEMORY OF / EDITH ARDLEY / WHO FELL ASLEEP / 3 MARCH 1871 / AGED 62 YEARS |
| `headstone_shouldered` | 29 in | 226 / 100 / 54 / 28 | HERE LIETH / THOS. WENLOCK / OF THIS PARISH / DIED 1794 |
| `headstone_low` | 26 in, one broken corner | 182 / 78 / 46 / 13 | R. H. / 1832 |
| `headstone_cross` | 40 in, ringed, stepped base | 564 / 330 / 188 / 44 | AT REST |

- The names and dates are invented.
- Origin on the ground at the middle, +X out of the inscribed face. Each goes 2 in into the ground so that it doesn't float on uneven grass.
- Collision per model is the old box for its kind: slab 6 x 22 x height, cross shaft 6 x 6 x 40, as the old arms had none. Surface `default`.
- One material: colour, normal and roughness at 2048, metalness and AO at 1024. About 20 px/in. No metal.
- LOD switches at 30, 70 and 150 (about 14, 34 and 72 m), from the note on props at distance.

## Files

- `read_old.py` measures the old stones from the OBJ into `old_stones.json`. `headstone.py` builds, bakes and exports. `paint_headstone.py` paints. `render_headstone.py` and `make_sheets.py` make the sheets. `verify_headstone.py` checks the files. `finish.ps1 [-Build]` runs them in order at idle priority.
- Toolkit: `Sources/Gameplay/capture-flag-v2/`'s `build.py` and `paint.py`, imported, not edited.
- Work files, renders, sheets and the export are in `output/asset-improvement-20261030/headstone/`. `headstone_v2/` there is laid out like Assets.
- Rerunning the build can change the unwrap, so bake and paint after it. The export refuses to run otherwise.

## Checked

From the files: `verify_headstone.py` passes. `check_outward.py` reports 0 inside out on LOD 0 of all four, every texture and file the vmat and vmdl name exists, nothing is in Assets, and no `_c` file exists.

In the renders: new stones stand at the old stones' measured places and yaws with the map's real west-half lawn, path, walls and ivy, loaded through the vmdl. The walls and ivy use only their colour maps, as Blender can't run the map's shaders, and the ground beyond the yard is a plain stand-in. The far view looks past the pieces cut off at the loaded region's edge, though their shadows stay.

## The weak spot

The cross's ring is a thin round tube (`headstone.py`, 0.92 in radius). It reads a little like a hoop pushed through the arms, where a real one is a flat stone band. The brief allowed two art passes and both went on the paint and the first build, so it's left as it is. Changing it means a rebuild, bake and paint: `finish.ps1 -Build`.

## Not checked

- Never compiled or seen in s&box, and Cycles flatters.
- The lettering hasn't been read at game distance.
- LOD switches haven't been watched.
- The models' collision hasn't been tested. The old stones keep theirs in the merged model until an install cuts them, so an install has to use one or the other, not both.

## To adopt it

Copy `headstone_v2/` into Assets. Then cut the old stones' faces from the OBJs the west and east halves really build from, by exact corner match, keep the collision, and place the models in the scene with renderers only, nearest height for each old stone. `Sources/Belltower/props/pew-v2/install_pews.py` and `Tools/belltower_pews.py` show the pattern.
