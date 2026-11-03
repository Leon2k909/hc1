# Railhead tyres v2

Created 2026-10-31. **Installed on the user's word the same day**, after seeing old and new side by side in s&box. See `docs/notes/176-stacked-tyres-v2-models-props-railhead-tyre-v2-sources-railhead-tyre-v2.md`.

The stacks of old tyres against Railhead's goods shed, three stacks on each side, 18 tyres in all. The old ones (`tyre_stack` in `Tools/railhead_dress_detail.py`) are 32-sided drums with rounded rims and black stickers for tread. These are real car tyres at the same size, 650 mm across and 205 mm tall, and hollow, so you can look down the hole
and see the liners. A high sculpt with real grooves, staggered blocks, shoulder lugs and sidewall ribs is baked onto a turned low mesh. Two tyres share one atlas: a used one, and a nearly bald one with fine sidewall cracks. Raised lettering gives only the type and size ("RADIAL TUBELESS", "205/65 R16", "STEEL BELTED"). No brands.

- Triangles: 4,320 / 1,672 / 624 / 224 (LOD 0-3), for each tyre. One material, one 2048 atlas, about 25 px/in round the tread and 47 across it.
- `tyre.py` sculpts, bakes and exports. `paint_tyre.py` paints. `capture_config.py` shoots old and new side by side in s&box, with `Sources/CerroBlanco/boulder-v2/capture_engine.cs.txt`. `finish.ps1 -Build` runs the build at idle priority and stops at the first step that fails.
- Work files and shots are in `output/asset-improvement-20261030/tyre/`: `draft1/` is the comparison. It needed no second pass.

## Checked

- `check_outward.py`: the tyre is one solid piece and right way out on LOD 0. Bounds match the old: 12.82 radius against 12.8, and 8.04 tall against 8.07.
- Compiled by the editor with no errors reported, and seen in s&box beside an old stack against the goods shed, in a hidden copy of the map's real scene with its sun, sky, fog and post effects. Exposure was held at one value so both match.
- After the install, in the same hidden copy, the stacks on both sides show only new tyres.

## Not checked

- Not seen in a match, or with the player camera's finish.
- LODs 1-3 haven't been seen in s&box. `switch_threshold`s (30, 90, 220) are estimates.

## How it was installed

`install_tyres.py` built each old stack with the map's numbers, cut 5,184 triangles a side from `extinguisher-v2/east-base.obj` and `west-base.obj` (what the dress models build from) and from the generator's OBJs, and added the scene's "Stacked Tyres" group, one model per tyre. `railhead_dress_detail.tyre_stack` now keeps only the collision box and records its tyres, so a full map run makes the same group, which hasn't been tested. `check_config.py` makes the check's shots.

## Known weaknesses

- The dust on the top tyre's sidewall is a little blotchy.
- The same two tyres repeat, turned, so a close look down a stack could spot it.
