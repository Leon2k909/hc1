# Riverdale locker banks v1 (2026-11-06)

**What it is:** the eight plain steel slabs that stood in for lockers on Riverdale (a bare `rv_steel` box, 12 triangles, no doors) are replaced by two real
two-tier locker banks: `locker_bank_4` (52 in wide, 4 doors, 6 placed) and `locker_bank_6` (80 in wide, 6 doors, 2 placed). Render only: the slabs' collision boxes are unchanged.
Status: installed in the live map and approved by the user; old slabs deleted.

## Where they are (8 banks)

| Place | Banks | Plan position | World position (x, y, z) | Doors face |
|---|---|---|---|---|
| B1 upper control room, south wall | 2 x `locker_bank_6` | e -120..-40 and 40..120, n -1000..-980, floor z 192 | (-990, +80, 192) and (-990, -80, 192) | north (+x) |
| West spawn building, upstairs room, west wall | 3 x `locker_bank_4` | e -2296..-2276, n centres -1100 / -1040 / -980, floor z 200 | (-1100 / -1040 / -980, 2286, 200) | east |
| East spawn building, upstairs room, east wall | 3 x `locker_bank_4` | e 2276..2296, same n centres, floor z 200 | (-1100 / -1040 / -980, -2286, 200) | west |

Picked because players spawn in, and fight past, those rooms and the slabs sit at eye level: they were the crudest props there (a flat rectangle you could read as a wall panel).

## The model

