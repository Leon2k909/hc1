# Orion chairs — approved shared dark Collider model

The user pointed out that a better chair already existed and the new proposal was too pale. All six Orion
chairs now reuse `models/props/collider/chair-trial-v1/after.vmdl`, the dark padded chair approved 2026-10-29.
Its 8,672-triangle mesh, four materials/textures and existing Collider installation are unchanged.
The duplicate Orion chair, private materials, builder and comparisons were deleted.

Renderer-only instances retain the old XY centres/facing, at scale 0.82 and yaw 180. No colliders are added.
The old geometry was incorrectly emitted at z=0 below the room floors; the new feet sit at 336.2 (four in
Launch Control) and 240.2 (two in OPS). Native traces hit the original physical floors 0.2 inches below them.
The original desks, screens and their physics were preserved.

Exactly 576 old render triangles were removed from the current Launch Control/Fuel inputs. All other faces
and vertex/UV/normal records are identical. Both ModelDocs/physics are byte-identical. The only semantic
scene changes are six new renderers. No full map generation was run.

`Tools/orion_task_chairs.py` and the CHAIRS/map-writer hooks preserve the shared resource and floor heights.
`verify.py` checks installed resources/nodes, preserved ModelDoc hashes, generator hooks and native floor proof.
`output/orion/task-chair-reuse-v1/verification.json` records the exact diff before retiring old snapshots.
`native/validation.json` confirms all six accepted models and floor hits, with editor scene/play state unchanged.
`native/ops.png` and `native/launch-control.png` show the dark chair in the saved map's context.
Native shared-model loading and floor checks passed. Explicit full map recompilation timed out, so it is not
claimed as completed. No match/performance benchmark was run. The pre-existing audit.py remains historical.
