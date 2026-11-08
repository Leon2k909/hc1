# Reef Hall lobby balcony glass railing v1 — rebuild installed and approved by the user, old backups deleted, 2026-11-06

**What:** the glass railing on the lobby's first-floor balcony (Reef Hall; 14 scene objects "Lobby Rail N 0..6" and "Lobby Rail S 0..6"
under `Aquarium`, section origins at world x +/-822, y 1940..2660, z 208): two runs of 840 in (21.3 m) over the lobby void, the
north run (plan n = 822) and its mirror on the south side (n = -822). Players on the balcony walk along it at eye level and everyone
on the lobby floor looks up at it. The old railing was baked into the merged lobby render model, 504 triangles for both runs. Per
run it was 15 square 2.5 in gunmetal posts, one 8-sided 3.2 in steel handrail tube and 14 flat zero-thickness glass quads, with no
fixings, no base and no glass edge.

**New:** two standalone models, `models/props/reefhall/lobby_rail_v1/lobby_rail_section.vmdl` and `lobby_rail_section_end.vmdl`
(the same plus the run's last post). A frameless-glass balustrade, same height (42 in), same 60 in post spacing, same footprint:

* a stainless base shoe 3.4 in wide with a chamfered top and a dark gasket slot the glass stands in;
* 0.5 in (12 mm) toughened glass panels with real edges, 57.6 in wide, one per bay (same `rh_glass` material as before);
* round stainless posts (10 sides at LOD0) with a base collar, a flared top and a cup under the handrail;
* two stainless glass clamps per post and side, each with a cap-head screw;
* a 2 in stainless handrail (12 sides at LOD0) in 120 in lengths with a splice ring at each joint and flat caps at the ends of the run;
* three LODs per model, no physics: the lobby's own collision boxes for the railing stay as they were.

Each model is a section of two bays (120 in), so the level of detail follows each section's own distance (a whole 21 m run as
one model would switch from its middle). Seven sections per run; the last one of each run is the `_end` model.

It was first installed with the old railing's faces, the original lobby OBJ and the scene as it was all kept, and a tested
`revert.py`. The user approved the new railing on 2026-11-06 and the old backups were then deleted (see DECISION).

## Reuse first (user guidance, 2026-11-06)

| Part | Taken from |
|---|---|
| Every surface | the map's own materials, remapped in the vmdl: `rh_steel` (posts, shoe, clamps, handrail), `rh_glass` (panels), `rh_black` (the gasket slot). Their textures are Reef Hall's own, already used by the lobby. **No new texture, no new material.** |
| Geometry | new. I looked for something to adapt among the existing rail work in this repo: [Veridant court stair handrail](../../Veridant/court-stair-rail-v1/README.md), [Veridant reception stair rail](../../Veridant/reception-stair-rail-v1/README.md), [Ares west stair-landing rail](../../Ares/stair-landing-rail-v1/README.md), [Riverside office porch railing](../../Riverside/office-porch-rail-v1/README.md), [Sewage pump-tower safety railing](../../Sewage/tower-rails-v1/README.md) and [Riverdale rail post fittings](../../Riverdale/rail-fittings-v1/README.md). They are tube stair rails, a timber porch rail, a tower guardrail and post sleeves: none is a 42 in frameless-glass balustrade on a 60 in post grid, so nothing could be reused as it stands. |
| Building blocks | the project's shared `Tools/riverdale_parts.py` helpers (`card`, `lathe`, `lathe_axis`) for the posts, screws, rings and flat parts, and `reefhall_map.configure` for the map's material set |

## Numbers (`Tools/model_stats.py`, `stats_before.json` / `stats_after.json` / `stats_after_end.json`)

KB = 1024 bytes, MB = 1,048,576 bytes. "shared" = a Reef Hall texture other surfaces of the map already use, so it costs nothing
extra when the rail is drawn.

