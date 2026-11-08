# Reef Hall straight stairs v1 — approved by the user and kept, old geometry and backups deleted, 2026-11-06

**What:** the straight flights of Reef Hall. Stage 1 is the lobby's two flights, scene objects "Lobby Stair N" (world 510, 2440, 0) and
"Lobby Stair S" (-510, 2440, 0) under `Aquarium`: 26 steps of 8 in climbing 208 in west from the foyer floor to the first-floor
west gallery, 280 x 180 in each, the first thing players coming out of the Red spawn walk up and the biggest dressing in the room
when you stand in the lobby. Stage 2 is the control room's flight (plan e 2666 -> 2380, n 770..900, 286 x 130 in, rail on one side).
The old flights were baked into the merged render models `reefhall_lobby` and `reefhall_control`. Per flight: 26 plain boxes (the
floor material on top, the dark wall material on the sides and risers), each with a flat 0.15 in brass strip box lying on its tread,
and a rail of 2.4 in square gunmetal posts under one 8-sided steel tube. 776 triangles per lobby flight (1,552 for both) and 700
for the control flight.

**New:** two standalone models, `models/props/reefhall/stairs_v1/lobby_stair.vmdl` and `control_stair.vmdl`. A closed-string stair on
the same footprint, step heights and run:

* treads in the floor's own slate finish, one slab per tread, with a chamfered 0.6 in nosing that overhangs a recessed riser by 1 in
  (a shadow line under every nose) and a brass anti-slip strip let into the tread;
* two 4 in kerbs (closed strings) that rise with the flight: their sloped tops carry the balustrade, the outer faces have a
  gunmetal plinth, a recessed concrete panel and a gunmetal stringer band, so the side of the flight is a clean diagonal instead of
  a stack of box ends;
* a closed end wall at the head with a plinth and two vertical reveals;
* the glass balustrade of the approved lobby balcony ([lobby-rail-v1](../lobby-rail-v1/README.md)) laid on the slope: stainless
  base shoe, 12 mm glass panels (about every 45 in along the slope), round posts with a collar and a cup under the rail, two clamps
  per post and side with cap screws, a 2 in round handrail with splice rings and domed ends. The handrail top is 34 in above the
  nose line, exactly the old rail hull's top, which is still the collision;
* three LODs per model (switch thresholds 24 and 70, about 456 in = 11.6 m and 1,330 in = 33.8 m), no physics: the generator's own
  step boxes and rail hulls stay the collision.

## Reuse first (user guidance, 2026-11-06)

| Part | Taken from |
|---|---|
| Every surface | Reef Hall's own materials, no new texture and no new material: `rh_floor` (treads), `rh_wall_dark` (risers, panels), `rh_gunmetal` (plinth, stringer band), `rh_brass` (inlay), `rh_steel` (posts, shoe, clamps, handrail), `rh_glass` (balustrade glass), `rh_black` (gasket slot, screws). |
| Balustrade | the approved lobby-balcony railing's parts and proportions, re-laid on the slope (the old model is a level run, so it could not be placed as it stands). |
| Geometry | new. The project's other stair work ([Veridant reception stair rail](../../Veridant/reception-stair-rail-v1/README.md), [Veridant court stair rail](../../Veridant/court-stair-rail-v1/README.md), [Ares stair landing rail](../../Ares/stair-landing-rail-v1/README.md)) is tube rails; none is a closed-string slate stair with a glass balustrade. |
| Building blocks | `Tools/map_kit.py` (`Model`, `write_obj`), `Tools/riverdale_parts.py` (posts, rings, domes), `reefhall_map.configure` for the material set. |

## Numbers (`Tools/model_stats.py`: `stats_before_lobby.json`, `stats_before_lobby_both.json`, `stats_before_control.json`, `stats_after_lobby.json`, `stats_after_control.json`)

KB = 1024 bytes, MB = 1,048,576 bytes. All textures are Reef Hall textures the lobby and control room already draw, so none of them
costs anything extra.

