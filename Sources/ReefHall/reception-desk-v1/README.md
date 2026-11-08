# Reef Hall lobby reception desk v1 — rebuild installed, old desk kept and revertable, 2026-11-06

**What:** the curved reception counter round the lobby's central tank (Reef Hall, `Aquarium` → "Lobby Reception Desk",
1 instance, world (0, 2420, 0)). The old desk was 16 flat facets (204 triangles) baked into the merged lobby render model:
a laminate top, a plain `rh_smooth` slab for a front with a 3 inch LED band stuck on it, and three black boxes for monitors.
It is the lobby's centrepiece, round the big tank, and is seen at eye level from anywhere on the lobby floor.

**New:** a standalone model, `models/props/reefhall/reception_desk_v1/reception_desk.vmdl`, same footprint (124 degree arc,
radius 212-250 in round the tank's centre, 42 in top):

* ten precast concrete panels, each in four smooth steps, V-joints between them, a recessed dark plinth, a shadow reveal
  under the top;
* a dark top 1.9 in thick with a rounded edge and a 1 in overhang;
* the warm LED band moved down onto the plinth recess (same `rh_led_warm` material and the same 3 inch height as the old
  strip; a first version made it 1.3 inch and that looked worse, see "Pictures");
* three monitors with keyboards and mice, cable grommets and a desk mat;
* three LODs (7,736 / 978 / 562 triangles), no physics: the old sixteen collision wedges stay in the lobby's collision model.

Nothing was deleted: the old geometry, the old lobby OBJ, the scene as it was and every new asset are kept, and
`revert.py` puts the old desk back (tested, see "Revert").

## Reuse first (user guidance, 2026-11-06)

| Part | Taken from |
|---|---|
| Precast and top surface | the project's existing Poly Haven CC0 `concrete_wall_009` scan: `materials/spillway/scans/concrete_wall_009_diff_2k.jpg`, `..._rough_2k.jpg` and `materials/collider/finish-v1/concrete_wall_009_nor_gl_2k.jpg` (already used by Spillway's wall vent and Collider). No new texture file was made; two small materials (`rd_precast.vmat`, `rd_top.vmat`) point at them with a tint that brings the warm scan to the map's cool grey. |
| Monitors | the approved control-room monitor (`Tools/reefhall_monitors.py`, `rh_monitor_*` materials), scaled 0.62 (a 45 in wall display becomes a 26 in desk screen) |
| Keyboards | the control-room operator keyboard (`Tools/reefhall_consoles.py`, `rh_console_*` materials), scaled 0.85 |
| Mice, desk mat, cable grommets | the approved office workstation (`Sources/ReefHall/office-desk-v1`) |
| Other materials | `rh_black`, `rh_led_warm`, `rh_steel`, `rh_pad_dark`, `rh_screen_data`: the map's own, remapped in the vmdl |

The desk body itself is new geometry. I looked for something to adapt and found nothing that fits: the existing shared desks
are straight (`models/props/shared/reception_desk_walnut_v1`, Veridant's 144 x 34 in walnut/limestone desk, 2,746 triangles;
`models/props/shared/operations_counter_v1`, a 334-triangle stone counter) and neither follows a 124 degree arc round a
cylinder, nor sits in this map's cool concrete/steel palette. A straight desk would also have changed the collision footprint.

## Numbers (`Tools/model_stats.py`, `stats_before.json` / `stats_after.json`)

KB = 1024 bytes, MB = 1,048,576 bytes. "shared" = a Reef Hall texture that other surfaces of the map already use, so it costs
nothing extra when this desk is drawn.

