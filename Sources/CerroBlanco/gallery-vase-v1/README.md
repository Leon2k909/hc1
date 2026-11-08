# Cerro Blanco East Hall display vase — installed, 2026-11-06

Rebuilds one eye-level display vase at plan (700,-300), on its existing 40-inch
white plinth beside the East Hall player route. The former 12-sided straight
cylinder with a flat black top becomes a turned red vessel with a grounded foot,
rounded body, shoulder, narrow neck, rolled lip and continuous hollow interior.
The existing museum red material is reused. No matching installed/pending vase
upgrade was found in the source/prop audit. Footprint and top height stay within
the original 12-inch diameter by 14-inch height envelope.

`build.py` stages a private dressing variant and render-only standalone vase.
Exactly 34 old vase triangles are removed and 6,240 added. All 29,618 unrelated
dressing triangles and their original indices/UVs remain, including the newly
approved hooded courtyard bin. The plinth, scene, colliders, lights, materials,
navigation and public dressing source are untouched. The vase never had separate
collision; none was added. This is a single trial, with no LOD/frame-time claim.

Native import/compile succeeded and the candidate loaded with IsError=false.
Geometry checks confirm finite vertices, unit normals within three-decimal OBJ
precision, outward nondegenerate triangles, bounds and preserved unrelated faces.
The live Dressing renderer was temporarily changed for the captures then restored
to the public dressing, which contains the approved bin. No scene save was needed.

`output/cerroblanco/gallery-vase-v1/before.png` and `after.png` are matched native
`screenshot_game` captures of the real editor viewport, cropped by that handler
to the same window rectangle. Position (-342,-658,64), angles (14,-45,0), FOV 80,
lighting, material and display settings are identical. No Computer Use, temporary
camera, isolated scene or RenderToBitmap. Artifacts/checks are retained beside them.

Assets: `models/maps/cerroblanco/gallery-vase-v1/dressing.vmdl` (private review),
`models/props/cerroblanco/gallery_vase_v1/vase.vmdl` (render-only local-origin prop).
The user approved installation and removal of the old vase. Exactly 34 cylinder
triangles were removed from the public quality-v1 dressing OBJ, and the 6,240
new vase triangles installed through the native editor. The public ModelDoc,
renderer/material slots and scene path remain unchanged; native compile passed.
The approved bin and all other dressing records are preserved.

`Tools/cerroblanco_display_vase.py` contains the approved model function, used by
the scoped `display_plinth` hook only at (700,-300), h=40. Existing plinth collision
is identical. `installed/verification.json` records hash guards, old-face removal,
generator parity and collision parity. Other display vases remain unchanged.
No scene save/quality-state update was required because the public renderer path
and all scene components remain unchanged. The old cylinder is no longer active
at the upgraded placement; historical review/backup assets are retained.
