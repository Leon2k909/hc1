# Cafe pan dulce — native review, 2026-11-06

The existing nine low-poly cafe pastries are rebuilt as rounded pan dulce with
hand-shaped outlines, scored sugar-crust domes and rounded baked bases. The same
seeded tray placements and approximately original footprint/height are retained.
Scoring is actual surface relief with a second crust material; no lighting,
camera finish, textures or physics are added. Bases meet the installed tray and
the dome/lower side use the same perturbed boundary radius, avoiding open seams.

`build.py` replaces exactly 540 old pastry triangles with 16,416 new triangles
in a private fine-model variant. All 74,040 unrelated faces and their indices/UVs
remain, including the approved grinder and newly installed curved display case.
Geometry verification checks finite/unit normals, nondegenerate outward faces
and exact expected face multisets. Native compile passed, candidate IsError=false.
The dense geometry applies only to this nine-piece review; no LOD/performance
claim is made, and repetition elsewhere should use a reduced mesh.

Matched actual viewport `screenshot_game` captures are before.png/after.png in
`output/cerroblanco/pan-dulce-v1/`, native crop at position (552,-650,64), angles
(17,0,0), FOV80 and unchanged map lighting/display settings. No Computer Use,
offscreen scene, temporary camera or RenderToBitmap. After capture the public
Fit-out Detail renderer was restored, retaining the old pastries pending approval.
The user subsequently approved the pastries and removal of the old meshes.
Native editor APIs installed the 16,416 pastry triangles in public fitout-fine,
removing the 540 old triangles and adding the crust-material remap. Compilation
passed. `cerroblanco_pan_dulce.build_into` replaces the legacy pastry loop in the
generator. `installed/verification.json` verifies the full expected face multiset,
generator triangle parity and no added collision. All unrelated fitout geometry
and the scene/renderer paths are retained. Old pastry geometry is no longer drawn.
