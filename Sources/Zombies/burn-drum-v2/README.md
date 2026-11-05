# Burn drum v2

Created 2026-10-30 and installed on Riverside the same day at the user's word ("yeah replace with new and do another"). Seen in s&box on 2026-10-31
in an editor capture with the map's real flames and light. The user's 2026-11-04 match screenshot exposed the fire-fit problem corrected below.

## Why this one

The wall-buy board was the weakest thing players see in Zombies. This is next. Burning drums are in Riverside's reference picture and
stand along the routes players run all match, but `riverside_parts.drum` makes each one a 14-sided cylinder in a flat tint, with rust
bands, a flat ember card and six glowing quads floating on its side for air holes (164 triangles). The other Zombies props are taken
or not seen: the ammo case and cash bag are another session's, and power-up drops are off.

## What it is

A 55 gallon drum made into a burn barrel:

- A sheet-steel shell with real wall thickness, rolled chimes, two rolling hoops, and dents that move both walls together.
- The lid chiselled out, leaving a jagged ring, and six air holes cut right through, so you see the hot inside through them.
- A lumpy ember bed with coals, and four logs charred into alligator skin, with heat in their cracks.
- Paint that browns and blisters as it climbs, then burns off to a dark scale. Soot rises from each air hole and over the rim, rust runs
  from under the hoops, and mud splashes up from the ground.
- Invented lettering: "WASTE OIL", "55 GAL LOT 3381".

One mesh and four models, for what the map uses: `burn_drum_blue` (4 on the map), `burn_drum_red` (3), `burn_drum_rust` (5) and
`burn_drum_cold` (2, with ash instead of embers).

## Numbers

- Triangles: 3,666 / 1,648 / 944 (LOD 0-2), against 164 and no LODs. 14 on the map. LOD 2 stays that high because at 444 the air
  holes' tunnels smeared into dark streaks up the side.
- One 2048 atlas layout, about 24 px/in on the outside. Four colour maps, roughness, metalness and normal for each of the two shell
  states (painted, rust), one AO and one glow mask. The glow is `F_SELF_ILLUM` with the mask at brightness 4.5. The old embers are 8.
- Same size as the old drum, same axes, origin on the ground at its axis. Radius 11.68 against 11.65, and 11.72 on LOD 1 and 2, as
  decimating moves points. Height 34.5. The bed is at the old height, 75% up, under where `MapFire`'s flames sit.
- No physics in the vmdls: the old hull (14 sides, radius 11.25) stays the collision.

## How it's installed

- `riverside_parts.drum` now keeps only the hull and the `FIRES` entry and records a placement, and `riverside_map.py` writes a "Burn
  Drums" group of 14 `ModelRenderer`s, each turned by the golden angle so no two show the same dents.
- **`riverside_map.py` wasn't rerun, because that isn't safe now.** An unmodified run changed the ground, levee and pad as well as the
  dressing, and reported paints with no material (`rv_steel`, `rv_yellow`, `rv_zinc`), because the shared kit has moved on since the map
  was last generated. So `install_drums.py` asks the map's code where the drums are, cuts exactly their faces from the checked-in
  `riverside_pad`, `_store` and `_dressing` OBJs (2,272 triangles), and adds the group to the scene.
- The OBJs only lost lines and the scene only gained them. The hull OBJs and the fires are untouched.
- To roll back: `git restore` those three OBJs, the scene, `Tools/riverside_parts.py` and `Tools/riverside_map.py`.
- `old_drum.py` cuts the before from `riverside_pad.obj`, so it now needs that file from before the install. Its result is kept in the
  work folder.
- `riverside_map.py --preview` and the map art no longer show drums, since the models aren't in its zone meshes.

## Files

- `Assets/models/zombies/burn_drum_v2/`, `Assets/materials/zombies/burn_drum_v2/`: the models and maps.
- `drum.py` builds, bakes and exports, with `drum_pack.py`. `paint_drum.py` paints. `old_drum.py` cuts the old drum out of
  `riverside_pad.obj`, reading only. `render_drum.py` and `make_sheets.py` make the comparison. `verify_drum.py` checks the files.
- Work files and renders: `output/asset-improvement-20261030/burn-drum/`.

## Checked and not checked

Checked, from the files (`verify_drum.py`):