| | BEFORE (old desk, `old/old_desk.obj`) | AFTER (`reception_desk.vmdl`) |
|---|---|---|
| LOD0 triangles / vertices | 204 / 150 | 7,736 / 4,860 |
| LOD1 / LOD2 triangles (switch thresholds) | none: part of the lobby model | 978 / 562 (20 and 60: about 9.7 m and 29 m) |
| Materials / unique texture files | 6 / 14 (all shared) | 15 / 18 (15 shared; 3 scan files, see below) |
| Largest texture (px) | 1536 x 1024 (`rh_screen_telemetry`, shared) | 2048 x 2048 (the three scan files) |
| Total texture pixels (MP) | 11.27 | 23.72 (11.14 shared + 12.58 scan) |
| Est. GPU texture memory (MB, RGBA8 + mips) | 57.33 | 120.66 (56.67 shared + 63.99 scan) |
| Compiled `vmdl_c` / `vtex_c` total (KB) | none of its own (inside `reefhall_lobby.vmdl_c`) / 2,648 | 222.6 / 25,103 (22,122 scan + 2,982 shared) |
| Object size (in / m) | 150.7 x 62.0 x 441.8 / 3.83 x 1.58 x 11.22 | 151.9 x 60.4 x 443.2 / 3.86 x 1.53 x 11.26 |
| Instances -> total LOD0 triangles added | 1 -> 204 | 1 -> 7,736 (net +7,532: the lobby model lost its 204) |
| Collision | 16 wedge hulls in the lobby's collision model | the same 16 hulls, untouched; the new model has no physics |

The lobby render model went from 42,533 to 42,329 compiled triangles (OBJ faces 43,258 -> 43,054).

Textures, BEFORE (all `shared` Reef Hall atlases): `rh_laminate`, `rh_smooth`, `rh_led_warm`, `rh_black`, `rh_gunmetal`,
`rh_screen_telemetry` colour, and the `plain`, `smooth`, `gunmetal`, `screens` normal / roughness maps.

Textures, AFTER: shared: `rh_black`, `rh_led_warm`, `rh_pad_dark`, `rh_steel`, `rh_screen_telemetry` colour, the `plain`,
`pad`, `steel`, `screens` normal / roughness maps, and the control room's `consoles/rh_monitor_polymer` normal / roughness.
**New to Reef Hall's loaded set** (already in the project, shared with Spillway and Collider): the three 2048 x 2048
`concrete_wall_009` files. They are 64 MB of the 121 MB and 22 MB of the 25 MB compiled, so that is the real extra cost of
this desk. `model_stats` reports 0 B compiled for the shared roughness maps (it could not find a separate `vtex_c` for
them), in BEFORE and AFTER alike, so the compiled totals leave them out on both sides.

Texel density: the scan photographs 1.805 m (71 in), so at its native 2048 px the precast is **28.8 px/in**, below the
brief's 40 px/in guide. I kept the 2k files rather than make a bigger bake: 40 px/in would need 4k files for a surface that
is seen from 1 m or more.

## Checks

* Compiles clean (`reception_desk.vmdl_c`, both materials, the lobby model): no errors for reefhall or reception in the log.
* Collision is unchanged: `rays.py` casts 61 rays through the scene's physics world (down onto the top, level at 20 and
  60 in against both faces and both ends, level at monitor height, through the monitors) before and after: 61 identical
  hits, positions and distances (`rays_before.json`, `rays_after.json`).
* The live scene differs from the one before the install only by the new object (`old/reefhall.scene.before`). The editor's
  save also re-derives one id pair in each of two prefab-instance id maps (`team_deathmatch.prefab`, `bomb_defusal.prefab`):
  not an edit, the same noise as Riverside's watch-deck README describes.
* The generator side is switched too: `Tools/reefhall_reception_desk.py` (`ENABLED = True`) and a hook in
  `Tools/reefhall_map.py` leave the old desk's faces out of the lobby and add the scene object, so regenerating the map keeps
  the new desk. `equiv_check.py` builds only the lobby, offline, and shows face for face that flag off is the original lobby
  OBJ, flag on is the cut made here, and the difference is exactly the 204 triangles of `old/old_desk.obj`.
  Never run the whole generator on this map without looking first: it rewrites the scene and all merged room models.

## DECISION 2026-11-06: user approved the new desk and asked to delete the old one

`old/` (old desk OBJ, original lobby OBJ, scene backup) and `revert.py` were deleted. The old desk is no longer in the lobby model
or the scene; it can still be recovered from git history of `reefhall_lobby.obj`. The Revert section below is historical.

## Revert (tested, 2026-11-06; files since deleted)

```
python Sources/ReefHall/reception-desk-v1/revert.py --check     look, change nothing
python Sources/ReefHall/reception-desk-v1/revert.py             delete the scene object, put the original lobby OBJ back, flag off
python Sources/ReefHall/reception-desk-v1/install.py            put the new desk back (after a revert)
python Sources/ReefHall/reception-desk-v1/revert.py --delete-assets   also delete the new model and materials
```

