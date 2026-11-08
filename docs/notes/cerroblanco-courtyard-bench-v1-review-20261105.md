# Cerro Blanco courtyard bench — compiled review candidate, 2026-11-05

The user requested a map model improvement. One bench on the courtyard route, plan
(-250,-800), is rebuilt with chamfered honed stone, a recessed foot, narrow seat supports,
shaped teak boards, photographed grain, separate end grain and flush fasteners. It reuses
the established Veridant bench construction/material helpers instead of duplicating their
texture assets. The existing museum honed-stone material and original bench dimensions remain.

`Tools/cerroblanco_courtyard_bench.py` stages a render-only packed dressing variant. Exactly
70 legacy triangles for this bench are removed; 25,974 unrelated faces and their original
indices/UVs are retained. The replacement adds 8,364 triangles. This is for one bench only;
do not expand it to every bench without considering geometry cost and LODs.

Native editor APIs imported the candidate to
`models/maps/cerroblanco/courtyard-bench-v1/courtyard_dressing.vmdl` and compiled it successfully.
It loads without model or material errors. The live renderer was NOT changed: the user
switched from Cerro Blanco to Gunsmith play during the work. Attempts to target the closed
museum scene failed without mutation. Gunsmith remains running, clean and unchanged.

`output/cerroblanco/courtyard-bench-v1/preview.cs.txt` renders both variants in a temporary
visual copy of the saved museum, with matching camera, lighting and post-processing. It
destroys that scene in finally. Matched before.png/after.png, geometry-checks.json,
preview-check.json and before-install.scene are in the same directory. These are isolated
editor previews, not gameplay captures. No performance or gameplay test was run.

This is ready for visual review and is not installed in the saved map. The original dressing
asset, scene and collision are untouched. On approval, use the native scene tools in the
museum to switch the Dressing ModelRenderer to the candidate, keeping its existing collider.
Update the generator/quality-state integration before treating it as a permanent installation.
No branch was created, and no Git staging, commit or push was performed.