- `check_outward.py` on LOD 0: 16 solid pieces, 0 inside out.
- Radius, height and ground contact of every LOD against the old drum, within 0.1 in.
- Every texture the vmats name exists, every file the vmdls name exists, the vmdls have no physics, and the cold one has no glow.
- On Riverside: 14 drums placed, all with existing models, the old drum faces gone, 12 drum fires still there, and the hulls unchanged.

Checked by eye, in Blender renders with backfaces made transparent as the engine culls them: the stencil reads the right way round,
and LOD 1 and 2 hold up from across the park.

In s&box 26.10.27c, in an isolated editor scene built from `riverside.scene`'s own moon, sky, fog, lights, fires and post-processing
(`Sources/Zombies/cooler-v2/capture_engine.cs.txt`, exposure held at 3.5):

- It holds up beside `MapFire`'s real flames, and the air holes glow. That capture showed one fault Blender hadn't, fixed since: the fire's light reached the
  drum's bare floor, which read as a pale patch through the holes, so the floor now burns like the walls.
- Collision, by rays against the compiled map (`collision_check.cs.txt` in the same folder): the top at z 130.5 and the side 11 in out, both metal.

The sheets sent to the user are Blender (Cycles, ACES 1.3) renders. Their night sheet's light and exposure are my estimate of the map's look.

**Not checked:**

- **An automated live-match check after the fire-fit correction.** Native captures hold exposure at 3.5 rather than using a player's settled auto-exposure.
- Whether the LOD thresholds (0, 20, 60, copied from the town house doors) switch at sensible distances.
- The old renders use the vmat's tints as sRGB, as `riverside_materials.py` writes them. If the engine reads them another way, the old
  drum's real colour differs a little from the sheet.

## Fire fit correction — 2026-11-04

The original `MapFire` profile placed roughly 37 in wide flame billboards on centres scattered across an 18 in square, and the wind
could push them farther out. This made the fire cross the 22.5 in drum's sides despite the emitter being above the coals.

`MapFire.OpeningRadius` and `OpeningHeight` now opt a contained fire into fitting its whole billboard inside a circular opening.
The 12 Riverside drum fires use radius 9.5 and rim height 7.59 above their existing emitter, Width 12, FlameHeight 30 and 18 flames/s.
`FlameParticles` keeps bases within that opening, holds crosswind off until their lower edge clears the rim, and keeps contained cards
upright. Depth feather is 1 instead of 8 to avoid a broad soft intersection with the drum. Distant contained fires retain their physical
height. Uncontained fires default to opening radius 0 and follow the previous controller path.

Applied and saved through native editor component tools, preserving other scene data and both cold drums. Generator settings updated
without rerunning the unsafe whole-map generator. Code hotloaded with zero compile errors. Front, side and above native sequences
checked; 24,646 particle samples with their bases below the rim had no opening escapes (maximum radial reach 8.75 in). No error models,
and the isolated captures preserved the user's scene and play state. This fix was not verified by an automated fresh match.

Work and receipt: `output/riverside/drum-fire-fit/`, including the pre-edit scene, `validation.json`, `compile-status.json`, before/after
captures and `comparison.png`. Rerun `rtk python Sources/Zombies/burn-drum-v2/fire_fix.py after` for captures and `... verify` for the
saved-scene comparison and sample checks. `fire_fix_sheet.py` lays out the unaltered screenshots with identical crops. The apply mode
uses native `set_component` and `save_scene` for persistence; if play is active, it also updates the runtime copies through the native
runtime-property tool. No drum meshes or collision hulls were changed.

## Fire realism refinement — 2026-11-04

The follow-up pass replaces the similarly tall, bright strips with mostly short flames and occasional taller tongues. A smooth burn
envelope varies emission and firelight together. Contained flames live a little longer, sway by up to four degrees, narrow and warm
as they fade, and use less additive intensity. The opening check accounts for the rotated billboard's full horizontal and vertical
extent, preserving the earlier rim fit. Open map fires and grenade flames keep their existing rendering path.

The twelve drum profiles now use 24 flames/s, 2 smoke puffs/s at size 48 and life 4.5, 2 smaller embers/s, and light brightness 2.2.
Smoke begins closer to the flame tips, rises more slowly and is less opaque. Tiny embers leave near the rim rather than spawning high
above it. Firelight sits closer to the fuel, with slower, less regular flicker. Width 12, height 30 and the 9.5 in opening are retained.
The generator retains these settings without regenerating the map.

