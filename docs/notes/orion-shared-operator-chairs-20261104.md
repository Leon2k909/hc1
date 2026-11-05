# Orion reuses the approved dark Collider chair

User correction: the chair should not be white, and a better chair was already made. Reused the dark padded
Collider chair approved 2026-10-29 for all six Orion placements, scale 0.82, without changing its shared assets.
Deleted the pale duplicate. Exactly 576 old triangles were removed; all other faces/attribute records,
both ModelDocs and physics were retained. Six renderers are the only scene changes. Feet are now on the actual
room floors (336.2/240.2) instead of the old z=0 placement. Desks/screens were not changed.

Native shared-chair loading, all six floor traces and exact source checks passed. The native capture preserved
scene/play state. An explicit full map compile request timed out and is not claimed as completed.
See `Sources/Orion/task-chair-v1/README.md` and `output/orion/task-chair-reuse-v1/`.
