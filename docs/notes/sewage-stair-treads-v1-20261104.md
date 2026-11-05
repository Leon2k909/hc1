# Sewage main stair treads v1 (2026-11-04)

The lower west flight, from plan `(-925,-765,-100,300,0,160)`, now has twenty open steel grating treads with bearing/cross bars, folded end plates, bevelled yellow grip nosings, end fasteners and a central support. This is render geometry; original step heights, outer stringers, handrails, walking ramps and collision hull are retained.

Installed in `models/maps/sewage/sewage_catwalks.vmdl` and visually approved. Keep both `models/maps/sewage/stair-treads-v1/before.vmdl` and `after.vmdl` variants at the user's explicit request; the new version is active. Native compilation succeeded. Exactly 480 former tread triangles are replaced with 35,292 new triangles; all 21,272 other catwalk triangles retain their exact positions, UVs and normals. Existing physics sections and hull file are unchanged.

`Tools/sewage_stair_treads.py` supplies this one flight; `Tools/sewage_map.py` retains it during future staged generation. Sources and guarded integration: `Sources/sewage/stair-treads-v1/`. Baselines, verification, matched native renders and state-preservation reports: `output/sewage/stair-treads-v1/`.
