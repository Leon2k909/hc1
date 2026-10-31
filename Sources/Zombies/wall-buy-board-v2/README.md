# Wall-buy board v2

Created 2026-10-30 and installed the same day at the user's word ("ye install it") after a before/after.
`ZombiesRoundSystem.CreateStation` now loads it. **It hasn't been compiled or seen in s&box yet**, and until it compiles the station
logs a warning and builds the old board instead. Nothing is committed.

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
- Work files and renders: `output/asset-improvement-20261030/wall-buy-board/`.

## Checked and not checked

Checked, from the files (`verify_board.py`):

- `check_outward.py` on LOD 0: 143 solid pieces, 0 inside out.
- Every LOD stays inside the station's collider, and runs the old board's width and from the floor to its top.
- Every texture the vmat names exists, every file the vmdl names exists, and the vmdl has no physics.
- The game's code compiles with the swap: `dotnet build` of `Code/hc1.csproj`, 0 errors. `hc1.csproj` still names an old s&box path,
  so this needed the real one passed in through a temporary targets file, without editing the project.

Checked by eye, in Blender renders: the stencils read the right way round, the AK-105 sits 0.3 in off the saddles without touching
them, and LOD 1 and 2 have no cracks or floating parts from across a room.

Known weakness: the plank grain is stretched hard along its length, so within about 18 inches it looks soft and streaky (the padlock
sheet shows it). From where a player stands it reads as weathered timber. The two art passes the brief allowed were used up, so this
wasn't fixed. It's a paint-only change in `paint_board.py`: short, crisp pore marks across the grain, with no rebuild or rebake.

**Not checked:**

- **It has not been compiled or seen in s&box.** The user asked for this round to stay offline, so the editor, `sbox-cli` and the bridge
  weren't used. The sheets are Blender (Cycles, ACES 1.3) renders, not engine screenshots. Nothing in a match has loaded it, so the
  fallback may be what shows at first. An open editor may compile the files by itself, so look for `_c` files before repeating this.
- Whether the LOD thresholds (0, 20, 60, copied from the town house doors) switch at sensible distances.
- Other guns. The render has only the AK-105, placed by the station's own sums from its default parts. Its real in-game bounds may
  differ slightly if they count other bodygroups. A pistol is thinner, so it will stand further off the saddles. No pistol was measured.
- The saddles are a flat rail behind the gun, not hooks under it, because the guns differ too much for hooks to fit all of them.
  Nothing passes under the gun, so it looks held against the rail rather than resting on it.
