# Boxyard's shipping crates v2: review candidate

Created 2026-10-30. **Not installed.** Boxyard's six crates still come from `railhead_props.crate`, which is unchanged. Nothing is
committed.

Boards with real gaps, a lapped frame with diagonal braces, skids, steel strapping, end handles, nails and made-up stencils, in the
map's two sizes (47.2 x 31.5 x 31.5 and 60 x 48 x 48). The old crate is better than its code suggests: its tiled wood is sharper close up
than this one, at 14 and 9.5 px/in, so this wins on shape and detail, not on grain.

- Triangles, LOD 0-2: 1,400 / about 840 / about 180 (standard), 1,550 / about 930 / about 220 (large), with a 2048 atlas each.
- The first pass had black lines down every corner: battens sharing a face bake fully occluded and show through. They're lapped now.
- `crate.py` builds, bakes and exports, `paint_crate.py` paints, `render_crate.py` renders, `verify_crate.py` checks, `make.ps1` runs them.

Not done: never compiled or seen in s&box (the images are Blender renders), and the LOD distances (30, 80) are estimates.

To install: as for the drums in `Sources/Boxyard/oil_drum_v2/README.md`. In `boxyard_map.props`, keep each crate's collision box with no
faces and place the model in the scene: engine position (n, -e, z0), yaw 0 for `along="n"` and 90 for `along="e"`.
