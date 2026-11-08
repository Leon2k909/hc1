# Operations stone counter — unused alternative, 2026-11-06

User requested the original counter remain in Veridant. Restored original render
source references, deleted the new counter scene object and restored the original
bar_counter generator call. Both reusable assets remain available. New model is
floor-centered and ready to place on another map; it has no collision of its own.

Rebuilt the sharp block with four separately fitted front stone panels, return
panels, recessed plinth and eased stone top. Same body footprint/42-inch height,
overhang, LED geometry/material and collision. 334 triangles; existing materials.
Exactly 26 original render triangles removed from Buildings imports, unrelated
records and physics retained. Original reusable asset retained at
models/props/shared/operations_counter_original_v1/counter_original.vmdl.
New model models/props/shared/operations_counter_v1/counter.vmdl.

Source Tools/veridant_operations_counter.py; ops generator hook matches one
Operations stone counter 1 scene object. Native compilation/model checks passed,
scene saved. Matching actual viewport captures output/veridant/operations-counter-v1/
before.png and after.png. No offscreen rendering or changed lighting/display settings.
Initial source OBJ backups remain; before/parent.vmdl was refreshed during
refinement and is post-replacement, not a restoration snapshot.
