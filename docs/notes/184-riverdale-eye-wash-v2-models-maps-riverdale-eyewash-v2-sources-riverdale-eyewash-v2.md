## Riverdale's eye wash v2 (`models/maps/riverdale/eyewash_v2`, `Sources/Riverdale/eyewash_v2/`, 2026-10-31)
- Replaced all 5 in the hall at the user's word, after they sent a screenshot of the old one and saw both side by side: east and west walls at n 560, north wall at e 962, south wall at e +-880.
- `riverdale_hall.eyewash` now only records a placement (`Tools/riverdale_eyewash.py`) and draws its sign. `riverdale_map.write_scene` adds an "Eye Washes" group, renderers only, as the old ones had no collision.
- It stands 0.25 in off the wall, on the epoxy band (`STAND_OFF`). On the bare wall, the band swallowed the bracket's plate.
- Its surface comes from `forestbase/scans/` at true scale: `metal_plate_02` for the wear's shapes, `container_side` for a faint mottle. A strong mottle read as moss in the engine.
- Installed with `install_eyewash.py`, which cuts the faces from the live `riverdale_hall_detail.obj` and `riverdale_hall_fine.obj` by position, because the hall isn't to be rebuilt whole. Each old eye wash was 68 faces in detail and 166 in fine.
- `riverdale.scene` has line ends partly doubled by an earlier tool, so it can't be rewritten whole without a huge diff. The group is inserted into the text, and only if the result parses to exactly the scene plus the group.
- The watcher missed the fine OBJ's rewrite for 2 minutes: compare `_c` and source times, as `verify_eyewash.py` does, before believing a look at it.
- Checked in a hidden copy of the hall, not in a match. See the folder's README.
