## Boxyard pipe stacks (2026-11-04)

- Both six-pipe stacks at B upgraded with hollow bores, wall thickness/bevelled rims, weld seams, mill markings,
  steel bands/buckles, timber dunnage and chocks. Original positions and seeded end staggering retained.
- `Tools/boxyard_map.pipes` calls `Tools/boxyard_pipe_stacks.py` and retains its original collision box expression.
  Sources and guarded native integration: `Sources/Boxyard/pipe-stacks-v1/`.
- Exact face splice removes480 faces, adds11,352 and preserves1,526 unrelated faces. Full ModelDoc physics,
  all hull sources and saved scene stay unchanged. No full map regeneration.
- Actual matched engine renders, installed context, snapshots and checks: `output/boxyard/pipe-stacks-v1/`.
- User asked to retain both versions: `models/maps/boxyard/pipe-stacks-v1/legacy_pipes.vmdl` is the inactive
  original render mesh; the new stacks remain active in the map and generator. Receipt: `retained-variants.json`.
