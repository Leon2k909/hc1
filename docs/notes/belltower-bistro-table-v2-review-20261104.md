# Belltower café table v2 — pending review, 2026-11-04

After installing the approved 21 bistro chairs, a native comparison was prepared for the table at
plan `(-600,-170)`. The candidate replaces the crude slab/straight legs with a rolled metal shell,
umbrella aperture, shaped cast pedestal, continuous curved legs, leveling feet and underside supports.
Existing colors/materials, parasol, diameter/nominal height and collision are preserved.

Source: `Sources/Belltower/bistro-table-v2/`; resource: `models/maps/belltower/bistro-table-v2/bistro_table.vmdl`.
LODs: 5,636 / 3,268 / 1,564 triangles. Private old-table removal affects exactly 434 triangles.
All three native model definitions compiled; matched warmed before/after captures restored the editor,
camera/tone state and temporary objects. Saved scene and shared source hashes are unchanged.
Evidence: `output/belltower/bistro-table-v2/{before,after}-final.png` and `review.json` in source.
User approved the native after image and requested removal of the old. All seven tables are installed
with stable scene IDs through `Tools/belltower_bistro_tables.py`; the eastern caf� spacing is preserved.
The native installation removed 3,038 legacy triangles from ten source meshes and saved the scene.
All seven affected VMDLs compiled, eleven private review files were retired, and original physics,
object IDs and editor/play state were preserved. See `installed.json` in the source folder.
