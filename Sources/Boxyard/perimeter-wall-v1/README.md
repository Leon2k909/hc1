# Boxyard perimeter wall v1 (boxyard-model session, 2026-11-06)

**Status: installed in the live scene, not committed. The old wall is kept and `revert.py` puts it back (tested).**

The yard's perimeter wall (four runs round the whole yard, seen from every route) rebuilt as real models: 28 board-formed concrete
panels and 28 concrete piers with galvanised brackets and barbed wire = **56 instances** in `Assets/scenes/maps/Boxyard/boxyard.scene`
(group "Perimeter Wall" under the "Boxyard" root, draw-only). The old wall was three paints baked into the yard's merged render
model (28 flat panels, 32 near-black posts, 8 wire strands); its faces are cut from `boxyard_yard.obj` and kept in `old_wall.obj`.

## Pictures (native editor viewport, matched)

`output/model-trial-20261106/boxyard/`: `before.png` / `after.png` (close), `before_far.png` / `after_far.png` (about 12 m back),
`before_lane.png` / `after_lane.png` (grazing view down the north lane). Each pair was captured back to back, in the same
1102 x 455 viewport (the editor's dock layout changed during the work, so the first BEFORE set was retaken together with the AFTER set),
with the Boxyard tab's real viewport camera at the same pose, the same lighting and post settings, and the new textures streamed
(`MarkUsed` 2048 on this model's materials only). Poses (engine units, FOV 80): close (690, -430, 64) pitch 6 yaw 32; far (352, -401, 64)
pitch 4 yaw 12; lane (700, 700, 64) pitch 0 yaw -80. Editor gizmos (spawn figures, icons, axis widget) are part of the native view.
`final_check.png` is the close view taken again after the last reinstall (mean difference to `after.png` 0.4 / 255).

## Why this prop, and what was reused

The old wall is the biggest crude thing in the yard: flat slabs with two shallow ribs, a blurry 2048 px texture stretched over
about 240 in (about 8.5 px/in), and posts that render almost black. Nothing existing fits a wall (no wall or fence model in
`Assets/models/props/**`, other maps' walls are baked into their merged models), so the models are new, the **textures are reused**:

| Used for | Source | Status |
|---|---|---|
| field, coping, piers (colour, roughness) | Spillway's committed Poly Haven `concrete_wall_009` 2k scan (CC0), `Assets/materials/spillway/scans/concrete_wall_009_{diff,rough}_2k.jpg`, referenced as they are | shared with Spillway |
| field normal | `materials/boxyard/perimeter_wall_v1/pw_concrete_normal.jpg`, a byte copy of the OpenGL conversion the Collider finish made (`materials/collider/finish-v1/concrete_wall_009_nor_gl_2k.jpg`), copied so nothing dangles if that trial is reverted | copy |
| plinth and first course | `pw_base_{color,normal,rough}` 2048 x 1024, cut from the same scan (four board-row windows made seamless) and weathered the way the old foot was (rain-splash dirt and sparse moss multiplied onto the scan, so its pores and streaks still show) | new, derived from the scan |
| steel brackets and wire | the map's existing `materials/boxyard/bx_galv.vmat` | shared (existing Boxyard material) |

Texel density: 48 in of wall = 2048 px, **42.7 px/in** (old about 8.5 px/in); both new materials carry a slight cool tint
(0.93 0.96 1.0) over the scan. The new field is
cleaner than the old one's faint rain streaks, but the dirty, mossy foot is kept; mean brightness of the wall is about 4 % lower than the
old one's in all three views, so it is not paler.

## The models (`Assets/models/props/boxyard/perimeter_wall_v1/`)

Inches, engine axes (x along the wall, y out of the yard, z up); instances only need a yaw (East 180, West 0, North -90, South +90).

* `perimeter_panel_{a,b}_v1` 228.57 in pitch (north and south runs, a/b alternate), `perimeter_panel_{c,d}_v1` 240 in pitch (east and
  west runs). 8 in thick, 128 in high like the old wall. Yard face: 8 in plinth with a 1.2 in weathering chamfer, 16 in first course
  (the dirty zone to z = 24), six 16 in board courses separated by V grooves (0.6 in half width, 0.5 in deep, LOD0 only), then an 8 in
  coping slab with a 1.5 in overhang and chamfered top. Back face: one plain sheet. Texture windows are random per 45 in bay.
* `perimeter_pier_{a,b}_v1`: 12 x 12 in shaft with 1 in chamfers on an 8 in base block, a cap with 0.8 in overhang and chamfered
  edges to z = 140, a steel base plate (four bolts), stem and two V arms to z = 160 that carry two wire strands per bay
  (2.5 in sag, barbs every 10 in).
* LODs per model (switch thresholds 0 / 36 / 110): LOD1 drops grooves, bolts and barbs and merges bays; LOD2 drops wire and bracket
  and the chamfers. No collision on the new models: the yard model keeps the wall's boxes.

## Install, collision and what the generator does

* `install.py` cuts the old wall's faces out of `boxyard_yard.obj` (and writes its mtl/vmdl the way the generator does: only the
  three wall paints' entries drop; the five collision boxes stay) and adds the 56-instance group to the scene. `Tools/boxyard_map.py`
  does the same on a regeneration (`wall_objects()`, `OLD_WALL_IN_YARD = False`); `verify_generator.py` proves it reproduces the
  installed scene group and the cut OBJ exactly.
* **Collision unchanged.** 48 physics rays in the editor scene (4 walls x 4 positions x z 30 / 100 / 140, `rays_and_lines.cs`) hit
  the same objects at the same positions before and after (0 differences): "Yard" at |n| = 830 / |e| = 798 for z 30 and 100, the
  map's "Player Clip" boxes at z 140. No collider sits under the new group (47 colliders in the scene both times). The collision boxes'
  yard faces are 2 in in front of the old visual face; the new piers project 2 in toward the yard, exactly to that plane (their caps
  0.8 in more, above the 128 in boxes), so nothing visible sticks out past where a player can stand. Nothing a bot or a player touches
  has changed. The wall body is 128 in high as before (the coping); the wire and brackets are 20 in higher than the old wire (160
  against 140), and the old wire had no collision either.

## LOD review (editor viewport, same north-wall bay on one clear line at 12 / 17.4 / 20 / 30 / 40 m)

`lod/` has the 20 captures (engine's own choice, and LOD0 / 1 / 2 forced with `ModelRenderer.LodOverride` on the 56 renderers, put back
to null afterwards: none left, checked), `lod_sheet2.png` is the contact sheet. The lines of sight were found with scene traces
(`rays_and_lines.cs`) because containers block most of the yard at eye height. Findings:

* This viewport is 1102 px wide at FOV 80, and the engine's LOD switch follows pixel size, so the thresholds act at about 13 in per unit
  here (the project's 19 in per unit is for 1920 x 1080 at FOV 90): LOD1 starts at about 12 m and LOD2 at about 36 m in the editor
  view, i.e. about 17 m and about 53 m in a 1920 px, FOV 90 game view. (Wire-band comparison of the engine's choice against each forced
  LOD: LOD1 at 17.4, 20 and 30 m, LOD2 at 40 m; 12 m is at the boundary.)
* LOD0 to LOD1 changes only the fine groove shadows and the barbs; LOD1 to LOD2 removes the thin wire and the bracket arms. The silhouette
  of the wall body (piers, coping, plinth) is the same in all three; even the forced LOD2 at 12 m differs from LOD1 only by the missing
  wire and brackets.

## Numbers (`Tools/model_stats.py`: `stats_before.json`, `stats_after.json`)

| | BEFORE (old wall, baked in the yard model) | AFTER (56 instances of 6 models) |
|---|---|---|
| LOD0 triangles / vertices | 616 / 1,232 (whole wall; no LODs) | panel a,b 440 / 1,006; panel c,d 452 / 1,042; pier 152 / 308; **whole wall 16,744 / 37,296** |
| LOD1 / LOD2 triangles (thresholds 36 / 110) | none | panel 74 / 32, pier 96 / 54; whole wall 4,760 / 2,408 |
| Materials / unique texture files | 3 / 6 (`bx_wall_panel` x3, `bx_galv` x3 *shared*; `bx_steel_dark` is a flat colour) | 3 / 9 (`pw_base` x3 new; `pw_concrete` x3: colour and roughness *shared* Spillway scan files, normal a copy; `bx_galv` x3 *shared*) |
| Largest texture (px) | 2048 x 1024 | 2048 x 2048 (the scan) |
| Total texture pixels (MP) | 9.44 (3.15 shared) | 22.02 (11.53 shared, 10.49 not) |
| Est. GPU texture memory (MB, RGBA8 + mips, worst case) | 48.0 | 112.0 |
| Compiled `vmdl_c` / `vtex_c` (KB) | wall is part of the yard model (not separable) / 4,592 | 100.7 (six files, 11.6 to 19.6 each) / 17,832 |
| Object size (in / m) | whole wall 1620 x 1686 x 140 in (41.1 x 42.8 x 3.56 m); old panel 240 x 8, post 6 x 12 x 140 | panel 240.0 (or 228.6) x 25.8 x 160.2 in (6.10 x 0.66 x 4.07 m); pier 13.6 x 13.6 x 160.5 in (0.35 x 0.35 x 4.08 m) |
| Instances -> total LOD0 triangles added | baked, 616 | 56 (28 panels, 28 piers; pier_a 14, pier_b 14, panel_c 8, panel_a 8, panel_d 6, panel_b 6) -> 16,744, net +16,128 |
| Collision (boxes) | 4 wall boxes + floor box in `boxyard_yard.vmdl` | the same; none on the new models; rays identical |

Net on the Boxyard map: `bx_wall_panel` (6.29 MP) is no longer referenced by anything in the live map (nothing else uses it), the new
unique textures are 18.87 MP, so the map loads about 12.6 MP more (about 64 MiB worst case, about 13.6 MB more compiled).

## Files

Created: `Sources/Boxyard/perimeter-wall-v1/` (this README, `pw_geom.py`, `pw_tex.py`, `build.py`, `objcut.py`, `cut_old.py`,
`scene_edit.py`, `install.py`, `revert.py`, `test_revert.py`, `verify_generator.py`, `old_wall.obj/.mtl`, `backup/`, `stats_*.json`),
`Assets/models/props/boxyard/perimeter_wall_v1/` (6 vmdl, 18 OBJ + 18 MTL), `Assets/materials/boxyard/perimeter_wall_v1/` (2 vmat,
4 jpg/png), and the pictures, capture and LOD scripts in `output/model-trial-20261106/boxyard/`.
Changed (tracked): `Assets/models/maps/boxyard/boxyard_yard.{obj,mtl,vmdl}`, `Assets/scenes/maps/Boxyard/boxyard.scene`,
`Tools/boxyard_map.py`.

## Revert and checks

```
python Sources/Boxyard/perimeter-wall-v1/revert.py        # byte-exact originals back, group out of the scene
python Sources/Boxyard/perimeter-wall-v1/test_revert.py --from-git    # scratch-copy proof: install, revert, again, all four files identical
```

Then set `OLD_WALL_IN_YARD = True` in `Tools/boxyard_map.py` (so a regeneration keeps the old wall) and reload the Boxyard tab (the
`output/model-trial-20261106/boxyard/swap.py revert|install` does the file swap and the tab reload and waits for the yard model to
recompile). The new models and materials stay on disk unused; nothing was deleted. `test_revert.py` without `--from-git` starts from
the working copies, so it only proves the revert while the tree holds the original files (use `--from-git` once installed).

## Not verified

* No play session: nothing was checked in a running match (look at 1920 x 1080, bots' movement, shots against the wall); collision
  is proven by editor-scene rays and by the unchanged yard vmdl only. FPS and video memory were not measured (the memory figures are
  estimates from the files).
* LOD distances for a game window are calibrated from the project's earlier measurement, not measured in a game window.
* The editor log shows no error for the new assets; the yard model recompiled by itself on each swap.

## Verdict

Clearly better up close and at 12 m: real board-formed concrete at 43 px/in instead of a blurry slab, grooves, a mossy plinth, coping, and
piers with brackets and wire that give the wall a silhouette. Weaker: it costs about 27 times the triangles at LOD0 (16.7k, falling to 4.8k and
2.4k with distance, and only the nearest runs are ever in view), and about 64 MiB more worst-case texture memory because the concrete scan is
used at 2048 x 2048; at 1024 x 1024 it would still be 21 px/in (about 2.5 times the old density) and a quarter of that memory.
