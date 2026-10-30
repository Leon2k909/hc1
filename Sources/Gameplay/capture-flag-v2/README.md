# Capture flag v2

Created 2026-10-30 on `asset/capture-flag-preview`. The user compared it with the old flag and told me to replace it, so
`DominationManager`, `HardpointManager` and `capture_point.prefab` now load it and `flag_pole_base` is gone from Assets.
Rollback: `output/asset-improvement-20261030/capture-flag/retired-flag_pole_base/`, and git history.

## What it replaced

`flag_pole_base` was the point model of Domination and Hardpoint (`DominationManager`, `HardpointManager`,
`capture_point.prefab`). It was a square white pole, a flat rectangle for a flag and three flat colours with no textures.
Two of its four meshes had no material and sat inside the others, so they fell to the vmdl's default and z-fought.

## What this is

A field mast as it would really be put up: weighted stand with gussets and weld beads, two-part telescoping mast with a
cam lever and index pin, three turnbuckled stays to staked foot plates held down by sandbags, a halyard over a sheave
cleated off with its spare coiled, and a flag on two snap hooks with a canvas heading strip, hems, tears and bullet holes.

- Same origin, same 102.6 height, flag flying along +X. Footprint grows from about 59 x 41 to 73 x 67, for the bags.
- Triangles: 31,910 / 15,712 / 5,814 / 894 (LOD 0-3). The old model is 3,436 with no LODs.
- Four materials: `cf_hardware` and `cf_soft` (2048, colour, normal, roughness, AO, plus metalness on the hardware),
  `cf_cloth` (2048 x 1024, alpha tested and two-sided), `cf_rope` (512, tiling). PNG sources total about 17 MB.
- Only `cf_cloth` takes `ModelRenderer.Tint`, as the old flag's material did, so team colours work without code changes.
- No third-party meshes or textures. Lettering is drawn with Windows' Bahnschrift. No game or brand markings.

## Pipeline

Run in this order. Blender 5.1, background, `-t 2`; every step here ran at idle priority beside a running game.

| Step | Does |
| --- | --- |
| `make_flag.py` | Fold shape, relaxed so the cloth keeps its length (Blender's wind can't fly a flag: see `sim_flag.py`, kept for that reason) |
| `sim_bags.py` | Drops seven bags into three piles with the cloth solver |
| `build.py` | All meshes, UVs at real scale and LODs, into `capture_flag_build.blend` |
| `bake.py` | Position, normal, finish and occlusion per texel |
| `paint.py` | Every texture, from those facts, in numpy |
| `export.py` | OBJs, vmdl and vmats |
| `verify.py` | File-level checks, and that the old model and its users are unchanged |
| `render.py`, `render_lods.py` | Matched comparison renders; the LOD sheet |

`check_outward.py` (run by `verify.py`) tests that solid parts face outward. Blender's renders are two-sided and hide it:
the first install had the mast and every other lathed part inside out until this caught it, before it was ever compiled.

Rerunning `build.py` can change the hardware's unwrap even with identical geometry, so always bake and paint after it.
`export.py` refuses to run if the UVs aren't the ones the textures were baked on.

Work files and renders are in `output/asset-improvement-20261030/capture-flag/`.

## Not done or not known

- **Never compiled or seen in s&box.** The user was playing, so the editor stayed closed. The images are Cycles renders of
  the exported files with ray-traced light, which flatter any asset. The real test is still to come.
- `switch_threshold`s (24, 60, 150) are an estimate from other models. Check them in the engine. The bags go angular at
  LOD 3 (a 2 x 2 grid); give them a finer grid if that LOD turns out to be seen closer than expected.
- The flag doesn't move. A wave needs a vertex shader or bones, and shaders can't be compiled offline.
- The model carries simple physics boxes, but the point managers only add a `ModelRenderer`, so players walk through
  it, as they do through the old one. The bags make that more noticeable.

## Still owed

Open the editor and let it compile; check the log, materials, LODs and team tint in a Domination and a Hardpoint match.
