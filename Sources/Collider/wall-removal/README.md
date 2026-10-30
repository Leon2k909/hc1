# West-wing concrete screen removal — 27 October 2026

Removed the pictured freestanding concrete wall at plan e -1524..-1500,
n -160..160, z 0..164. The east-wing screen was removed in the subsequent
`Sources/Collider/wall-removal-east` pass; both are now absent.

`Tools/collider_remove_west_wall.py` stages a one-time migration against the
installed structure: exactly 12 render triangles and one `PhysicsShapeBox`
are removed. Every other OBJ byte and ModelDoc byte remains exact. The hull
mesh, detail/machine/glass models, materials and saved scene are preserved.
`collider_map.wings` retains the open west approach in future generation.

The minimap is regenerated from the actual published box/hull physics. The
reconstructed pre-edit map must match every published radar pixel before the
new map is accepted. The guarded native importer publishes only the structure
OBJ, structure ModelDoc and minimap; it does not edit or save the scene.

Native compilation and resource freshness pass. Nine rays through the removed
wall are clear, while nine rays through the east reference wall are unchanged.
All 68 authored positions pass support, clearance and reachability checks, with
zero exposed Retakes pairs before or after. Native matched images record both
wings. `verify.py` produces `installed.json` and the output validation receipt.

Backups, staged files and the removed collision node are in
`output/collider/wall-removal/stage-v1`. `primary-stage-sync.json` records the
guarded synchronization of the matching primary build-stage files.
