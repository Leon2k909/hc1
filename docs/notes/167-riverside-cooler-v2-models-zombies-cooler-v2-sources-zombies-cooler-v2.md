## Riverside's cooler v2 (`models/zombies/cooler_v2`, `Sources/Zombies/cooler-v2/`, 2026-10-31)
- The open ice chest at the dog run's gate, from the reference picture, replacing three boxes and four cans at the user's word ("cooler new better") after a side
  by side in s&box. Same footprint, height and lid angle, and the same lid lettering in the same hand.
- `riverside_parts.cooler` keeps the collision box in `riverside_pad.vmdl` and records a placement. The scene's `Cooler` object holds the model.
- Installed by `install_cooler.py`, which cuts its 136 triangles from `riverside_pad.obj`: `riverside_map.py` can't be safely rerun (note 163).
- Seen in s&box in an isolated editor scene under the map's own light, exposure held at 3.5: it reads well there, and needed no brightening, where the old body
  nearly vanished. Collision tested with rays. **Not yet seen in a live match.** See the folder's README.
