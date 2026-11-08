# Riverdale B1 desk v1 (2026-11-06)

**What it is:** the plain 72 x 40 x 30 in grey box (12 triangles) that stood as the desk in B1's upper control room is replaced by a steel workstation desk: eased laminate top with
a steel edge band, a three-drawer pedestal (drawer fronts, steel pull handles, label holders, a lock), a kneehole with a modesty panel, an end panel, plinths, levelling feet,
a cable tray under the top and a grommet. Render only: the old box's collision is unchanged. Status: installed in the live map and approved; old box deleted.

- Where: B1 upper control room, plan e -36..36, n -960..-920, floor z 192 (world -940, 0, 192); drawers and kneehole face north into the room. 1 instance.
- Model: `Assets/models/props/riverdale/b1_desk_v1/b1_desk.vmdl` (3 LODs, thresholds 0 / 30 / 80), generator `desk.py`. Only the map's own materials: rv_desk, rv_dark, rv_stainless, rv_steel, rv_galv, rv_white. No new texture.
- Install: the old box's 12 triangles cut from `riverdale_middle.obj` (exact lines in `install_state.json`), a "Desks" group added to `riverdale.scene` after "Locker Banks", and the generator keeps it:
  `Tools/riverdale_desks.py` (`NEW_DESK`) plus 4 edits in `Tools/riverdale_map.py`. The editor recompiled the map model and scene by itself, 0 errors.

## Before / after (real editor viewport, same poses, 10 s settle, native screenshot_game crops 1102 x 455)

| View | BEFORE | AFTER | Pose |
|---|---|---|---|
| Close, about 3 m | `output/model-trial-20261106/riverdale-desk/before.png` | `.../after.png` | `-870,-120,255` angles `13,120,0` |
| Far, about 5 m | `.../before_far.png` | `.../after_far.png` | `-700,-150,255` angles `9,160,0` |
| Side, about 2.5 m | `.../before_side.png` | `.../after_side.png` | `-930,-135,240` angles `12,90,0` |

Mean luma before -> after: 105.9 -> 105.6, 100.3 -> 99.4, 102.2 -> 102.3. (Gizmos, the green zone box and the spawn mannequin are editor gizmos.)

## Numbers (Tools/model_stats.py; stats_before.json, stats_after.json)

| | BEFORE | AFTER |
|---|---|---|
| LOD0 triangles / vertices | 12 / 24 | 1,006 / 2,296 |
| LOD1 / LOD2 triangles (thresholds 30 / 80) | none | 434 / 110 |
| Materials / unique texture files | 2 / 10 (shared map materials) | 6 / 27 (all the map's own, shared) |
| Largest texture | 1024 x 1024 | 1024 x 1024 |
| Total texture pixels / est. GPU | 10.49 MP / 53.33 MB (shared) | 28.31 MP / 144.00 MB (shared; nothing new) |
| Compiled vmdl_c / vtex_c | no own vmdl_c | vmdl_c 37.7 KB; vtex_c 14,543 KB (shared) |
| Object size | 72 x 40 x 30 in | 72 x 40.9 x 30.06 in (handles stand 0.9 in proud) |
| Instances -> LOD0 triangles | 1 -> 12 | 1 -> 1,006 |
| Collision | 1 box | unchanged (the same box, kept in the map model) |

## Old box deleted

Approved by the user 2026-11-06 ("good change, install new, delete old"). The old geometry, install/revert scripts and install state are deleted; not revertible by script. `desk.py` regenerates the model. New files: `Assets/models/props/riverdale/b1_desk_v1/`, `Tools/riverdale_desks.py`, `output/model-trial-20261106/riverdale-desk/`; changed `riverdale_middle.obj`, `riverdale.scene`, `Tools/riverdale_map.py`, `CLAUDE.md`. Nothing committed.

## Not verified / weak points
- No play session or bot test; collision is the same box. No frame-time measurement.
- Nothing sits on the desk (no monitor, keyboard or papers) and there is no chair: the desk itself is the only change.
- The textures are the old paint-on-steel scans; the grey reads close to the old block's colour.
