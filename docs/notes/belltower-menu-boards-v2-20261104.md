# Belltower menu boards v2 — six installed, old geometry deleted

Approved 2026-11-04. All six A-frames use the reviewed physical timber/hinge/chain model, with four
original A menus and two original B menus. Source LODs: 4,144 / 3,152 / 218 triangles. Native compiles passed.

The scene has a saved `Menu boards` group with stable IDs. `Tools/belltower_menu_boards.py`,
`belltower_detail.sandwich_board` and the map writer preserve it on regeneration without shifting old
planting IDs. Existing positions, rotations, materials and physics were preserved.

264 old triangles were removed from the canonical meshes and corresponding shared material imports;
four retired menu-panel OBJ meshes and obsolete private review wrappers/base meshes were deleted.
Seven model definitions were updated/compiled to stop referencing retired panels, including five
historical preview definitions. No VMDL still references the deleted menu sources. Shared menu textures
and the before/after PNG evidence remain.

`Sources/Belltower/menu-board-v2/installed.json` records the native save/deletion. Source/compile and
restoration checks passed. Final comparison and installed capture: `output/belltower/menu-board-v2/`.
Matched review images use one temporary inspection light, removed after every capture.
