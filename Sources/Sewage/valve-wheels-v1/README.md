# Sewage valve wheel review

Four cast red handwheels with smooth rims, five swept dished spokes, packed
spindle glands, machined washers, hex retaining nuts and spindle keys.
The wheel plane moves 26 units along its existing spindle axis to clear the
pipe body. The first wheel moves 5 units inward for wall clearance.

Targeted splice removes exactly 2,272 original wheel faces and preserves
all 51,582 other pipework faces with their original positions, UVs and normals.
The original model and OBJ stay untouched. The copied base ModelDoc retains
the original physics; the scene's ModelCollider is unchanged by installation.
New wheel geometry is 20,992 triangles across four wheels, render only.
Materials reuse Riverdale's red valve enamel and Sewage's crane steel/dark.

Both preview models compiled successfully in the native editor.
Matching native captures are in `output/sewage/valve-wheels-v1/`.
Capture uses an isolated temporary scene, preserving the live scene and play state.
The first camera pass exposed the buried original mounting; the final matching
pair shows the corrected spindle clearance from a nearby unobstructed viewpoint.

Approved and installed in Sewage on 2026-11-04, with the saved scene verified on disk.
`install.cs.txt` checks the original
pipework SHA-256 before updating its renderer reference and adding a separate
wheel renderer, then saves only Sewage and verifies the resulting disk file.
No full map rebuild and no change to the approved pipe texture or flange details.
