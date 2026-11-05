## Reef Hall bronze entrance planter — installed (2026-11-04)

- Rebuilt the two lobby entrance planter shells with rounded corners, 24 recessed flutes, rolled rim and recessed
  toe. Private brushed bronze textures. Original foliage, soil, position, size and metal collision retained.
- User accepted; public lobby and offline generator now use the new shell. Guarded native installation preserved
  the active Riverside scene and stopped play state. Public lobby compiled and loaded with all three new materials. Narrow
  splice: 52 shell triangles removed, 11,968 added, 31,290 unrelated faces retained exactly. Physics byte identical.
- Sources, staging, checks, matched native before/after and original-lighting placement renders:
  `Sources/ReefHall/bronze-planter-v1/`. Evidence is in its local `review/` directory because the `output` junction's
  offloaded D: writes stalled during this task. Do not use abandoned partial snapshots in `output/reefhall/bronze-planter-v1/`.
- Native isolated scenes rendered the comparison and saved lobby visual roots with only the render-model swap;
  user scene, unsaved state and play state were preserved. No full map rebuild or envmap bake.