Native profile application: `rtk python Sources/Zombies/burn-drum-v2/fire_realism.py apply` (only the twelve fires with a nonzero opening).
Capture: `rtk python Sources/Zombies/burn-drum-v2/fire_fix.py after drum-fire-realism`; verify with `fire_realism.py verify`, and lay out
the native before/after images with `fire_fix_sheet.py drum-fire-realism`. Work, code/scene snapshots and receipts are under
`output/riverside/drum-fire-realism/`. The saved scene comparison permits only those twelve profile edits. Animated front/side/above
captures were checked, including tilted-card containment. No new mesh, texture or collider was needed.

## Rooted fire replacement — 2026-11-04

The user still saw dancing, misplaced particles. The earlier controller kept changing each billboard's size, rolling it about its
centre, and ultimately lifting it off the fuel. The drum path now uses `Code/Maps/BarrelFlameParticles.cs`: seven continuous tongues
on the actual four logs, resolved through each drum renderer's world transform. Their feet stay fixed. There is no random relocation,
whole-card roll, lift-off or lateral wind drift. The native 64-frame flame sheet provides upward motion, with independent phases and
small smooth height variation. Its proportions are retained; sites near the wall produce smaller flames instead of thin stretched strips.

The entire horizontal billboard fits inside the opening. A shared 32 by 64 dynamic normal field supplies a restrained heat shimmer
above the rim, with distortion fading to zero at the edges. Twelve barrels share one field updated at most 25 times a second and use
one heat card apiece. The flame count is now fixed at seven per drum (84 total); `FlamesPerSecond` governs open fires only.
Existing opening settings enable this path automatically. No scene profile or map regeneration is needed. Open map fires and grenade
fire retain their existing emission path.

Native three-angle animation QA: `rtk python Sources/Zombies/burn-drum-v2/fire_rooted.py`. It checks attachment on all twelve drums,
stable roots across frames, full-width opening containment, refractive plumes, error models and preservation of the user's active scene
and play state. The old `fire_fix.py` particle measurements and `fire_realism.py verify` describe the superseded transient controller;
use `fire_rooted.py` for the current controller. Work and source snapshots: `output/riverside/drum-fire-rooted/`. The
`make_rooted_preview.py` helper makes a GIF and contact sheet from the native frames without recolouring them. Captures still use fixed
exposure 3.5; a fresh player match has not been automated.

Final native check: 12 controllers attached to the log models, 84 persistent fuel sites, 12 refractive plumes. Across 45,360 samples
from the three views, no billboard crossed the opening, maximum horizontal reach was 9.0 in against radius 9.5, maximum measured foot
drift was 0.0000153 in (float precision), and whole-card roll stayed zero. No error models or matching barrel errors in the console;
code compilation passed with zero errors. The capture preserved its source editor scene and play state.

## Playback correction after the clipping pass — 2026-11-04

The clipping pass removed the separate refractive heat card and raised contained-fire depth feather from 0.3 to 2 in, softening
intersections with the fuel and rim. A visual-version marker rebuilds the old transient objects on hotload. Five native camera angles
were captured under `output/riverside/drum-fire-clipping/fixed/`; the exact user viewport cutoff was not confirmed after desktop
control was stopped. The earlier heat-card description above records the previous implementation; the current controller has no heat card.

That pass also incorrectly fed frame units into the sprite renderer's normalized sequence phase. The user reported extremely fast
fire. The corrected phase is `(_time * (20 / 64) + phase / Tau) % 1`: 20 sheet frames/s, a full cycle every 3.2 seconds, with independent
normalized starting phases. The earlier comment claiming an unnormalized 64-unit renderer cycle was incorrect. Flame roots, geometry
and the clipping-pass depth feather remain in place. In the live Riverside editor, 16 samples across 1.555 simulation seconds measured
0.312502 normalized cycles/s, or 20.000156 sheet frames/s; every sampled phase stayed in [0,1). All twelve controllers were present,
and compilation completed without errors. Receipt: `output/riverside/drum-fire-speed/playback-validation.json`.
