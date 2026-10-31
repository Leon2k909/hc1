# Orion tarp pile v2

Created 2026-10-31. **Not installed:** `Tools/orion_parts.py` and Orion's merged model still draw the old pile. The user decides from `output/asset-improvement-20261030/tarp-pile/tarp_pile_before_after.png`, which is rendered by s&box.

## Why this one

Candidates on Boxyard and Orion were rendered close up in the engine first. Boxyard's pipes and pallets are acceptable. Orion's `OP.tarp_pile`, by B3's corner in the yard, was the worst: a 14 x 10 grid of quads (280 triangles) pushed up into two peaks under a crinkly, glossy normal map, which reads as a mossy boulder rather than a tarp.

## What it is

An olive PVC tarpaulin thrown over a stack of gear. Its folds aren't modelled by hand: Blender's cloth solver drops a real-size 196 x 218 in sheet on the load, with the map's bollard beside it, and four moving walls tuck its hem in. Three yellow ropes hold it down, drawn taut over it with a shallow groove where they bear, each ending under a hessian sack. Panel welds, the hem, brass eyelets, corner patches, storage creases and the stencil are painted on the flat sheet, so they follow the folds. Its lettering is the map's own: ORN, GSE COVER 07. No bullet marks.

- Triangles: 18,124 / 7,611 / 1,650 (LOD 0-2), against 280 and no LODs. There is one on the map.
- One material and one 2048 atlas, about 8 px/in on the sheet. Two-sided (`F_RENDER_BACKFACES`), as it's one layer of cloth.
- Bounds: x +-60, y -62 to 68, z 0 to 61.6, against about +-40 x +-55 x 78 for the old one. It's lower, as a real load is, and its skirt spreads further at floor level.
- No physics. The old collision box, x +-32, y +-44, z 0 to 62.4, is what the load was built to fill, so it stays and cover doesn't change.

## What it changes in the map

- **It covers a bollard.** The bollard at plan (236, 40) stands 5 in outside the collision box's corner, so the cloth drapes over it and it can't be seen from most sides. It still collides. Moving the pile about 19 in away along its length would clear it, but that moves the cover, so it hasn't been done.
- Its skirt reaches past the collision box at floor level, with sacks 4 in high on it. Players walk over them with no collision. The corner nearest Fuel Processing's wall may touch it: the sim's -y wall stops short of the building, and nothing in the sim keeps a corner off it.

## To install

The prop is merged into `orion_props`, so it goes in as the red crates did (`Sources/Orion/red_crate_v2/install_map.py`):
- In `Tools/orion_parts.py`, `tarp_pile` keeps only its `m.oriented_box( ..., { "default": None }, surface )` and records a placement.
- In `Tools/orion_map.py`, add a scene object using `models/props/orion/tarp_pile_v2/tarp_pile.vmdl` at `K.to_world( ( 195, 0, 0 ) )` with `K.yaw_rotation( heading )`, where the heading is `math.degrees( math.atan2( 0.2, 1 ) )`.
- `oa_tarp` then has no triangles left in `orion_props`, so that slot goes. Other models' tarps are unaffected.
- Run `verify_tarp.py <root> installed` afterwards.

## Pipeline

`finish.ps1 -Stages sim,clay,build,bake -Paint -Export` runs it at idle priority. `capture_config.py` and `capture_compare.cs.txt` (through `sbox-cli --call run_csharp`) render old and new, and `make_sheet.py` makes the sheet.

| Step | Does |
| --- | --- |
| `tarp.py sim` | The cloth, at real scale in metres. Writes the settled sheet to `sheet_verts.npy` |
| `tarp.py clay` | Plain renders of its shape, to judge before spending a build |
| `tarp.py build` | Lays corners flat, smooths the solver's sawtooth, draws the ropes, thins the mesh, unwraps, LODs |
| `tarp.py bake`, `paint_tarp.py` | Bakes, then every map in numpy. The sheet's flat coordinates are baked too, so its welds and eyelets stay straight on the cloth |
| `tarp.py export` | OBJs, vmdl, vmat. Refuses if the UVs aren't the ones baked on |

Rerunning the build can change the unwrap, so bake and paint after it.

## Checked and not checked

Checked from the files by `verify_tarp.py`: 0 of its 10 solid pieces inside out; every LOD's normals agree with its faces, its UVs are in the atlas and it stands within its limits; every file named exists; no physics; Orion doesn't use it yet.

Checked in s&box on 2026-10-31: it compiled with no errors, no error models, and it was rendered off-screen in an isolated scene built from `orion.scene`, in Orion's own light at a held exposure, with the old slot hidden.

**Not checked:** a real match, so the player camera's look and walking over the skirt. Frame time. The LOD thresholds (0, 28 and 80, estimates) haven't been watched switching.

**Known and left:** the wall lamp beside it still lights one fold pale. Most of that was a specular glint, cut by making the coating more matte, and what's left is that fold facing a close lamp.

Orion's four tarped case blocks (`OP.drape`) still look like rock, with a jagged hem: they're a different model and weren't touched here.
