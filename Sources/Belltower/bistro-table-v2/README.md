# Belltower café table v2 — review candidate

Created on `codex/belltower-bistro-table-v2-review`, after the user approved all 21 replacement chairs.
Approved by the user and installed in all seven saved caf� positions (four west, three east). Review position: plan `(-600,-170)`, world `(-170,600,0)`.

The original thick, faceted slab and straight square legs are rebuilt as a rolled steel sheet top,
real umbrella aperture and grommet, shaped cast column with collars, four continuous tapered curved
legs, broad leveling feet and curved underside support arms with a mounting ring and fasteners.
It retains the green top, black base, 27.6-inch diameter and 29-inch nominal tabletop height.
The existing parasol, chairs, surrounding geometry and collision are unchanged.
Materials are the existing `iron_green` and `iron_black`; no texture edits were made.
LODs: 5,636 / 3,268 / 1,564 triangles versus 434 original triangles.

The original review builder staged the private table and a west variant with exactly 434 old table faces removed.
All unrelated source bytes are retained. An unchanged fresh production definition is compiled as
`west_baseline.vmdl`, so both views follow the same material-loading path. Both versions are warmed
with discarded renders before capturing the final comparison. Native compilation passed for all
three model definitions. All authored source faces are finite and nondegenerate.

Evidence: `output/belltower/bistro-table-v2/before-final.png` and `after-final.png`.
Both use the same camera, framing, projection, tone parameters and temporary inspection light.
The GPU exposure result was not independently measured. Every capture restored the saved model,
camera/tone state, objects and editor/runtime state. No scene or shared-source hashes changed.
`review.json` records the checks; `audit.py` preserves the evidence and verifies its guards.
Outside the table inspection region, 0.004% of pixels differ by more than 5/255.

Installed through the editor on 2026-11-04. Exactly 3,038 old triangles were removed from ten source meshes;
all seven affected VMDLs compiled. Eleven obsolete private review files were deleted. Existing object IDs,
physics and editor/play state were preserved. `installed.json` records the receipts.
`build.py` now stages only the accepted resource; regeneration uses `Tools/belltower_bistro_tables.py`.