`revert.py` takes `output/editor-lock`, brings Reef Hall to the front for a few seconds, deletes the "Lobby Reception Desk"
object and saves, then restores the front scene. It swaps `old/reefhall_lobby_original.obj` back only while the lobby OBJ is
still exactly what `install.py` wrote (sha256), so a later edit by someone else is never overwritten, and sets
`ENABLED = False` in `Tools/reefhall_reception_desk.py`. The scene's "unsaved changes" flag is not trusted: the editor's copy is
compared with `reefhall.scene` object by object first.

I ran it for real, then installed again:

* scene object deleted and saved; lobby OBJ = the original (sha256 `3ee4a27f8b1f...`, same bytes as `old/reefhall_lobby_original.obj`);
  the editor recompiled the lobby model back to exactly 42,533 triangles (and to 42,329 again after the reinstall);
* a native capture of the reverted state at the close pose (`reverted.png`) against `before.png`: same viewport, and in the
  rows that show the desk front and the floor (rows 200-454) 95 of 280,755 pixels differ, by at most 1 level out of 255. The
  rest differs only where the aquarium animates (`reverted_vs_before_diffx8.png`, difference x8). So the old desk was back exactly;
* the scene file after the revert has the same objects as `old/reefhall.scene.before` except that other sessions had edited
  Reef Hall meanwhile (Rotunda, Rotunda Bench 1, Tunnel, Tunnel Bench 1: the bench-clearance work, `reefhall_rotunda_bench_clearance.vmdl`).
  Those edits were in the editor's copy and the file before the revert started, so they were kept, not undone. `revert.py` now
  lists such differences by name instead of calling them a failure, and `install.py` no longer insists on the scene being
  byte-identical to the original (the first reinstall attempt stopped on exactly that, with nothing changed);
* the reinstall made a new scene object (guid `90902d9e-00b5-4858-a806-ceb20e37eb98`, written to `native-objects.json`).

