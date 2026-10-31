## Burn drum v2 (`models/zombies/burn_drum_v2`, `Sources/Zombies/burn-drum-v2/`, 2026-10-30)
- Riverside's 14 drums (blue 4, red 3, rust 5, cold 2), replacing `riverside_parts.drum`'s flat 14-sided cylinders at the user's word after a
  before/after. Same size, and the ember bed is at the old height, under where `MapFire`'s flames sit.
- `riverside_parts.drum` keeps the hull and fire and records a placement. The scene's "Burn Drums" group holds the models.
- **Don't rerun `Tools/riverside_map.py` without looking at what it changes.** The shared kit has moved on since the map was last generated: on
  2026-10-30 an unmodified run rewrote the ground, levee, pad and dressing, and reported paints with no material (`rv_steel`, `rv_yellow`,
  `rv_zinc`). `install_drums.py` cuts the drums from the checked-in OBJs instead.
- Seen in s&box on 2026-10-31 in an isolated editor scene, with `MapFire`'s real flames under the map's own light (`Sources/Zombies/cooler-v2/capture_engine.cs.txt`):
  it holds up, and the hull's collision tested with rays. That showed one fault Blender hadn't, fixed since: the fire's light reached the drum's bare floor, which
  read as a pale patch through the air holes. **Not yet seen in a live match**, and the LOD distances are unchecked. See the folder's README.
