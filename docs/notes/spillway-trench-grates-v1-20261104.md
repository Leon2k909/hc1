## Spillway trench grates (2026-11-04)

- Five cargo-yard flat grating quads replaced with framed steel bar panels, cross ties, bolts and lifting eyes.
- `Tools/spillway_map.cargo_yard` calls `Tools/spillway_trench_grates.py`; sources and guarded native installer in
  `Sources/Spillway/trench-grates-v1/`. This is a targeted splice; no full map rebuild is needed.
- Remove10 old triangles, add37,394, preserve39,906 other faces exactly. All hulls, full physics suffix and scene
  remain unchanged. Visuals stay inside the original footprints, below one inch above the floor. Dark backing
  covers the existing floor through the slots; no excavation or gameplay change.
- Matched native renders, installed map view, snapshots and checks: `output/spillway/trench-grates-v1/`.