- Real proportions in inches: 80 in tall, 20 in deep (the old slab's footprint exactly), 26 in per door column, two tiers.
- Carcass with eased edges (0.22 in bevel), top cap, dark plinth, side returns, dark liner behind the doors.
- Each door (LOD0): bevelled slab with rim strips, a recessed louvre vent with 5 angled blades and 2 posts, a latch pocket with a stainless bar, two studs and a key barrel,
  two galvanised hinge barrels, and a label holder (dark frame with a white card).
- LOD1 keeps slab, rim, 3 louvre blades and the latch bar; LOD2 is plain door slabs with dark vent quads. Switch thresholds 0 / 30 / 80 (about 14 m and 39 m, per `prop-distance-look`).
- Materials: only the map's own `materials/riverdale/rv_steel`, `rv_dark`, `rv_stainless`, `rv_galv`, `rv_white` (all five are already in the Riverdale scene: rv_stainless and rv_galv are used by `riverdale_hall_detail.obj`).
  No new texture was made, so the colour identity and wear of the old steel is kept (same scan, same tint).
- Files: `Assets/models/props/riverdale/locker_bank_v1/locker_bank_4.vmdl`, `locker_bank_6.vmdl` plus `*_lod0/1/2.obj/.mtl`. Generator: `locker_bank.py` (`python -X utf8 locker_bank.py [out dir]`).

## How it is installed

- The 8 slabs' faces (12 triangles each) were cut from `riverdale_middle.obj` (24 lines), `riverdale_west.obj` (36) and `riverdale_east.obj` (36). No vertex line was touched; the three area models'
  collision (explicit `PhysicsShapeBox` per old slab, in their vmdls) is unchanged. The exact cut lines are in `install_state.json`.
- The scene `Assets/scenes/maps/Riverdale/riverdale.scene` has a new group "Locker Banks" with 8 `Sandbox.ModelRenderer` objects (text-level insertion, file format and CRLF kept).
- The generator keeps the banks on a rebuild: `Tools/riverdale_lockers.py` (`NEW_LOCKERS = True`; `False` draws the old boxes again) and four small edits in `Tools/riverdale_map.py`
  (import, `LOCKERS.PLACED.clear()` in `build()`, `LOCKERS.bank( ... )` in place of `box( ..., "rv_steel", METAL )` for the 8 slabs in `b1()` and `spawn_side()`, and the scene group in `write_scene()`).
  `verify_hook.py` builds the three areas with the hook off and on: collision boxes identical (31 / 44 / 48), only the slabs' 12 / 18 / 18 `rv_steel` polygons disappear, 8 placements.
- The editor recompiled the three map models and the scene by itself; compile succeeded with 0 errors; the editor's two small new vmdls were compiled with `recompile_asset`.

## Before / after (real editor viewport)

Native frame captures (`bridge_call screenshot_game`, crop x 428 y 100 w 1102 h 455), the same pose, 10 s settle, no change to lighting, exposure or post. Mean luma before -> after:
close 65.9 -> 63.1, far 94.4 -> 94.2, B1 113.0 -> 112.9 (the lighting is the same). Poses are in `output/model-trial-20261106/riverdale/camera_poses.json`.

| View | BEFORE | AFTER | Pose |
|---|---|---|---|
| Close, west spawn room, 106 in (2.7 m) | `output/model-trial-20261106/riverdale/before.png` | `.../after.png` | `-1040,2170,262` angles `6,90,0` |
| Far, same room, 439 in (about 11 m, its longest sight line) | `.../before_far.png` | `.../after_far.png` | `-700,2095,262` angles `4,155,0` |
| B1 upper control room, 190 in (4.8 m) | `.../before_b1.png` | `.../after_b1.png` | `-790,0,256` angles `6,179.9,0` |

(The orange bulbs, red/green/blue axis gizmo, the green zone box and the white spawn mannequin are editor gizmos; they are in both images.)

## Numbers (`Tools/model_stats.py`, definitions in its docstring; JSON in `stats_before.json`, `stats_after.json`)

BEFORE = one old slab (the same 12 triangles for 52 in and 80 in wide), measured from `old_slab_52.obj` / `old_slab_80.obj`. AFTER = one new bank. "shared" = the map's own materials, already loaded for the rest of the map.

| | BEFORE (slab) | AFTER `locker_bank_4` (52 in) | AFTER `locker_bank_6` (80 in) |
|---|---|---|---|
| LOD0 triangles / vertices | 12 / 24 | 1,762 / 3,964 | 2,538 / 5,716 |
| LOD1 / LOD2 triangles (switch thresholds 30 / 80) | none (face of a map model) | 794 / 114 | 1,086 / 142 |
| Materials / unique texture files | 1 / 5 (shared) | 5 / 22 (shared) | 5 / 22 (shared) |
| Largest texture (px) | 1024 x 1024 | 1024 x 1024 | 1024 x 1024 |
| Total texture pixels (MP) | 5.24 (shared) | 23.07 (shared) | 23.07 (shared) |
| Est. GPU texture memory (MB, RGBA8 + mips) | 26.67 (shared) | 117.33 (shared) | 117.33 (shared) |
| Compiled `vmdl_c` / `vtex_c` total (KB) | no own vmdl_c; vtex_c 4,616 (shared) | vmdl_c 55.9; vtex_c 12,703 (shared) | vmdl_c 74.2; vtex_c 12,703 (shared) |
| Object size (in / m) | 52 x 80 x 20 / 1.32 x 2.03 x 0.51 and 80 x 80 x 20 / 2.03 x 2.03 x 0.51 | 52 x 80 x 20.11 / 1.32 x 2.03 x 0.51 | 80 x 80 x 20.11 / 2.03 x 2.03 x 0.51 |
| Instances -> total LOD0 triangles | 8 slabs -> 96 | 6 -> 10,572 | 2 -> 5,076 |
| Collision | 8 `PhysicsShapeBox` (one per slab) | unchanged (the same 8 boxes, kept in the map vmdls) | unchanged |

Net: 15,648 LOD0 triangles for the 8 banks, minus the 96 of the old slabs = +15,552 if every bank were drawn at LOD0 at once (it never is: at most three banks are in a room, and LOD1 / LOD2 take over at about 14 m / 39 m).
No new texture memory: the five materials were already in the Riverdale scene. The frame cost of the extra triangles was not measured.

Collision check in the live editor scene (rays through `Scene.Trace`): from the close pose along +y at z 262 and z 205 the first hit is the west model's collider at y 2276 after 106 in (the front plane of the banks);
from (-900, 80, 232) along -x the first hit is the B1 model's collider at x -980 after 80 in. Same planes as the old slabs.

## Old slabs deleted

The user approved the banks on 2026-11-06 ("yes good change"). The old slab geometry, install/revert scripts and install_state.json were deleted, so this is no longer revertible with a script; `locker_bank.py` still regenerates the models.

## Files

- New: `Assets/models/props/riverdale/locker_bank_v1/` (2 vmdl, 6 obj, 6 mtl, editor `.meta` files), `Tools/riverdale_lockers.py`, this folder (`locker_bank.py`, `make_old.py`, `old_slab_52.obj/.mtl`, `old_slab_80.obj/.mtl`,
  `install_lib.py`, `install.py`, `revert.py`, `install_state.json`, `verify_hook.py`, `test_install_revert.py`, `stats_before.json`, `stats_after.json`, this README), `output/model-trial-20261106/riverdale/` (6 images, `camera_poses.json`).
- Changed: `Assets/models/maps/riverdale/riverdale_middle.obj`, `riverdale_west.obj`, `riverdale_east.obj`, `Assets/scenes/maps/Riverdale/riverdale.scene`, `Tools/riverdale_map.py`, `CLAUDE.md` (index line).
- Nothing committed.

## Not verified / known weak points

- Seen in the engine: the west spawn room (close and far) and B1. The east spawn building's three banks use the same model mirrored (yaw 90); their position and facing were computed and checked by the generator, not looked at.
- No play session or bot test was run. Collision is unchanged and the rays above agree, so routes and bot nav should be as before; not proven by a match.
- The doors do not open and all 8 banks are identical (same door, blank label card, no per-door dents or marker); the wear is only the shared steel scan.
- The front of the west banks is 10 in off the wall plane at y 2286 (a ray 10 in above the banks stops there), so about half of each 20 in deep carcass is probably inside the wall, exactly as with the old slabs; their footprint was not changed.
- The door fronts read a little darker and greyer than the old flat slab (same material; the recesses and ambient occlusion darken them). Luma over the whole frame is within 3 points.
