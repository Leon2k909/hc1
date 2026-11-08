# Veridant closed terrace umbrella — applied review, 2026-11-05

Accepted for map use on 2026-11-06, with the old asset retained separately:
`models/props/shared/terrace_umbrella_original_v1/umbrella_original.vmdl`.
That compiled prop has its origin at floor centre, its original burgundy canopy
and metalwork, and the original base collision. `retain_original.py` creates it
without changing the new map canopy.

The terrace's smooth cone/bulb canopy is replaced with gathered cloth panels,
irregular longitudinal folds, fine panel seams, a close-fitting fabric tie,
scalloped lower edges and capped rib tips. The original burgundy materials,
position, height, base, pole and finial remain. The model is static; there is no
cloth simulation or animation.

The scoped patch removes exactly 960 canopy/tie/rib-tip triangles from a copy of
the latest active buildings base and imports 10,740 replacement triangles. Every
unrelated OBJ record and index, all other model imports, the complete physics
suffix, scene and lighting remain unchanged. The earlier banner, reception light
and stair rail upgrades remain active. The narrow umbrella_closed generator hook
retains the new cloth while emitting the original base/pole/finial and collision.

`build.py` stages from guarded backups; `prepare_import.py` imports through the
native editor; `verify.py` checks finite data, unit normals, nondegenerate faces,
unchanged records/physics and earlier accepted imports. The original reference
OBJ is retained here; do not use --refresh-reference after installing the generator
hook, since that option was only used while staging the original canopy.

Matching actual editor viewport frames are
`output/veridant/terrace-umbrella-v1/before.png` and `after.png`, using the same
existing editor camera at terrace eye height, framing and settings. No temporary
cameras, isolated scenes or RenderToBitmap. Backups, stage and verification remain
in the same output directory. Do not import an old stage over newer edits without
a deliberate baseline refresh.
