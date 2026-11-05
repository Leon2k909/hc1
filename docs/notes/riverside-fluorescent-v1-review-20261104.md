# Lucky Stop fluorescent fixture v1 – installed

Built after the office rooftop AC, then installed both fittings following explicit user approval on 2026-11-04.
Source/workflow: `Sources/Riverside/fluorescent-v1/README.md`. Resource: `models/props/riverside/fluorescent_v1/fixture.vmdl`.

The two old store ceiling fittings are simple boxes with glowing cards. The candidate has two shaped T8 tubes with dimmer ends,
metal end caps, pins and holders, a folded reflector and thin painted housing, ballast cover/label, catches, screws and mounting tabs.
Six materials; one emissive. Original point lights stay unchanged. LOD triangles 2,770 / 1,594 / 458. Housing and tubes fit inside the
old 48 x 8 x 3.1 in envelope; two mounting posts and plates extend to local Z 4.6 to meet the ceiling across the old 1.5 in gap.
No new physics. First placement `760,-150,145.4`, second `890,-280,145.4`, yaw zero.

Private review background removes exactly 14 original triangles for the first fitting from the current store input, preserving
its other approved upgrades. Original input, ModelDoc and saved scene are hash-protected. Native studio and store-light captures
use isolated scenes/worlds, preserving the current scene and play state. Work/receipts: `output/riverside/fluorescent-v1/`.
Geometry checks pass winding and degeneracy at all three LODs; nine resources compile successfully.

Removed 28 old triangles from the current store input; saved two native ModelRenderers under `Store Ceiling Lights`. Public
store ModelDoc, all pre-existing scene objects, collision and point lights are preserved, including the concurrent Pole Insulators
addition. The generator now emits both model placements; a narrow comparison confirms only fourteen old polygons removed with
identical lights and collision. Twelve legacy/private-background files were archived outside Assets and deleted through the editor.
Saved-map native captures pass with both fittings present and no error models. See installed.json and generator-check.json.
