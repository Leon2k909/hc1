# Belltower picnic tables — installed 2026-11-04

User approved the table and requested replacement/deletion of the old version. All ten picnic tables in the mirrored beer gardens now use the approved model (4,244 triangles each), retaining dimensions, wood finishes and original cover collision.

The four live bounded wood imports lose all 600 old table faces. Both canonical town OBJ/MTL caches also remove the old geometry and include the replacements. Both public ModelDocs add `picnic-table-v1/installed_{west,east}.obj` with distinct `bt_pt_` material aliases, preserving all prior imports and the full physics suffix. No full regeneration, scene or lighting edits. Streaming splices preserve unrelated source lines.

`Tools/belltower_picnic_table.py` reproduces the approved geometry/UVs; the production map's shared `picnic_table()` now calls it and retains the old collider. Both mirrored halves regenerate the new design. The obsolete preview ModelDoc and its base meshes were reference-audited and removed from Assets, including generated metadata/compiled preview data. Output archives retain the original sources for reproducibility.

Sources: `Sources/Belltower/picnic-table-v1/`. Native install and cleanup receipts: `output/belltower/picnic-table-v1/installed.json` and `obsolete-preview-cleanup.json`. Both public models/materials loaded; west/east garden captures passed in actual play with one player, zero error models and the original editor state restored. No performance benchmark.
