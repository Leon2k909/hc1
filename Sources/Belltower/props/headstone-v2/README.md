# Belltower churchyard headstones v2

Not installed: the map still draws its old stones, and no scene names these models. A compiled copy is in `Assets/models/props/belltower/headstone_v2/` and `Assets/materials/belltower/headstone_v2/`, for the in-game preview. These source scripts' first pass went on git in e2a67355, with the user's request to commit everything; the scan repaint and the Assets copy haven't.

`sheets/headstone-in-game-before-after.png` is the one to judge by: real in-game screenshots from one Belltower team deathmatch on 2026-10-31, same spot in each row. `match_shots.py` takes them. For the "after", the match's West Half renderer swaps to a temporary copy of the west half with the old stones' 288 triangles cut out (`preview_model.py`, in `Assets/models/compare_old/headstone-preview/`), and a new stone stands at each old stone's exact place and turn. Nothing is saved, and the map's files are only read. The other sheets in `sheets/` are Blender renders. The first in-game try, in `in-game/first-try-overlapping/`, stood new stones beside old ones and ran them into the churchyard wall.

Why this one: Belltower's churchyard has 38 stones, 19 in the west half and the same 19 mirrored in the east. Each old one is a plain box, or two boxes for a cross, in `compiler-safe/west/west_001_ashlar_grey.obj`, with a wall texture stretched across it and no lettering. 14 of the 19 are slabs of 26 to 31.5 in, and 5 are crosses.

The user's verdict on the first paint, procedural noise at 20 px/in: "new textures look low quality/pastel not hyper realistic". This version's surface is a real photo scan instead, the `medieval_blocks_03` set Belltower's walls already use, at its true scale. Over it go soot, rain runs, chipped edges, cut letters, sparse lichen and moss.

| Model | Height | Triangles, LOD 0-3 | Lettering |
|---|---|---|---|
| `headstone_arched` | 32 in, on a footing | 236 / 108 / 60 / 25 | IN LOVING MEMORY OF / EDITH ARDLEY / WHO FELL ASLEEP / 3 MARCH 1871 / AGED 62 YEARS |
| `headstone_shouldered` | 29 in | 226 / 110 / 62 / 28 | HERE LIETH / THOS. WENLOCK / OF THIS PARISH / DIED 1794 |
| `headstone_low` | 26 in, one broken corner | 182 / 88 / 52 / 13 | R. H. / 1832 |
| `headstone_cross` | 40 in, flat ring, stepped base | 596 / 314 / 172 / 44 | AT REST |

- The names and dates are invented.
- Each stone has its own grade of the scan: grey limestone, darker brown, warm sandstone, blacked grey.
- Origin on the ground at the middle, +X out of the inscribed face. Each goes 2 in into the ground so that it doesn't float on uneven grass.
- Collision per model is the old box for its kind: slab 6 x 22 x height, cross shaft 6 x 6 x 40, as the old arms had none. Surface `default`.
- One material: colour, normal and roughness at 4096, AO at 2048, metalness at 1024. About 41 px/in, the scan's own scale. That's a real memory cost for four small props, not measured in the engine; dropping to 2048 costs detail at about a metre.
- LOD switches at 30, 70 and 150 (about 14, 34 and 72 m), from the note on props at distance.

## Files

- `read_old.py` measures the old stones from the OBJ into `old_stones.json`. `scan_stone.py` quilts the scan into a clean sheet with no joints, from block faces marked by hand. `headstone.py` builds, bakes and exports. `paint_headstone.py` paints. `render_headstone.py` and `make_sheets.py` make the sheets. `verify_headstone.py` checks the files. `finish.ps1 [-Build]` runs them in order at idle priority.
- Toolkit: `Sources/Gameplay/capture-flag-v2/`'s `build.py` and `paint.py`, imported, not edited.
- Work files, renders, sheets and the export are in `output/asset-improvement-20261030/headstone/`. `headstone_v2/` there is laid out like Assets.
- Rerunning the build can change the unwrap, so bake and paint after it. The export refuses to run otherwise.

## Checked

In a real match: the material and four models compiled and loaded without errors, and all 19 west-half stones drew in the old stones' places with no old faces left showing, seen from six spots with the HUD and gun up. They read darker than in the Blender sheets, and darker than the map's tan walls and the old stones, mostly on faces in shade.

From the files, before copying them into Assets: `verify_headstone.py` passes. `check_outward.py` reports 0 inside out on LOD 0 of all four, and every texture and file the vmat and vmdl name exists.

In the renders: new stones stand at the old stones' measured places and yaws with the map's real west-half lawn, path, walls and ivy, loaded through the vmdl. The walls and ivy use only their colour maps, as Blender can't run the map's shaders, and the ground beyond the yard is a plain stand-in. The far view looks past the pieces cut off at the loaded region's edge, though their shadows stay.

## Not checked

- The east half's 19 mirrored stones: the preview only swaps the west half.
- Walking into them. The match's collision is still the old boxes.
- The smaller lines on the arched and shouldered stones are hard to read in the match at about 2 m, worst of all "WHO FELL ASLEEP", "3 MARCH 1871" and "AGED 62 YEARS".
- LOD switches haven't been watched, and no stone was seen from past about 7 m.
- The models' collision hasn't been tested. The old stones keep theirs in the merged model until an install cuts them, so an install has to use one or the other, not both.
- The scan's licence: `forestbase/scans/LICENSE.txt` covers that folder only. `medieval_blocks_03` was already in the project and shipping on the walls, and I didn't look for its own licence.

## To adopt it

Cut the old stones' faces from the OBJs the west and east halves really build from, by exact corner match, keep the collision, and place the models in the scene with renderers only, nearest height for each old stone. `Sources/Belltower/props/pew-v2/install_pews.py` and `Tools/belltower_pews.py` show the pattern.
