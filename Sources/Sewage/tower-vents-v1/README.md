# Sewage pump tower vent housing review

Four louvred breather housings with recessed dark cores, five overlapping
rain-shedding rings, tapered cowls, tie rods, gasket bands and eight-bolt mounting
flanges. Anchors and the existing 848-unit pipe outlets stay aligned; bent elbows
remain in the approved pipework model.

The targeted splice removes exactly 480 original housing faces and preserves
17,400 unrelated tower faces with identical positions, UVs and normals. The
sibling base ModelDoc retains the original physics. The new render-only housings
total 22,112 triangles and reuse the approved pipe finish and crane hardware.

Both models compiled through native s&box MCP. Matched captures are in
`output/sewage/tower-vents-v1/`, made in an isolated temporary scene without
changing the user's active scene or play state. Final viewpoint is inside the
crown railing to expose the housing detail.

Approved and installed in Sewage on 2026-11-04. Temporary side-by-side comparison
objects were removed before saving. The saved scene was checked on disk, and
the original tower model remains available. `install.cs.txt` checks the original source
SHA-256, changes only the tower renderer reference and adds one named vent group,
then saves Sewage and verifies the disk file. The original tower model and source
remain available for reuse/reversion. No whole-map rebuild.

Old lamp retention was separately verified: `models/maps/sewage/sewage_details.vmdl`
and its source OBJ still exist, and the model loads successfully. The saved map
uses `work-lamps-v1/base_details.vmdl` and exactly one new caged-lamp group.
