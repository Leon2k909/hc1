# Retaining-wall planting strip

Replaces only the ten crossed-card plants at plan E=740..753, N=34..148,
seed 812, beside the east terrace retaining wall. The original visible plants
occupied N=65..150. Their exact 80 oriented triangles were removed from the
current `pergola-flowers-v2/foliage-base.obj`; every retained byte and original
OBJ vertex, UV and normal index remains unchanged.

`Tools/veridant_wall_rosemary.py` retains the old layout-call signature but uses
the reviewed garden planter's authored beech shrub mesh and material. Its source
and provenance remain in `Sources/Veridant/planter-shrub-v1/beech-source.json`.
Uniformly scaled, rotated crowns retain their leaf proportions, texture UVs,
authored normals and branching. Roots are embedded into a shallow soil bed with
dark metal edging. The two draw-only imports total 27,304 triangles. No collision,
scene objects, map geometry, light, animation or per-frame work is added.

The map generator delegates only the pictured seed-812 strip to this builder and
preserves its material bindings. Other shrub calls and every unrelated current
render import are retained. The foliage model keeps its existing resource path.

Publication and verification:

- First scoped card removal: `output/veridant/shrub-volume-v1/stage-v2/manifest.json`.
- Final geometry published by `stage-v4`; final cleaned-source manifest: `stage-v5`.
- Native model compile: `compile-v4-native/asset_compile.json`; material compiles:
  `compile-native/call_tools.json`. The authored leaf material was already installed.
- The provisional sparse procedural version was rejected during screenshot review.
  Final assets use the authored shrub; trial sources remain only in the output record.
- Use underscore-only ModelDoc node names. Names containing a hyphen produced
  native `RenderMeshFile` resolve failures; the final two node names compile.
- Matched view: `output/veridant/quality/shrub-volume-v1-filled/wall-border.png`.
- Close-up: `output/veridant/quality/shrub-volume-v1-detail/wall-border-close.png`.
- Native capture receipts verify restoration of scene camera, tone, camera state,
  scene objects and stopped play state. This task never writes the scene.

The separate bar/planter work saved the shared scene during this task. Its additions
and probe changes were reviewed and retained; the scene hash therefore differs
between the first and final captures. The final capture uses the current saved
document. `concurrent-scene-review.json` records that check. No GPU frame-rate
benchmark was performed.
