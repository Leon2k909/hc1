# Riverside sleeper retaining walls — real-scan texture (rs_ties v2, installed 2026-11-07, kept by the user)

The user said the raised yard's timber wall texture "looks bad" and asked to reuse a fitting texture or make one.
The wall is `riverside_ground.vmdl`'s `rs_ties` faces (the pad's and terrace's sleeper retaining walls, their 2 in
caps, the levee face and its cards in `Tools/riverside_map.py`), so every sleeper wall on the map changed together.

- Old: `riverside_materials.ties()`, numpy paint at 11 px/in, pale cloudy blotches, straight courses, no real grain.
- Searched first: Railhead's `rw_sleeper` is concrete and `rw_sleeper_wood` procedural; Stillhouse's tarred timber is
  procedural; Lowtide's pile timber has an unknown source image; the plank scans are deck boards. None fitted as-is.
- New: `Tools/riverside_sleepers.py` lays Belltower's photographed oak boards (`brown_planks_03`, 4K) out as 12 courses
  of 8 in sleepers per 96 in tile at 43 px/in: each sleeper a different straightened board, wandering joints with
  packed soil, staggered butt joints sawn slightly off square with end splits, eased arrises, about half the sleepers
  keeping patchy creosote, growth 0.7% and only in the joints. Normal map from the scan's integrated height plus the
  wall's own shapes. Maps: `materials/riverside/rs_ties_v2_{color,normal,rough,ao}.png` (rough and AO at 2048).
- `Tools/riverside_materials.py rs_ties` now calls it; `ties()` and the old `rs_ties_*` maps are kept on disk.
- Rollback: copy `rollback/rs_ties.vmat` over `Assets/materials/riverside/rs_ties.vmat` (and drop the hook in
  `riverside_materials.build`).
- Review: `review/before.png`, `review/after_v1.png` (editor window captures, same camera `review/camera.json`,
  same scene lighting) and `review/comparison.png`. Not yet seen in a match or at a distance.
