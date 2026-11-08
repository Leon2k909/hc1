# Courtyard CCTV — existing approved Riverdale asset reused, 2026-11-06

One camera at (480,-1000,200), out(1,-1), replaced in a private fitout-fine
variant with the existing approved riverdale_camera construction and all six
existing CCTV PBR materials. No new texture or geometry design is invented. The
original wall anchor and downward aiming vector are retained; the Riverdale
housing/mount projects slightly further from the wall. Exactly 58 old triangles
are removed, 2,832 reused camera triangles added, with all 103,920 unrelated
faces/indices/UVs preserved. No scene, collision, light or public source changes.
Native compile passed and model loads without error.

Before/after are native actual-window screenshots under output/cerroblanco/
courtyard-cctv-v1 at camera(-1050,-530,180), angles(-14,45,0), FOV80, unchanged
lighting and native crop. No temporary scene/camera or Computer Use. Original
Fit-out Detail renderer restored after review, leaving the old camera active.
All source models, materials and variants remain retained pending approval.

User subsequently approved installation. Public fitout-fine now contains the
2,832 reused camera triangles in place of the 58 old ones. Native compile passed.
The generator delegates this placement to cerroblanco_courtyard_cctv. Scene,
physics and every unrelated face remain unchanged; all source assets are retained.
