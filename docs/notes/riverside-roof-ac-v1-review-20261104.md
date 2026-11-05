# Riverside office rooftop AC v1 — installed

Built and approved 2026-11-04. Installed after “ye good, replace with new, delete old and do another”. Source and workflow:
`Sources/Riverside/roof-ac-v1/README.md`. Candidate: `models/props/riverside/roof_ac_v1/roof_ac.vmdl`.

Replaces the office trailer's two-box, 24-triangle AC with a hollow chamfered housing, recessed fan, four blades and motor,
wire guard, louvers, condenser fins, service cover and fasteners, weathered PBR plastic, folded base and a flexible roof curb.
3,796 / 1,940 / 868 triangles. Six materials. Horizontal footprint stays within 0.26 in of the original footprint on each axis;
the roof curb closes the former gap below the box. No added physics. Engine placement: `-640,524.23195,219.5`, yaw zero.

Imported and compiled using the native editor. Studio three-angle captures and office-roof comparisons use isolated worlds/scenes;
the active scene, dirty flag and play state are preserved. Work and receipts: `output/riverside/roof-ac-v1/`.
Geometry checks pass for winding and degeneracy at all LODs. The saved scene and original pad inputs are hash-checked unchanged.

Installed through native scene tools, with exactly 24 matching faces cut from the current pad OBJ. Only the new group and renderer
are added to the saved scene; the pad ModelDoc and physics remain byte-identical. Native saved-map roof captures passed with no
error models. Receipts: `native-install.json`, `installed.json`, `installed-capture.json`. Twelve comparison asset files were deleted
from Assets and archived outside runtime resources under `retired-review-assets/`.

The office's `P.trailer` call now opts into `roof_ac_model=True`; `ROOF_ACS`, `carry` and `roof_ac_objects` preserve that one placement.
Random draws, other trailer details and original collision are preserved. No map regeneration. The old review scripts expect legacy
geometry and should not be rerun after installation. See README for the guarded installation scripts.
