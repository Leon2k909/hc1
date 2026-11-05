# Belltower cafe menu board v2 — installed 2026-11-04

The user approved the before/after comparison and requested replacement and deletion of the old boards.
Installed on `codex/belltower-menu-board-v2-install`.

The candidate replaces the two solid slab boards and painted frame with separate bevelled timber stiles
and rails, recessed chalk panels, open feet, steel shoes, corner fasteners, two barrel hinges and linked
retaining chains. It uses the existing photographed wood, iron and chalkboard materials. The menu bitmap
is unchanged; UVs crop out its painted frame so the physical timber supplies that frame instead.

Three source LODs have 4,144 / 3,152 / 218 triangles. Native compilation and finite/nonzero-face checks
passed. `build.py` stages only private review assets. A private west visual model removes exactly the
44 original cafe-board triangles, leaving all other source records and saved physics intact.

`review.py` imports/compiles and captures through native s&box. The before/after comparison temporarily
swaps the west visual model and adds the candidate at world `-218,628,0`, then restores the original
model, object IDs, cameras, tone and editor state. All shared source guards remain exact, including the
scene with the twelve approved flowerpots already installed.

The cafe sits in deep shade. `before-detail.png` and `after-detail.png` use the same temporary inspection
light, camera, projection and exposure settings so the joinery can be judged. The light is removed after
each capture and is never saved. Dark natural-light captures are retained separately. A fixed-exposure
metadata change alone produced identical pixels, so the bright-exposure attempt is not evidence of an
effective GPU exposure change.

All six boards are installed in a saved `Menu boards` group, preserving four A menus and two B menus,
their positions, orientations and collision. Native compilation passed for both variants, both town
models and the five older preview definitions whose shared retired menu imports were removed.

The old generator was replaced by `Tools/belltower_menu_boards.py`; planting indices remain stable.
The canonical town meshes lost exactly 264 old menu triangles. All other source records and physics
were preserved. Four retired menu-panel meshes and the obsolete private comparison wrappers/base
meshes were deleted (24 files including metadata/compiled companions). No VMDL still references them.
Before/after PNG evidence and shared materials remain. See `installed.json` and the one-time migration
scripts. `build.py` now stages only the accepted model and its two menu variants.

Comparison and restoration records: `output/belltower/menu-board-v2/`.