| | BEFORE lobby flight (one of two) | AFTER `lobby_stair.vmdl` | BEFORE control flight | AFTER `control_stair.vmdl` |
|---|---|---|---|---|
| LOD0 triangles / vertices | 776 / 426 (both: 1,552 / 852) | 4,326 / 3,054 | 700 / 370 | 2,454 / 1,836 |
| LOD1 / LOD2 triangles | none: part of the room model | 2,714 / 822 | none | 1,648 / 536 |
| Materials / unique texture files | 5 / 15 | 7 / 18 (LOD2: 5) | 5 / 15 | 7 / 18 |
| Largest texture (px) | 2048 x 2048 | 2048 x 2048 | 2048 x 2048 | 2048 x 2048 |
| Total texture pixels (MP) | 32.24 | 33.03 (`rh_black` adds 0.79) | 32.24 | 33.03 |
| Est. GPU texture memory (MB, RGBA8 + mips) | 164.00 | 168.00, none of it new | 164.00 | 168.00 |
| Compiled `vmdl_c` / `vtex_c` total (KB) | none of its own / 13,435 | 163.8 / 13,738 (shared) | none / 13,435 | 94.2 / 13,738 (shared) |
| Object size (in), length x height x width | 282.4 x 249.3 x 180.0 | 281.0 x 242.0 x 180.0 | 288.4 x 249.3 x 130.0 | 287.0 x 242.0 x 130.0 |
| Instances -> total LOD0 triangles | 2 (baked) -> 1,552 | 2 -> 8,652 (net +7,100) | 1 (baked) -> 700 | 1 -> 2,454 (net +1,754) |
| Collision | the generator's step boxes and rail hulls in the room's collision model | the same, untouched | same | same |

LOD0 is 5.6 times the old triangle count per flight (3.5 times for the control flight); LOD2 (822 / 536) is about what the old flight
cost. By the distance rule the foot of a lobby flight is LOD0 (4,326) and the other flight, 26 m away, LOD1 (2,714): about 7,000 in
view against 1,552. Each flight is also one more model with seven material draws; the old flights shared the room's draws. I did not
check which LOD the editor drew at each pose, and I did not measure frame time.

The lobby render model went from 41,825 to 40,273 compiled triangles (OBJ faces 42,550 -> 40,998), exactly the 1,552 old stair
triangles; the control-room render model from 135,904 to 135,204 (OBJ faces 136,036 -> 135,336), exactly the 700.

## Checks

* **Exactly the old stairs were removed, nothing else, and the collision is the generator's own** (`equiv_check.py`, offline). It
  builds all eight rooms with the new-stair flags off and on and compares them: the collision (boxes and hulls) is identical in every
  room (lobby 203 boxes / 107 hulls, control 122 / 41, the other six rooms are untouched), and the render triangles removed are
  lobby: brass 624, wall 520, gunmetal 240, floor 104, steel 64 = 1,552; control: brass 312, wall 260, gunmetal 60, floor 52,
  steel 16 = 700 (`equiv_check.json`, `ALL OK`).
* **Collision in the real editor scene is unchanged** (`rays.py`): 666 physics rays through the Reef Hall scene (26 treads x 5
  lines per flight, handrail hulls from above, rays across each flight at rail height, the head wall and the foot, and a grid of 143
  vertical rays over the lobby and 49 over the control room; 158 rays per flight, 192 in the grids). BEFORE and AFTER hit the same
  points with the same normals, ray for ray (`rays_before.json`, and `rays_after.json`, cast at the end with both stages installed):
  659 of the 666 hit something both times.
* **The scene** (`reefhall.scene`) has 696 objects against 693 in `old/reefhall.scene.before`: "Lobby Stair N" and "Lobby Stair S"
  (both `lobby_stair.vmdl`) and "Control Stair" (`control_stair.vmdl`), positions and models read back from the saved file, nothing
  removed.
* **Same exposure, same frame:** the capture rectangle was the same for BEFORE and AFTER (`rect_matches_before: true`), unchanged
  patches (a wall, the ceiling) have the identical mean luminance in both (29.8 / 29.8 and 66.4 / 66.4 of 255), and the tread tops
  are as bright as before (mean luminance 30.9 vs 31.7, 30.3 vs 30.0, 30.9 vs 28.8, 32.6 vs 29.5 on four patches), so the new
  stairs are not simply darker.

## Pictures: matched BEFORE / AFTER from the real editor viewport (`output/model-trial-20261106/reefhall_stairs/`)

