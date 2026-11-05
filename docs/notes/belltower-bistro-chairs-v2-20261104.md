# Belltower bistro chairs v2 — installed 2026-11-04

User approved the matched native before/after comparison and requested replacement and deletion of the old.
All 21 chairs are installed: 12 in the western café and 9 in the more widely spaced eastern café.
`Tools/belltower_bistro_chairs.py` owns the stable scene group and placements; `belltower_detail.bistro_chair`
delegates to it. Mirrored chair headings use `180-yaw`, retaining their inward-facing layout.
`belltower_cafe_spacing.apply_east` translates the scene props as well as the remaining baked café geometry.

The native install removed 8,064 legacy triangles from eight canonical/partition OBJ sources, preserved
all unrelated bytes and physics, and saved the scene with a 21-child `Bistro chairs` group. All seven
affected current/historic VMDLs compiled successfully. Eleven obsolete private chair comparison files
were deleted with hash-checked backups. Shared materials and original before/after PNG evidence remain.

Resource: `models/maps/belltower/bistro-chair-v2/bistro_chair.vmdl`, LOD triangles 4,376 / 2,376 / 684.
Source and receipts: `Sources/Belltower/bistro-chair-v2/`. Comparison: `output/belltower/bistro-chair-v2/`.
The rebuilt curved green steel frame and timber slats reuse existing materials. Collision is unchanged.
