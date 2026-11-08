# Orion launch-mount cage lights — review, 2026-11-04

Rebuild of the four7-inch glowing cubes above the launch platform's equipment boxes, at plan(524,2630),
(864,2630), (864,2970), (524,2970), z276. Flanged cast base, moulded base ribs and screws, rounded luminous
diffuser, top rain cap, three guard rings and eight bent guard uprights. Uses only the original `oa_steel`,
`oa_dark` and `oa_lamp_warm` materials: no new textures, external assets, generated imagery or added lights.

**Accepted and installed.** Public pad and generator now use the four new fixtures. The old `before.*` cube-light
comparison assets were removed from game Assets at the user's request; receipt/rollback archive in `review/`.
Original shared materials remain because the new lights and other map assets use them. Render-only change replaces
48 original cube triangles with22,384 new triangles across four fixtures, retaining90,294 other pad faces exactly.
Existing light declarations and original collision stay unchanged. New fixtures keep the7×7-inch footprint and
original top height; bases extend2.5 inches downward to meet the equipment-box tops instead of floating above them.

`build.py` snapshots guarded inputs, requires all old faces to match public mesh coordinates/UVs/normals and stages
private comparison assets. `verify.py` checks hashes, exact retained faces, full physics suffix, finite geometry,
triangle area, original footprint and base/top heights. `lamp.py` freezes the old cube recipe and builds the new
fixtures. On acceptance, narrow-splice pad render faces and hook only these four coordinates in `orion_parts.work_lamp`,
leaving point-light handling untouched. No whole map rebuild.

Native `direct.py SCRIPT` uses one-shot `run_csharp` when persistent connections time out. `capture.cs.txt` renders
actual old/new samples with identical floor, lighting, camera, framing and exposure. `context.cs.txt` clones saved
Orion visual roots and substitutes only the preview pad render model, then destroys the temporary scene. It does
not switch/save the user's document or change play mode. Evidence and snapshots are in local `review/` on C:.
