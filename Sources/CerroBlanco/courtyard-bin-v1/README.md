# Cerro Blanco courtyard hooded bin — installed, 2026-11-06

Rebuilds the one 16-sided cylinder bin on the courtyard/gallery route at plan
(380,-650). It has a smooth rolled stainless shell and rim, an inset service door
with real sector gaps, lock and hinge knuckles, recessed plinth, inner liner and
bottom, and a closed crowned rain hood on two uprights above the real opening.
The same museum stainless/black materials and original 18-inch diameter by
34-inch height envelope remain. Existing Railhead three-bay recycling bins were
checked but do not suit this single round museum bin.

`build.py` stages a private dressing variant and a standalone render prop.
Exactly 46 old bin triangles are removed; all 25,998 unrelated dressing faces and
their original indices/UVs remain. New bin: 3,222 triangles. No old public dressing,
scene, collider, light, navigation or generator changes. The old bench also stays
active, as requested. Geometry checks cover finite vertices/unit normals, correct
winding, nondegenerate triangles, bounds and preserved unrelated faces. Normals
are checked within map_kit's three-decimal OBJ precision.

Native import/compile succeeded and the candidate loads with IsError=false.
Only the live Dressing ModelRenderer was temporarily changed for comparison and
then restored; the scene is unsaved=false. Original collision still uses the
existing envelope. No frame-time, LOD or gameplay test is claimed.

`output/cerroblanco/courtyard-bin-v1/before.png` and `after.png` are native
`screenshot_game` captures cropped by the handler to the same region of the actual
editor window. The same live viewport position (-705,-320,47), angles (20,-48,0),
FOV 80, lighting and display settings were used. Full-window context captures and
validation receipts are retained beside them. No Computer Use, temporary camera,
isolated scene or RenderToBitmap was used.

## Hood-support correction, 2026-11-06

The user spotted unconnected hood supports. The first review's posts were at
radius 7.15 with radius 0.32, ending 0.49 inches inside the liner's inner edge.
They therefore floated over the cavity instead of attaching to the rim.
Posts now sit at radius 8.5 on the actual rolled rim and extend from 25.8 to
32.55, intersecting both the rim at 26.9 and hood underside at 32.25. Capped
stainless mounting sockets at both ends make the attachments visible. The new
bin is 3,654 triangles; its bounds, materials, collider and unrelated faces are
unchanged. Native compile/model-load and geometry checks pass.

`after-joints.png` and `joint-checks.json` in the output directory record the
corrected connection and native close-up. This is the actual editor viewport,
cropped by the native handler, position (-686,-335,43), angles (13,-51,0), FOV 80.
Earlier before/after pictures are historical first-review evidence. The original
map dressing was restored after inspecting the revised candidate.

Retained assets: `models/maps/cerroblanco/courtyard-bin-v1/dressing.vmdl` (private
packed review) and `models/props/cerroblanco/hooded_bin_v1/bin.vmdl` (render-only
standalone, ground origin).

## Approved installation

The user approved the corrected bin and asked to delete the old one. Exactly 46
old cylinder faces were removed from the public quality-v1 dressing OBJ and the
3,654 corrected bin triangles installed in their place through the native editor.
The public ModelDoc, material slots, renderer path, all 25,998 unrelated faces,
scene and entire collision remain unchanged. Native compilation succeeded.
`Tools/cerroblanco_hooded_bin.py` contains the approved model construction;
`cerroblanco_parts.litter_bin` applies it only at (380,-650), retaining the exact
old 16-sided collision hull. The other courtyard bin is unchanged. Quality-state
already retains the same public renderer path, so no patch/export is required.
`installed/verification.json` records source hashes, old-face removal, generator
parity and collision parity. Original visual geometry is no longer active at the
upgraded placement; historical review and backup files are retained for reference.
