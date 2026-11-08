# Cafe pastry display — native review, 2026-11-06

Replaces the counter's frameless rectangular glass case with a curved-front case,
continuous swept end frames, fitted tray, formed base, rear tracks and overlapping
sliding glass access panels with connected handles. The existing nine pastries
are retained. Existing museum glazing, stainless and dark frame finishes are
reused; no textures, lights, food, collision or navigation are added.

`model.py` builds the case at its actual counter placement (e628..682,n604..626).
`build.py` stages the private fitout-fine variant. Exactly 22 old case triangles
are replaced with 2,112 new triangles, preserving all 72,468 unrelated faces and
their UVs/indices, including the approved grinder. Appending declarations retains
the source's later vertex blocks. One new pane triangle coincides with an old
triangle; verification compares the complete expected multiset rather than only
counting geometric differences. Bounds, normals and nondegenerate outward faces
pass. Native compilation succeeded and the candidate loads with IsError=false.

Matched native `screenshot_game` window captures are `before.png` and `after.png`
under `output/cerroblanco/cafe-display-v1/`. Actual viewport position (515,-655,64),
angles (8,0,0), FOV80, original lighting/settings, identical native crop. No
Computer Use, offscreen preview or temporary cameras. The renderer was restored
to public fitout-fine after review; no scene was saved or public source changed.
The public model retains the approved grinder, and public dressing retains the
approved bin and both vase upgrades. No LOD/frame-time/gameplay test claimed.

User approved the display and removal of the old case. The 22 old case triangles
were replaced with the 2,112 new triangles in public fitout-fine through native
editor APIs. Native compilation passed. The public ModelDoc, renderer path,
materials, scene, collision, pastries and all unrelated geometry are unchanged.
The generator uses `cerroblanco_cafe_display.build_into` in place of the two old
case boxes. `installed/` retains the original OBJ/ModelDoc. The old case is no
longer drawn. Private review: `models/maps/cerroblanco/cafe-display-v1/fine.vmdl`.
`display.vmdl` is a render-only asset in the prop folder
and retains map-space coordinates; it is not a local-origin reusable prop.
