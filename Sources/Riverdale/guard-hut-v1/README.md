# Riverdale guard huts v2 (2026-11-07)

**What it is:** the two spawn-yard guard huts were a plain 100 x 100 x 110 in concrete box with a window hole onto a painted office card, a flat roof slab, a flat blue door and a
rooftop box (576 triangles, 10 materials). They are replaced by two placed models, `guard_hut_east` (yard window on the east face) and `guard_hut_west` (mirrored), plus an interior
spot light each. Render only: collision unchanged. Status: installed, **review pending**. v1 (a plain white booth) was shown first; the user said "u can do better", so this is v2.
The old faces are kept: `python -X utf8 install.py revert` puts them back (tested once, sha1 exact; since then only the scene group was replaced with `install.py regroup`).

## Where

| Hut | Plan centre | World (x, y, z) | Model |
|---|---|---|---|
| West spawn yard | e -2120, n -1450 | (-1450, +2120, 0) | `guard_hut_east` |
| East spawn yard | e +2120, n -1450 | (-1450, -2120, 0) | `guard_hut_west` |

## The model (`Assets/models/props/riverdale/guard_hut_v1/`, generator `hut.py`)

- Prefab steel cabin: 5 in walls with real openings, light-grey profiled cladding (`rv_fc_clad_light`) with geometric ribs every 8 in, square dark corner posts, a dark base channel,
  an eave band, a concrete pad.
- Real glass (`materials/railhead/rw_glass`, the map's control-room glass) on three sides: the yard window (fixed pane + inboard sliding pane, latch, stainless deal tray), and a side
  window on each side face with a transom. Dark frames, pressed-steel sills, interior stools.
- Door in a framed opening: recessed blue steel door, wired vision panel, kick plate, lever, lock, hinges, closer, PPE sign, a caged bulkhead lamp above. No-smoking sign on the south face.
- Roof: overhanging deck (deeper over the door), fascia, white soffit, back gutter and downspout with brackets, vent cap.
- Back wall: through-wall air conditioner with grille, brackets and condensate drain; meter box with conduit.
- Weathering: the map's translucent splash grime (`rv_grime_foot`) along the wall foot.
- Interior: epoxy floor, concrete walls, tiled ceiling with a troffer, worktop under the yard window with a cabinet, monitor showing a camera feed, keyboard, phone, logbook, mug,
  office chair, notice board, whiteboard, clock, binders on a shelf, key box, CCTV monitor on a bracket, extinguisher with its sign, heater (atlas art from the map's own hall/yard
  sign and screen atlases). Lit by a scene spot light (`Guard Hut Lamp`, 98 in up, radius 112, no shadows, colour 0.55,0.52,0.46).
- LODs: 7,118 / 1,538 / 704 triangles (thresholds 0 / 30 / 80, about 14 m and 39 m).

## How it is installed

- `Tools/riverdale_huts.py` (`NEW_HUT = True`): `hut()` replaces the old `box( ... METAL )` and `guard_hut()` in `Tools/riverdale_map.py` `spawn_side()`, records the placement and
  adds the same collision box; `scene_group()` writes the two huts with their lamps. `guard_hut()` is still in the file, unused.
- `install.py apply`: diffed two staged generator builds (hook off/on); exactly 576 face lines per area cut from the live `riverdale_west.obj` / `riverdale_east.obj` (kept in `install_state.json`),
  no vertex line touched. `regroup` replaces the "Guard Huts" scene group; `revert` restores both OBJs and the scene byte for byte.

## Before / after (real editor viewport, native `screenshot_game`, same pose, no lighting or post change)

| View | BEFORE | AFTER | Pose |
|---|---|---|---|
| Close, 200 in (5 m) | `output/model-trial-20261106/riverdale-hut/before.png` | `.../after.png` | `-1330,1960,80` angles `6,127,0` |
| Far, about 15 m | `.../before_far.png` | `.../after_far.png` | `-1050,1700,85` angles `4,133.6,0` |
| Other (mirrored) hut, new only | | `.../after_west_hut.png` | `-1330,-1960,80` angles `6,-126.9,0` |

Mean luma before -> after: close 58.5 -> 51.0, far 56.5 -> 55.8 (the hut is darker-framed; the scene lighting was not changed apart from the two small interior lamps).

## Numbers (`Tools/model_stats.py`; `stats_before.json`, `stats_after.json`)

| | BEFORE (one hut) | AFTER (one hut model) |
|---|---|---|
| LOD0 triangles / vertices | 576 / - | 7,118 / 15,436 |
| LOD1 / LOD2 triangles | none (faces of a map model) | 1,538 / 704 |
| Materials / unique texture files | 10 / 25 | 27 / 58 (all already in the map) |
| Total texture pixels (MP) | 25.43 (shared) | 105.91 (shared) |
| Est. GPU texture memory (MB) | 129.33 (shared) | 538.65 (shared) |
| Compiled vmdl_c (KB) | none | 207.5 |
| Object size (in) | about 112 x 112 x 130 | 122 x 122 x 123 |
| Lights | none | 1 unshadowed spot inside |
| Collision | one box | unchanged |

No new texture memory (every material is already used by Riverdale or its glass), but 27 materials means up to 27 draw calls per hut at LOD0 (12 at LOD2).

## Not verified / weak points

- No play session; collision is unchanged.
- 27 materials per hut is a lot of draw calls for one prop; frame cost not measured.
- The pad is 2 in wider than the collision box and the downspout shoe and sills stand proud of it (render only).
- The monitor and chair backs read as dark squares through the yard window.
- The old `guard_hut()` function is kept (unused) until approval. Nothing committed.