Method (the trial brief's rules): every picture is a native capture of the s&box editor's own Reef Hall viewport (a window capture of
the editor, cropped to the viewport: x 428, y 104, 1101 x 455 px). No temporary camera, isolated scene, offscreen render, changed
exposure or Blender render. The editor's own `set_editor_camera` puts the viewport camera on the same poses (`poses.json`, FOV 80)
for BEFORE and AFTER (the camera position, angles and FOV the editor reported for each BEFORE capture equal its AFTER capture's to
0.01, for all 11 poses, and the reverted captures' equal BEFORE's), and `capture_set.py` checks that the viewport rectangle is the
same as BEFORE's (`rect_matches_before: true`). It keeps one log per label and a later run replaces it: `captures_after.json` and
`captures_reverted.json` hold only the control runs, the lobby AFTER run's console output is `captures_after_lobby_console.txt`, and
`captures_before_run1.json`, `captures_before_run2.json` and `captures_before.json` are the BEFORE runs in order. The editor draws
its gizmos into the viewport (light bulb icons, the axes widget, the green camera
line, the cyan reflection-probe frames): they are in both pictures of a pair. The aquarium water and fish animate, so those pixels
never match. No texture streaming request was made for either set. `pair_<pose>.png` puts the two unaltered captures side by side
(BEFORE left, AFTER right, captions added above); `diff_<pose>.png` is the absolute difference times 8 (`compare_images.py`).

| Pose | Where (plan coordinates e, n, z, inches) | Pair | Mean abs. difference / share of pixels over 8 levels |
|---|---|---|---|
| lobby_close_foot | on the lobby floor 110 in in front of the north flight's foot, eye 64 in up, looking up its centre line | `pair_lobby_close_foot.png` | 4.2 / 16.8 % |
| lobby_mid_side | 4 m south-east of the flight's foot, looking at its side across the foyer | `pair_lobby_mid_side.png` | 2.5 / 10.7 % |
| lobby_far | about 15 m from the foot, a corner of the lobby, looking at the flight | `pair_lobby_far.png` | 2.7 / 13.3 % |
| lobby_rail_close | at the foot, beside the flight's low-n rail, looking up along it | `pair_lobby_rail_close.png` | 3.2 / 13.3 % |
| lobby_south_close | the same as close_foot for the south flight (the same model, moved to n = -510) | `pair_lobby_south_close.png` | 4.7 / 18.9 % |
| lobby_top_down | from the west gallery, 64 in above its floor, looking down the flight at 45 degrees | `pair_lobby_top_down.png` | 7.8 / 21.8 % |
| lobby_head_west | west of the flight's head, 64 in up, looking east at its end wall | `pair_lobby_head_west.png` | 2.3 / 6.5 % |
| lobby_head_corner | the covered ground-floor area under the west gallery, looking at the end wall's corner and the flight's side | `pair_lobby_head_corner.png` | 2.8 / 5.7 % |

What the pictures show (looked at at full size and in 2x crops of the captures):

* **Close (close_foot, rail_close, south_close):** the old rail is one black tube on chunky square posts with nothing between them.
  The new one is a slim handrail on slim round posts with glass between them; the handrail runs along the same line (it meets the
  balcony rail at the same point). The old flight's side is a jagged stack of box ends; the new one is a closed string, a clean
  diagonal with a gunmetal band. The treads show the floor's grain and thin nosing highlights, and the brass inlay catches the lights
  in places. The tread tops themselves are a subtle change in this dark hall: their mean brightness is the same as before.
* **Mid-distance (mid_side), the clearest pair:** the old flight is a solid stepped block; the new one is a smooth slope with a
  plinth at the floor, the string band and the glass balustrade above, in the same style as the balcony rail above it.
* **12 to 15 m (far):** the silhouette is the same; the near side reads as a clean slope line instead of a stepped edge, and the rails
  are thinner with glass. The gain here is real but small.
* **From above (top_down):** the old lower treads are black in the BEFORE capture (the reverted capture below is pixel for pixel the
  same as BEFORE, so that is repeatable; I did not establish why those treads are black), the new treads are readable and the brass
  strips glint orange and green where they reflect the lights.
* **The head end wall (head_west, head_corner):** it is a large plain wall in both; the new wall has a dark plinth at its foot and two
  1 in reveals, which are barely visible under the editor's light icons. I would not count head_west as evidence of a change.

Where the whole-frame difference numbers in the table come from: they are mostly not the stairs. In `diff_lobby_far.png` the only
changed areas are the flight itself (string edge, rails, treads) and the animated aquarium tanks; floor, walls and ceiling are
black. 87 % of the differing pixels of the far pose lie outside the flight (the aquarium). The revert test below gives the noise
floor for an unchanged scene.

## Revert (tested on both stages, 2026-11-06; the old geometry and the backups are kept until the user decides)

```
python Sources/ReefHall/stairs-v1/revert.py lobby --check     look, change nothing
python Sources/ReefHall/stairs-v1/revert.py lobby             delete the two scene objects, put the original lobby OBJ back, flag off
python Sources/ReefHall/stairs-v1/install.py lobby            put the new stairs back (after a revert)
python Sources/ReefHall/stairs-v1/revert.py control           the same for the control flight (see below)
```

`revert.py` works under `output/editor-lock` (it waited 2.5 minutes while `spillway-model` held the lock): it brings Reef Hall to the
front only while the scene step runs, deletes the objects whose names start with the room's prefix ("Lobby Stair "), saves, and puts
the scene that was in front back. It swaps `old/reefhall_<room>_original.obj` back (sha256 checked), waits for the editor's own file
watcher to recompile the room model (nothing is force-compiled) and sets the generator flag in `Tools/reefhall_stairs.py` back to
False. The new models stay in `Assets/models/props/reefhall/stairs_v1` (nothing then uses them). `Tools/reefhall_map.py` needs no
change to revert: with the flags False it builds exactly what it built before (`equiv_check.py`).

I ran it for real on the lobby, then installed again:

* two objects deleted, scene saved (`Removed 2, Left 0, Saved True`); the live lobby OBJ is byte-identical to
  `old/reefhall_lobby_original.obj` (sha256 starts dd5a8629); the editor recompiled the lobby model back to exactly 41,825
  triangles in 5 s (and to 40,273 again after the reinstall);
* the 666 collision rays: identical to BEFORE (`rays_reverted.json`);
* native captures of the reverted state at four poses against BEFORE (`reverted_*.png`, `pair_reverted_*.png`,
  `reverted_vs_before_*_diffx8.png`): the old stairs are back. Mean absolute difference per channel / share of pixels over 8
  levels: close_foot 0.88 / 5.0 %, mid_side 0.90 / 6.3 %, far 2.57 / 13.9 % (the animated aquarium), top_down 0.00 / 0.0 % (pixel for
  pixel identical). That is the noise floor for the AFTER comparison: close_foot BEFORE vs AFTER is 4.2 / 16.8 %, mid_side 2.5 / 10.7 %.
* the first set of reverted captures came back completely black: the editor window had been minimized from the desktop (its
  rectangle was at -32000,-32000), and a minimized DirectX window captures as zeros. `window_state.py` now restores the window
  without activating it, puts it behind the other windows for the run and minimizes it again afterwards, and `capture_set.py`
  retakes any frame that comes back all black. The reverted pictures above are the retake.

## Stage 2: the control-room flight (`control_stair.vmdl`, scene object "Control Stair" at world 835, -2666, 0)

Installed the same way (`install.py control`): the 700 old stair triangles are cut from `reefhall_control.obj` (136,036 -> 135,336
faces), the editor recompiled the room from 135,904 to 135,204 compiled triangles in 6 s, one scene object added (696 objects),
`CONTROL = True`. The 666 collision rays are identical to BEFORE with both stages installed.

| Pose | Where (plan coordinates e, n, z, inches) | Pair | Mean abs. difference / share over 8 levels |
|---|---|---|---|
| control_close | 94 in beyond the foot, eye 64 in up, looking up the flight's centre line | `pair_control_close.png` | 3.3 / 9.7 % |
| control_side | 3.3 m to the open (low-n) side of the flight, looking at its side and rail | `pair_control_side.png` | 1.8 / 5.5 % |
| control_far | about 11 m away, looking at the flight with the spawn markers in front | `pair_control_far.png` | 0.9 / 3.1 % |

The same changes as in the lobby: the jagged boxed side becomes a clean sloped string and wall, the single tube on square posts
becomes a slim handrail on round posts with glass between them, the treads get grain and nosings. `control_close` is the weakest
picture: hundreds of the editor's light icons cover the lower half of the frame in both BEFORE and AFTER, so I would not use it as
evidence of anything but the head of the flight, where the new string and glass can be seen. `control_side` is the clearest: the old
jagged boxed side and single tube on square posts against a clean sloped string with glass bays between round posts. In `control_far`
(about 11 m, the spawn markers in front) it is the same change as a straighter, thinner silhouette: a small gain at that distance.

### Control revert (tested, then installed again)

* `revert.py control`: one scene object deleted, scene saved (`Removed 1, Left 0, Saved True`); the live control OBJ is byte-identical
  to `old/reefhall_control_original.obj` (sha256 starts a4644f17); the editor recompiled the room model back to exactly 135,904
  triangles in 6 s; generator flag `CONTROL = False`.
* The 666 collision rays: identical to BEFORE (`rays_reverted.json`; the lobby stairs were installed at that moment).
* Native captures of the reverted state against BEFORE: `control_side` is pixel for pixel the same (mean absolute difference 0.000,
  0.0 % of pixels over 8 levels), `control_far` 0.31 / 0.8 %, all of it the editor's light and spawn icons and a few thin edge lines
  (`reverted_vs_before_control_*_diffx8.png`, `pair_reverted_control_*.png`).
* `install.py control` again: 135,904 -> 135,204 compiled triangles in 5 s, 696 objects in the scene, and the 666 rays are identical to
  BEFORE with both stages installed (`rays_after.json`).

## Verdict (my own reading; the decision is the user's)

**An improvement at the distances where players meet these stairs, bought with a lot more triangles.**

* **Clear:** the lobby flights from 4 m and closer (mid_side, close_foot, rail_close, south_close, top_down, head_corner) and the
  control flight from the side (control_side). The stepped box side becomes a clean sloped string with a plinth and a band (in
  head_corner the jagged stepped silhouette against the aquarium window becomes a clean diagonal, and the end wall gets a dark
  plinth at its foot); the single black tube on
  chunky square posts becomes a slim handrail on round posts with glass between them, the same family as the lobby balcony rail above
  it; the treads show the slate's grain and nosing lines.
* **Small:** at 11 to 15 m (lobby_far, control_far) the silhouette is the same; the near side reads as a clean line instead of a
  stepped edge and the rails are thinner.
* **Weak or not evidence:** control_close (the editor's light icons cover the lower half of the frame in both pictures) and
  lobby_head_west (a wall under a cloud of light icons: no visible change). The end wall's plinth and two reveals are only just
  visible in the dark hall, best in lobby_head_corner.
* **Tread colour is a subtle change:** the mean brightness of the tread tops is the same as before, so the new stairs are not darker,
  but they are not obviously lighter either.
* **Cost:** LOD0 is 5.6 times (lobby) and 3.5 times (control) the old triangle count per flight: net +7,100 triangles in the lobby
  (+17 % of the lobby room's 41,825) and +1,754 in the control room (+1.3 % of 135,904). About 82 % of the new triangles are the
  glass balustrade. Each flight is also a model with seven material draws that the old flights, baked into the room model, did not
  add. LOD1 and LOD2 bring that down (LOD2 is about the old cost). I did not measure frame time.
* **Handrail height:** the new handrail's top is 34 in above the nose line, the same as the old rail's collision hull (unchanged).
  The old tube looked higher: its centre was 40 in above the nose line, so its top was about 41.6 in, which makes the new rail about
  7.6 in lower than the old one looked. If the higher look is preferred, `RAIL_DZ` in `stairs.py` raises it (render only: the
  collision stays at 34 in, as it was behind the old rail).

**Not verified:** a play session (nobody walked or fought on these stairs in a match: the collision is proven by 666 identical rays
through the editor scene and by unchanged generator geometry, not by driving a player up them); the in-game look (the pictures are
the editor viewport with its gizmos and the editor's own lighting, not the game camera with its tone-mapping, ambient occlusion,
bloom and vignette); which LOD the editor drew at each pose; frame time.

**Decision:** keep both stages, then I delete `old/` and `stage/` (the original room OBJ copies and the scene backup) and `revert.py`
stops working, as for the desk and the lobby rail; or revert either stage with `revert.py lobby` / `revert.py control` (both tested).

## Files

Created: `Tools/reefhall_stairs.py`; `Assets/models/props/reefhall/stairs_v1/` (`lobby_stair.vmdl`, `control_stair.vmdl`, each with
`_lod0/1/2.obj` and `.mtl`; the editor compiled the `.vmdl_c`); everything in `Sources/ReefHall/stairs-v1/` (this README, the builder
`stairs.py`, `install.py`, `revert.py`, `capture_set.py`, `window_state.py`, `make_pairs.py`, `preview.py`, `extract_old.py` (do not
re-run it after an install: it reads the room OBJs that the install has cut), `equiv_check.py`, `rays.py`, `split_old_flight.py`,
`compare_images.py`, `poses.json`, the json records, `captures_after_lobby_console.txt` and `stats_*.json`, `old/` backups, `stage/`
cut OBJs); the pictures in
`output/model-trial-20261106/reefhall_stairs/`.

Changed: `Assets/models/maps/reefhall/reefhall_lobby.obj` (1,552 triangles cut), `Assets/models/maps/reefhall/reefhall_control.obj`
(700 cut), `Assets/scenes/maps/ReefHall/reefhall.scene` (+3 objects), `Tools/reefhall_map.py` (the `stair()` / `stair_rail()` `draw=`
switches, the `reefhall_stairs` import and the scene hook; its diff also holds the earlier desk and rail trials' edits and other
sessions' work).

Nothing committed, nothing pushed.

## Status

Approved by the user ("yes good") on 2026-11-06. `old/` and `stage/` (the original room OBJ copies, scene backup and cut OBJs) are deleted, so `revert.py` no longer works; `install.py` is kept for reference. The generator flags in `Tools/reefhall_stairs.py` stay True.