`--delete-assets` was not run: it would delete the model I am delivering. I took `output/editor-lock` from `boxyard-model` at 19:20Z
after it had held it for 22 minutes (the brief's stale mark is 10) and after messaging that session; nothing was running and the
front scene was not Boxyard's.

## Pictures: matched BEFORE / AFTER from the real editor viewport (`output/model-trial-20261106/reefhall/`)

Method (the trial brief's rules): every picture is a native capture of the s&box editor's own Reef Hall viewport
(`screenshot_game`, a window capture of the editor, cropped to the viewport rectangle [428, 104, 1101, 455]). No temporary
camera, isolated scene, offscreen render, changed exposure or Blender render. The editor's own `set_editor_camera` puts the
viewport camera on the same three poses (`poses.json`, FOV 80) for BEFORE and AFTER, and `capture_set.py` checks that the
viewport rectangle is the same (`captures_after.json`: `rect_matches_before: true`). Before each AFTER picture the desk's 39
textures are requested at up to 2048 px (`MarkUsed(2048)`, only this model's materials), so no first-frame low mips show.
The editor draws its gizmos into the viewport (light bulb icons, the axes widget, the green camera line): they are in both
pictures. The aquarium water and fish animate, so those pixels never match.

| Pose | Where | BEFORE (18:36) | AFTER (19:58) | Difference x8 |
|---|---|---|---|---|
| close, public side | plan (-2167, -228, 60 in), about 2.3 m outside the desk front, looking at the front panels, the top and the nearest monitor; inside the 9.7 m LOD0 range | ![before](../../../output/model-trial-20261106/reefhall/before.png) | ![after](../../../output/model-trial-20261106/reefhall/after.png) | `diff_close_x8.png` |
| far, public side | plan (-2200, -472, 64 in), 13.2 m from the tank centre, the whole desk and the second tank; LOD1 is drawn here | ![before](../../../output/model-trial-20261106/reefhall/before_far.png) | ![after](../../../output/model-trial-20261106/reefhall/after_far.png) | `diff_far_x8.png` |
| staff side | plan (-2262, -75, 64 in), between the desk and the tank, looking along the top at two monitors | ![before](../../../output/model-trial-20261106/reefhall/before_staff.png) | ![after](../../../output/model-trial-20261106/reefhall/after_staff.png) | `diff_staff_x8.png` |

Files: `before.png`, `before_far.png`, `before_staff.png` and `after.png`, `after_far.png`, `after_staff.png` (1101 x 455 each),
in `output/model-trial-20261106/reefhall/`. The same folder holds `diff_close_x8.png`, `diff_far_x8.png`, `diff_staff_x8.png`
(`compare_images.py`, absolute difference times 8), `reverted.png` / `reverted_vs_before_diffx8.png` (the revert test above) and
`iteration1/` (the first AFTER set, see below).

What the difference pictures show: the desk (front panels, top, monitors, keyboards, the LED band and its floor glow) and the
animated aquarium water, plants and fish, plus a few of the editor's light-bulb icons. The floor, walls, stairs, other tanks
and other props in frame are unchanged. Mean absolute difference per channel / share of pixels that differ by more than 8 levels:
close 8.5 / 17.8 %, far 4.8 / 11.4 %, staff 6.1 / 14.2 %.

What the pictures show:

* Close: the old front is one flat blue-grey slab with a white strip at its foot and a black box for a monitor. The new
  front is panelled: V-joints between the ten precast panels, a concrete surface (hairline cracks, stains, small pits),
  a recessed dark plinth, and a dark top with a rounded edge and a small overhang. The monitor (its screen faces the staff, so
  the public side sees its back panel with vent slots) stands on a proper stand, and a keyboard and a mouse lie on the top.
* Far: the same silhouette and the same LED glow on the floor, as it has to be; what changes is the panel rhythm along the
  front, the lip of the top and monitors with a stand instead of black boxes. The gain at 13 m is real but small.
* Staff side: the old monitors were thick flat boxes on a short stub with the screen picture on the face and nothing on the
  desk; the new ones are thin screens on stands with a keyboard, a mouse and a desk mat in front of each, and the top reads
  as a thick rounded slab. The screens show the same telemetry picture the old monitors had (the map's `rh_screen_data` material).

Iteration history (kept in `iteration1/`): the first AFTER set had a 1.3 inch LED band. Beside the old 3 inch strip it was a
regression: the floor glow broke into a row of beads and the plinth looked starved. I changed the band to the old 3 inch height,
low on the plinth (`desk.py`: `LED_Z0, LED_Z1 = 2.4, 5.4`), rebuilt, recompiled (19:25Z), and retook all three AFTER pictures at
19:58Z with the final model; those are the ones above. `iteration1/` is evidence of the miss, not part of the result.

Capture housekeeping: the AFTER run took `output/editor-lock` at 19:57:51Z (after the Spillway session released it), found Reef Hall
already in front (nothing to restore but the viewport camera), put the viewport camera back to (-1350, 700, 25) / (7, -125, 0)
as found, left Reef Hall in front as found, and released the lock at 19:58Z. No play session was started and the capture run
does not edit the scene.

Verdict, honestly: **better where a player sees it, but expensive for one prop.** The front, top and monitors are
clearly improved at the distance a player walks past (2 to 3 m); the improvement at 13 m is modest. What it costs: 7,736
triangles at LOD0 against 204 (38 times, one instance); about 64 MB estimated GPU texture memory and 22 MB compiled for the
three 2k scan files (already in the project, new to Reef Hall's loaded set); a texel density of 28.8 px/in, under the brief's
40 px/in guide (I saw no softness in the pictures); and no collision of its own. The LED band looks about the same as before
(the upgrade is the body, not the lighting). If the cost is not wanted here, the cheapest savings would be in LOD0 detail and in
one of the three scan textures; I did not try either. The old desk is kept and `revert.py` puts it back.

## Files

Created: `Tools/reefhall_reception_desk.py`; `Assets/models/props/reefhall/reception_desk_v1/` (vmdl, three LOD OBJ/MTL);
`Assets/materials/reefhall/reception_desk_v1/` (`rd_precast.vmat`, `rd_top.vmat`); everything in this folder
(`desk.py` the generator, `preview.py`, `extract_old.py`, `equiv_check.py`, `rays.py`, `editor.py`, `install.py`,
`revert.py`, `capture_set.py`, `poses.json`, `old/`, `stage/`, the JSON results).
Changed: `Assets/models/maps/reefhall/reefhall_lobby.obj` (the 204 triangles cut, original kept in `old/`),
`Assets/scenes/maps/ReefHall/reefhall.scene` (+1 object), `Tools/reefhall_map.py` (the hook). Nothing committed or pushed.
