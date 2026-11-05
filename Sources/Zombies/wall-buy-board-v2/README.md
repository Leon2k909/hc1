# Wall-buy board v2

Created 2026-10-30 and installed the same day at the user's word ("ye install it") after a before/after.
`ZombiesRoundSystem.CreateStation` loads it. The model and material were fully compiled through the native editor on
2026-11-04 and inspected in matched engine captures. The missing-model fallback remains available.

## Why this one

The old board is `models/dev/box.vmdl` (`materials/dev/primary_white.vmat`) stretched to 2 x 60 x 40 and tinted brown. It hangs
20 inches off the floor with nothing holding it up, the gun floats 5 inches in front of it, and every match has three. The other
candidates were stronger or aren't seen: the weapon crate is Poly Haven's `treasure_chest`, the workbench is the user's own model,
the ammo case and power-ups are another session's, and power-up drops are off (`DropPowerUps` is false and nothing sets it).

## What it is

An armoury rack that stands on the floor, so it works against a wall or free of one, as `TryPlaceStation` can place it either way:

- A welded steel frame on two foot plates with hazard paint, with braces, a low rail and a flat-bar X.
- Five bolted planks where the old board was, with grain, knots, rust running from the bolts and two stencils.
- A padded rail behind the gun, at the height and depth the gun is already centred on, so no gun code changes.
- A padlock on a vinyl cable off the rail's end, and a sign-out sheet on a clipboard, hung where a rifle's stock doesn't cover it.

All lettering is invented: "ARMS ISSUE", "CLEAR BEFORE RACKING", "SIGN OUT", "ISSUE RACK 60 LOT 4471".

## Numbers

- Triangles: 9,086 / 3,872 / 674 (LOD 0-2). The old board is a plain box with no LODs.
- One material, one 2048 atlas: colour, normal, roughness, metalness, AO. 25 px/in on the plank faces, about 15-19 on the steel, 80
  on the data plate, 58 on the sheet. The planks' backs get less, since they're rarely seen.
- Same axes as the old board (+X towards the player, Z up) and the same origin: the old board's centre, station (-4, 0, 40).
- Bounds, board-local: x -1 to 9, y +-30, z -40 to 20. The old board is x +-1, y +-30, z +-20. Its width and top are kept. The
  new model grows down to the floor and forward to the feet, and exactly fills the station's BoxCollider (10 x 60 x 60), which
  isn't changed. There's no physics in the vmdl, as the station's collider does that job.

## How it's installed

In `ZombiesRoundSystem.CreateStation`'s wall-buy case, the board's `LocalPosition` stays, and it loads this model at scale 1 with no
tint. If the model is missing or hasn't compiled, the same code falls back to the old box, scale and tint, as the workbench does.
So to roll back, delete the model's load and keep the fallback's three lines. Nothing else refers to the board.

On Riverside, the only map with hand-placed spots, the three wall buys stand on flat ground (pad z 96 and low ground z 0) with their
backs 1 in off the wall, going by `Tools/riverside_map.py`. Elsewhere `TryPlaceStation` picks the spot, so on sloping ground one foot
could float or sink, which the old board, hanging in mid-air, never showed.

## Files

- `Assets/models/zombies/wall_buy_board_v2/`, `Assets/materials/zombies/wall_buy_board_v2/`: the model and its maps.
- `board.py` builds, bakes and exports. `paint_board.py` paints. `render_board.py` and `make_sheets.py` make the comparison.
  `verify_board.py` checks the files. `run_idle.ps1` runs any of them at idle priority.
- Approved paint/build inputs: `output/wall-rack-detail-20261104/work/`; native captures: `after/`.
  Superseded build and comparison files and the gallery's OLD rack were removed after approval.

## Checked and not checked

Checked, from the files (`verify_board.py`):

- `check_outward.py` on LOD 0: 143 solid pieces, 0 inside out.
- Every LOD stays inside the station's collider, and runs the old board's width and from the floor to its top.
- Every texture the vmat names exists, every file the vmdl names exists, and the vmdl has no physics.
- The game's code compiles with the swap: `dotnet build` of `Code/hc1.csproj`, 0 errors. `hc1.csproj` still names an old s&box path,
  so this needed the real one passed in through a temporary targets file, without editing the project.

Checked by eye, in Blender renders: the stencils read the right way round, the AK-105 sits 0.3 in off the saddles without touching
them, and LOD 1 and 2 have no cracks or floating parts from across a room.

### Timber and lettering refresh (2026-11-04)

- Repainted from the existing geometry bakes: shorter knot-following grain, small pores, saw marks, and roughness/normal
  detail replace the strongest smeared bands. The weathered grey-brown palette and bolt stains remain.
- Removed the heavy horizontal cut through the sprayed lettering and reduced its source blur; ARMS ISSUE and
  CLEAR BEFORE RACKING now read as single lines instead of looking doubled.
- Uses the same meshes, LODs, UVs and 2048 atlas. Triangle counts, texture dimensions, station fit and gun placement do not change.
- Full native material/model compilation and offline asset checks passed. Matched whole-rack and close-detail engine
  approved captures remain in `output/wall-rack-detail-20261104/after/`; the active scene and play state were preserved.

**Not checked:**

- **A live match.** The current model and material have been compiled and rendered in an isolated native scene; a player
  walking up to a live wall-buy station still needs checking.
- Whether the LOD thresholds (0, 20, 60, copied from the town house doors) switch at sensible distances.
- Other guns. The render has only the AK-105, placed by the station's own sums from its default parts. Its real in-game bounds may
  differ slightly if they count other bodygroups. A pistol is thinner, so it will stand further off the saddles. No pistol was measured.
- The saddles are a flat rail behind the gun, not hooks under it, because the guns differ too much for hooks to fit all of them.
  Nothing passes under the gun, so it looks held against the rail rather than resting on it.
