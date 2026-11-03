# Orion tarp pile v2

Created 2026-10-31, and it replaced Orion's tarp pile the same day at the user's word ("Yes, install it"), after the before/after in `output/asset-improvement-20261030/tarp-pile/tarp_pile_before_after.png`, rendered by s&box. That sheet is from just before the bollard fix below.

## Why this one

Candidates on Boxyard and Orion were rendered close up in the engine first. Boxyard's pipes and pallets are acceptable. Orion's `OP.tarp_pile`, by B3's corner in the yard, was the worst: a 14 x 10 grid of quads (280 triangles) pushed up into two peaks under a crinkly, glossy normal map, which reads as a mossy boulder rather than a tarp.

## What it is

An olive PVC tarpaulin thrown over a stack of gear. Its folds aren't modelled by hand: Blender's cloth solver drops a real-size 196 x 218 in sheet on the load, with the map's bollard beside it, and four moving walls tuck its hem in. Three yellow ropes hold it down, drawn taut over it with a shallow groove where they bear, each ending under a hessian sack. Panel welds, the hem, brass eyelets, corner patches, storage creases and the stencil are painted on the flat sheet, so they follow the folds. Its lettering is the map's own: ORN, GSE COVER 07. No bullet marks.

- Triangles: 18,149 / 7,622 / 1,649 (LOD 0-2), against 280 and no LODs. There is one on the map.
- One material and one 2048 atlas, about 8 px/in on the sheet. Two-sided (`F_RENDER_BACKFACES`), as it's one layer of cloth.
- Bounds: x -60 to 61, y -62 to 68, z 0 to 61.7, against about +-40 x +-55 x 78 for the old one. It's lower, as a real load is, and its skirt spreads further at floor level.
- No physics. The old collision box, x +-32, y +-44, z 0 to 62.4, is what the load was built to fill, so it stays and cover doesn't change.

## What it changes in the map

- **It covers a bollard.** The bollard at plan (236, 40) stands 5 in outside the collision box's corner. The tucking wall can push the sheet through something that thin, so the build pushes the cloth back out into a bulge round it, and rays out of its sides and top confirm it's under the cloth. It still collides. Moving the pile about 19 in away along its length would clear it, but that moves the cover, so it hasn't been done.
- Its skirt reaches past the collision box at floor level, with sacks 4 in high on it. Players walk over them with no collision. The corner nearest Fuel Processing's wall may touch it: the sim's -y wall stops short of the building, and nothing in the sim keeps a corner off it.

## In the map

- `Tools/orion_parts.py`'s `tarp_pile()` writes only its old collision box and records a placement, and `Tools/orion_map.py`'s `tarp_pile_object()` puts the model in the scene with no collider.
- `install_map.py <root> <scratch> <backup> [--copy]` installed it, as the red crates' did: a scratch run, a comparison, and it cuts the old pile's 280 triangles from the live OBJ rather than copying the script's. The only scene change is 1 new object, `orion_props` lost only `oa_tarp`, and its collision lines are unchanged. 0 problems in 93 spots, none cut off.
- Rollback: `output/asset-improvement-20261030/tarp-pile/before-install/` holds the model's files and the scene as they were. The old material stays in Assets, as other tarps use it.
- `capture_compare.cs.txt` compares old and new by hiding the `oa_tarp` slot, so it only works on the files in `before-install`.

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

Checked from the files by `verify_tarp.py <root> installed`: 0 of its 10 solid pieces inside out; every LOD's normals agree with its faces, its UVs are in the atlas and it stands within its limits; every file named exists; no physics; Orion uses it.

The build checks itself: every ray out of the bollard's sides and top meets the cloth, and no edge of the sheet is over 14 in (the solver leaves 2.7, flattened corner flaps about 8, and a sheet dragged across the pile 50 or more).

Checked in s&box on 2026-10-31, in an isolated scene built from `orion.scene` in Orion's own light at a held exposure (`Sources/Boxyard/ibc_tote_v2/check_config.py` and `capture_installed.cs.txt`):
- It compiled with no errors in the log, and there are no error models.
- It stands at the old pile's place and turn with no collider of its own. It was seen from five sides and the top with no holes, and the bollard doesn't show through.
- Rays with a clear path stopped exactly on the old collision box, on surface plastic, at +x, -x and +y. The -y ray started inside Fuel Processing's wall, so that face wasn't tested.
- The open `orion` tab had no unsaved changes, so it was reloaded, because a stale tab would have overwritten the scene if saved.

**Not checked:** a real match, so the player camera's look, walking over the skirt, and how the fold near the lamp looks in play. Frame time. The LOD thresholds (0, 28 and 80, estimates) haven't been watched switching.

**Known and left:** the wall lamp beside it still lights one fold pale. Most of that was a specular glint, cut by making the coating more matte, and what's left is that fold facing a close lamp.

Orion's four tarped case blocks (`OP.drape`) still look like rock, with a jagged hem: they're a different model and weren't touched here.
