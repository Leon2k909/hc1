# Kiosk wall fixtures — approved reception housing reused, 2026-11-06

User requested original kiosk lights remain active. Restored original Dressing
render references, deleted both new scene objects and removed generation hook.
New reusable fixture asset remains available but unused in Veridant.

Replaced the two flat kiosk lamp cards with the existing reception fixture,
rotated to face east and scaled to 80%. Includes recessed lens, beveled steel
housing, weather lip and fixings. Existing point-light positions/settings retained.
106 triangles per model; no added collision. Removed exactly eight original
render triangles from Dressing imports; unrelated records and physics unchanged.

Source Tools/veridant_kiosk_wall_light.py delegates to veridant_reception_light.
wall_washer generation hook applies only at the original kiosk placements.
Current scene has two Kiosk recessed wall light objects, saved and verified.
Native compilation/model-load checks passed. New asset
models/props/shared/kiosk_wall_light_v1/light.vmdl; original retained at
models/props/shared/kiosk_wall_light_original_v1/light_original.vmdl.

Matching actual displayed viewport captures and original source/parent snapshots
are under output/veridant/kiosk-wall-lights-v1/. No temporary rendering or
changed lighting/display settings.