| | BEFORE (old railing, both runs; was `old/old_rail.obj`, deleted after approval) | AFTER (`lobby_rail_section.vmdl` / `lobby_rail_section_end.vmdl`) |
|---|---|---|
| LOD0 triangles / vertices | 504 / 384 (both runs, 252 per run) | 634 / 412 per section; end section 866 / 562 |
| LOD1 / LOD2 triangles (switch thresholds) | none: part of the lobby model | 362 / 130; end section 478 / 170 (thresholds 20 and 60: about 9.7 m and 29 m from a section's origin) |
| Materials / unique texture files | 3 / 6 (`rh_gunmetal`, `rh_steel`, `rh_glass`; all shared) | 3 / 6 (`rh_black` replaces `rh_gunmetal`; all shared) |
| Largest texture (px) | 1024 x 1024 | 1024 x 1024 (`rh_steel`) |
| Total texture pixels (MP) | 6.29 | 3.93 |
| Est. GPU texture memory (MB, RGBA8 + mips) | 32.00 | 20.00 (none of it new: the lobby already draws all of it) |
| Compiled `vmdl_c` / `vtex_c` total (KB) | none of its own (inside `reefhall_lobby.vmdl_c`) / 1,722 | 30.1 + 38.3 = 68.4 / 1,431 (shared) |
| Object size (in / m) | 842.5 x 43.6 x 1647.2 / 21.4 x 1.1 x 41.8 (both runs as one mesh) | section 122.0 x 43.2 x 3.4 / 3.10 x 1.10 x 0.09; end section 123.4 long |
| Instances -> total LOD0 triangles added | 1 (baked) -> 504 | 14 (12 + 2 end) -> 9,340, net +8,836 (the lobby model lost its 504) |
| Collision | three collision-only boxes per run in the lobby's collision model | the same boxes, untouched; the new models have no physics |

What that means while playing (only sections in view are drawn, each one separately): standing mid-balcony the whole near run is LOD0
(6 x 634 + 866 = 4,670) and the far run LOD2 (6 x 130 + 170 = 950): about 5,600 triangles for the railing against 504 before.
From the lobby floor, both runs are LOD1: 5,300 triangles. At most 14 extra model draws of three materials each. These are the
counts the distance rule gives (19 in per threshold unit); I did not check which LOD the editor drew.

The lobby render model went from 42,329 to 41,825 compiled triangles (OBJ faces 43,054 -> 42,550).

The textures are all existing ones. The table's 32 -> 20 MB compares the two models' own material lists; it is not a change in
what the map loads (the lobby already loads all of these textures; I did not check whether anything else still uses `rh_gunmetal`).

## Checks

These were all run before the old backups were deleted (see DECISION).

* Compiles clean: both `.vmdl_c` (30,806 and 39,194 bytes) and the lobby model. `model_stats.py` counts 634 / 362 / 130 and
  866 / 478 / 170 triangles per LOD from the OBJs; in the editor the section's bounds are +/-1.7 in across the run and -62..60 in
  along it.
* Collision is unchanged: `rays.py` casts 314 rays through the Reef Hall scene's physics world, before the install, after it and
  after the revert. Per run: level rays at base, glass and handrail height and a wider set (33 stations each), 20 rays straight
  down, rays along the run from both ends and diagonal glass and handrail rays. The three sets are identical, hit for hit, position,
  distance and object name: 310 hit the "Lobby" collision object and 4 hit nothing every time (`rays_before.json`,
  `rays_after.json`, `rays_reverted.json`).
* The saved scene (`reefhall.scene`) has 693 objects against 679 in `old/reefhall.scene.before`: the 14 new "Lobby Rail" objects
  (names, positions and models read back from the file) and no other object added. The editor's save also rewrites prefab-instance
  id maps; that is noise.
* The generator side is switched too: `Tools/reefhall_lobby_rail.py` (`ENABLED = True`), `railing(..., draw=)` and the lobby's call in
  `Tools/reefhall_map.py` leave the old railing's drawing out of the lobby (its collision boxes are still built) and add the scene
  objects, so regenerating the map keeps the new railing. `equiv_check.py` builds only the lobby, offline: flag off is face for face
  the original lobby OBJ (43,054 faces), flag on is the cut made here (42,550), the difference is exactly the 504 triangles of
  `old/old_rail.obj`, and the lobby's collision hulls (107) and boxes (203) are identical either way. Never run the whole generator
  on this map without looking first: it rewrites the scene and all merged room models.

## DECISION 2026-11-06: user approved the new railing and the old backups were deleted

The user answered "yes new is better and do something else" to my question "Keep the new lobby railing?" (buttons "Keep, delete old"
and "Revert it", with the delete stated beforehand), so `old/` (`old_rail.obj` / `.mtl`, `reefhall_lobby_original.obj`,
`reefhall.scene.before`, `removed.json`) and `revert.py` were deleted. Before deleting, the live lobby OBJ was confirmed
byte-identical to `stage/reefhall_lobby_without_rail.obj`, the saved scene had its 14 "Lobby Rail" objects and `ENABLED` was True, so
nothing live depended on them. The old railing is no longer in the lobby model or the scene. It can still be recovered from git:
`HEAD:Assets/models/maps/reefhall/reefhall_lobby.obj` still has the original 43,258 faces (the old railing's 504 triangles and the
old desk's 204), and `railing()` in `Tools/reefhall_map.py` still draws the old railing when `Tools/reefhall_lobby_rail.py` has
`ENABLED = False`. `install.py`, `extract_old.py` and `equiv_check.py` are records of what was done and are not meant to be re-run
without the deleted files. The Revert section below is historical.

## Revert (tested, 2026-11-06, 20:52Z; `revert.py` and the backups since deleted)

```
python Sources/ReefHall/lobby-rail-v1/revert.py --check     look, change nothing
python Sources/ReefHall/lobby-rail-v1/revert.py             delete the 14 scene objects, put the original lobby OBJ back, flag off
python Sources/ReefHall/lobby-rail-v1/install.py            put the new railing back (after a revert)
```

`revert.py` works under `output/editor-lock`: it brings Reef Hall to the front only while the scene step runs, deletes the 14 "Lobby
Rail" objects (only those the install recorded; it stops without deleting if the count or ids differ), saves, and puts the scene
that was in front back. It swaps `old/reefhall_lobby_original.obj` back and sets `ENABLED = False` in
`Tools/reefhall_lobby_rail.py`. The models are left in `Assets/models/props/reefhall/lobby_rail_v1` (nothing then uses them).

I ran it for real, then installed again (20:52:08Z to 20:52:55Z):

* 14 objects deleted and the scene saved; lobby OBJ = the original (same bytes as `old/reefhall_lobby_original.obj`); the editor
  recompiled the lobby model back to exactly 42,329 triangles (and to 41,825 again after the reinstall);
* native captures of the reverted state at the three poses against the BEFORE pictures (`reverted*.png`,
  `reverted_vs_before_*_diffx8.png`): the old railing is back and the difference pictures are black except for the animated
  aquarium (mean absolute difference per channel: close 0.48, along 1.77, far 3.60 of 255; the share above 8 levels is
  2.6 / 8.8 / 19.7 %, which is the aquarium's own animation, so it is also the noise floor for the AFTER comparison);
* the 314 collision rays: identical to BEFORE;
* the reinstall made 14 new scene objects (guids in `native-objects.json`).

## Pictures: matched BEFORE / AFTER from the real editor viewport (`output/model-trial-20261106/reefhall_rail/`)

Method (the trial brief's rules): every picture is a native capture of the s&box editor's own Reef Hall viewport
(`screenshot_game`, a window capture of the editor, cropped to the viewport: x 428, y 104, 1101 x 455 px). No temporary camera,
isolated scene, offscreen render, changed exposure or Blender render. The editor's own `set_editor_camera` puts the viewport camera
on the same poses (`poses.json`, the editor reports FOV 80) for BEFORE and AFTER, and `capture_set.py` checks that the viewport
rectangle is the same (`captures_after_main_poses.json` and `captures_reverted.json`: `rect_matches_before: true`). The editor draws
its gizmos into the viewport (light bulb icons, the axes widget, the green camera line): they are in both pictures. The aquarium
water and fish animate, so those pixels never match. No texture streaming request was made for either set (see "Iteration history").

| Pose | Where | BEFORE (20:28Z) | AFTER (20:51Z) | Difference x8 |
|---|---|---|---|---|
| close | plan eye (-2400, 905, 272): on the balcony 2.1 m behind the north rail, eye 64 in above the balcony floor, looking at the rail diagonally down toward the east | ![before](../../../output/model-trial-20261106/reefhall_rail/before.png) | ![after](../../../output/model-trial-20261106/reefhall_rail/after.png) | `diff_close_x8.png` |
| along | plan eye (-2690, 905, 272): near the run's west end, 2.1 m behind the rail, looking east along it | ![before](../../../output/model-trial-20261106/reefhall_rail/before_along.png) | ![after](../../../output/model-trial-20261106/reefhall_rail/after_along.png) | `diff_along_x8.png` |
| far | plan eye (-2250, 330, 64): standing on the lobby floor 12.5 m south of the north rail, looking up at it | ![before](../../../output/model-trial-20261106/reefhall_rail/before_far.png) | ![after](../../../output/model-trial-20261106/reefhall_rail/after_far.png) | `diff_far_x8.png` |

By the distance rule the close pose draws the nearest sections at LOD0, the along pose LOD0 near and lower further away, and the far
pose LOD1; the pictures do not prove which LOD the editor chose.

AFTER only (no matched BEFORE, taken to check placement of both runs): `after_overview_north.png` (from 83 in behind the south rail,
looking north across the void at the north run, with the south run in the foreground seen from behind; the glass tank hides the middle
of the far run) and `after_overview_south.png` (the same from the north balcony). Both far runs read as continuous lines of posts and
glass across the void, with no section standing across the balcony; individual section joints cannot be told apart at this size. The
positions of all 14 objects were read back from the saved scene file (see Checks).

Files: `before*.png`, `after*.png` (1101 x 455 each), `diff_*_x8.png` (`compare_images.py`, absolute difference times 8),
`reverted*.png` and `reverted_vs_before_*_diffx8.png` (the revert test), `iteration1/` (see below).

What the difference pictures show: the railing (posts, handrail, base shoe, glass edges), the animated aquarium (water, plants, fish)
and a few faint spots where reflections in the glass and floor changed with the rail. The rest of the frame (walls, balcony floor,
stairs, other tanks, props) is black or near black. Mean absolute difference per channel / share of pixels that differ by more than
8 levels: close 2.96 / 10.0 %, along 3.18 / 12.0 %, far 3.27 / 17.6 %. In the far pose an unchanged scene already gives 19.7 % (the
revert test), so that number is mostly the aquarium.

What the pictures show:

* Close: the old posts are thick square black bars and the handrail a heavy black tube; the glass is a flat sheet with a thin dark
  strip at its foot. The new posts are slim round steel with a collar at the foot and a flared top under the handrail, with two clamp
  plates per post on each side of the glass; the glass stands on a wider, chamfered steel shoe that runs along its whole foot, and the
  handrail is visibly thinner. The gasket line and the screw heads cannot be told apart at this size.
* Along: the same at a glance: the near posts are slim round steel instead of chunky black squares and the handrail is thinner; toward
  the far end of the run the two pictures read alike.
* Far (12.5 m): the silhouette is the same. The old rail reads as a heavy dark band (thick handrail, black posts every 60 in); the
  new one as a thin handrail with slim posts. The glass looks the same. The gain at this distance is real but small.

Iteration history (kept in `iteration1/`): the first AFTER set (20:48Z) was wrong twice. 1. The sections stood across the balcony
instead of along it: `map_kit.Model` coordinates are plan (e, n, z) and the north run lies along e, but I had drawn the section with
"along" on plan y (my offline preview used the same frame, so it looked right). Fixed by turning the finished model a quarter turn
(`rail.py`: `turn_to_plan`), rewriting the OBJs and recompiling (identical bytes on a second explicit recompile). 2. That set was
taken after requesting 2048 px mips for the rail's textures (`MarkUsed(2048)`). These textures are shared with the lobby floor, and
the request made the floor show a tile grid that BEFORE does not have, so the pictures were not matched. The final AFTER set makes no
streaming request (`REEFHALL_NO_STREAM=1`; the rail adds no texture the lobby does not already show). `iteration1/` is evidence of
the miss, not part of the result.

Capture housekeeping: every capture run took `output/editor-lock`, opened Reef Hall's viewport, put the viewport camera back to
(-1350, 700, 25) / (7, -125, 0) as found, and released the lock. The BEFORE run found the editor's front scene named "Scene" and could
not bring it back afterwards (the log says "no session Scene"), so Reef Hall stayed in front; the AFTER, reverted and overview runs
found Reef Hall in front and left it there, and it is the front scene now (not playing). I waited about 17 minutes for the lock
(until 20:47Z) while `spillway-model` held it: its `owner.txt` kept being refreshed, so I did not take it over although the
directory's age passed ten minutes, and I sent it one courtesy message. No play session was started and the capture runs do not edit
the scene.

## Verdict, honestly

**Better where a player sees it, but modest, and expensive for a rail.** At 2 to 3 m the new railing is clearly improved: slim round
posts with real fixings, glass with real thickness standing in a base shoe, a thinner handrail, against square black bars and
zero-thickness glass. At 12.5 m the improvement is small (thinner posts and handrail, same silhouette). What it costs: about 5,600
triangles in view while standing on the balcony against 504 (11 times; 9,340 if all 14 sections were LOD0), 14 extra model draws, but
no new texture or material at all and 68 KB of compiled model. The collision is exactly as before. If the triangle cost is not
wanted, the cheapest savings are in LOD0 (the 10-sided posts, the screws) and a nearer LOD1 switch (thresholds 20 and 60 are not
tuned): I tried neither. Not verified: a play session (editor viewport only), which LOD the editor drew at each pose, any
frame-time effect (triangle counts only), and a matched BEFORE of the south run (its AFTER is only in the overview picture). The user
approved the new railing; the old backups and `revert.py` are deleted (see DECISION).

## Files

Created: `Tools/reefhall_lobby_rail.py`; `Assets/models/props/reefhall/lobby_rail_v1/` (two vmdl, six LOD OBJ/MTL, compiled files);
everything in this folder (`rail.py` the generator, `preview.py`, `extract_old.py`, `equiv_check.py`, `rays.py`, `editor.py`,
`install.py`, `capture_set.py`, `compare_images.py`, `poses.json`, `stage/`, the JSON results; `revert.py` and `old/` were deleted on
approval); `output/model-trial-20261106/reefhall_rail/` (the pictures).
Changed: `Assets/models/maps/reefhall/reefhall_lobby.obj` (the 504 triangles cut; the original is in git history),
`Assets/scenes/maps/ReefHall/reefhall.scene` (+14 objects), `Tools/reefhall_map.py` (the import, `railing(draw=)`, the lobby's call,
the scene hook). Nothing committed or pushed.
