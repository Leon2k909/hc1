# Veridant reception stair rail — applied review, 2026-11-05

Replaces the five-post reception stair handrail with smooth tubing, rounded top
rail end caps and side-mounted plates with four small fasteners each. Tube radii,
upper/mid-rail centre lines and overall rail height are retained. The end posts
move three inches inward along the flight so all plate anchors lie on the actual
stair run; post lower ends and fixing plates follow the actual 17-tread profile.

The scoped patch replaces 82 original triangles with 1,648 new triangles in an
additional ModelDoc render import. Every unrelated OBJ record/index, all other
render imports (including the accepted cloth banner and reception light), the
entire physics suffix, scene and lighting are preserved. The narrow generator
hook retains exactly the original 7..176-height player clip and only affects the
named reception stair rail. No collision additions or live navigation changes.

`build.py` stages from guarded backups; `prepare_import.py` imports through the
native editor; `verify.py` checks finite data, unit normals, nondegenerate faces,
retained records and byte-equivalent physics. The loaded Buildings and Dressing
models reported IsError=false; Veridant has no unsaved scene changes.

Actual displayed editor viewport frames at matching camera/settings are
`output/veridant/reception-stair-rail-v1/before.png` and `after.png`. No temporary
camera, isolated scene or RenderToBitmap. Existing editor gizmos remain visible.
Backups, stage and verification are in that same output directory. Historical
imports must not overwrite newer work without a deliberate baseline refresh.
