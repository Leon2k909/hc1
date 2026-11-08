# Veridant operations banner cloth — applied review, 2026-11-05

Replaces the operations building's flat banner front/back cards with a thin,
smoothly shaded cloth mesh. Its top remains fixed to the existing rod. Broad
static folds, a shallow outward hang and a gently curved lower edge provide
physical shape. This is static model geometry, not a cloth simulation.

The original SECURE / EXPLORE / CONTROL artwork and atlas UV direction are kept.
The canopy, rod, light strip, registered light and physics are unchanged. The
scope removes exactly four old triangles from a copy of the latest active
buildings base and adds 4,896 cloth triangles. Every unrelated OBJ record/index,
all other imports (including the accepted reception light) and the entire physics
suffix are preserved. The original desk and original sign stay active.

`Tools/veridant_operations_banner.py` builds the cloth. The narrow
`veridant_parts.banner` hook retains only this named banner during regeneration;
other banners keep the old implementation. `build.py` stages from the guarded
original snapshot, `prepare_import.py` imports through the native editor, and
`verify.py` checks finite vertices, unit normals, nondegenerate faces, 2.135-inch
minimum clearance from the wall and unchanged unrelated records/physics.

Actual displayed editor frames: `output/veridant/operations-banner-v1/before.png`
and `after.png`, using the same existing editor camera and settings. No temporary
cameras, isolated scenes or RenderToBitmap. A native frame capture caught and
allowed correction of an initially mirrored UV direction; that intermediate
image is not the final after image. Final lettering reads in the original direction.

Before/after and import/verification evidence remain in that output directory.
Do not rerun historical imports over newer assets without deliberately refreshing
the baseline and preserving intervening work.
