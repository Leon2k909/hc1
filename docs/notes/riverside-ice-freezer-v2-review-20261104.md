## Riverside ice freezer v2 — archived duplicate, 2026-11-04

Superseded by the user-approved `ice-cabinet-v1` installation in “Show project in the editor”. This version was never installed; its private assets have been archived outside Assets. Preserve the approved version. Historical review details follow; the next candidate is the speed-limit sign.

- Next model after installation of the 54 approved sandbags. **Not installed.** Existing Lucky Stop freezer remains in the map.
- `models/props/riverside/ice_freezer_v2/ice_freezer.vmdl`: insulated door, gasket, raised ICE header, metal hinges/screws, curved pull and latch, compressor louvres, rubber feet and panel seams. Three LODs: 2,616 / 1,464 / 460 triangles, one 2k PBR atlas with header glow. Original procedural textures and generic lettering; no external assets.
- Cabinet is 38 × 30 × 60 inches, origin at ground centre, canonical front engine +X. Proposed position `622,-160,20`, yaw 180. Handle projects beyond original box. Retain the original simple metal collider and porch light if later approved.
- Matched native s&box captures use identical camera/exposure and a temporary inspection light. Comparison background hides exactly 14 old faces only in a separate render-only store copy. Production scene/store hashes are unchanged. Geometry, winding, UV and normal-map checks passed; model loads without errors. No gameplay/LOD playtest.
- Recipe: `Sources/Riverside/ice-freezer-v2/README.md`. Evidence: `output/asset-improvement-20261030/riverside-ice-freezer/before-after.png`. Do not regenerate the full Riverside map or disturb the concurrent drinks-fridge/pole-transformer work.
