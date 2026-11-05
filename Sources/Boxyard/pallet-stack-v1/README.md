# Boxyard southwest pallet stack — review, 2026-11-04

Reuses the already approved Spillway `models/maps/spillway/pallet_v2/pallet.vmdl` mesh and wood atlas instead of
creating a competing asset. See `Sources/Spillway/cargo-props-v2/README.md` for the original scan, licence and bakes.
Adapts its dimensions to the existing Boxyard stack at plan(-632,-589):47.24×31.5×17.01 inches, three layers. Alternate
pallets rotate180 degrees for board variation. Source UVs and texture atlas are preserved; normals use the inverse
transpose of the dimension scaling. No new textures, external downloads, image generation or lights.

**Rejected candidate: keep the original active.** The user preferred the original wood texture and requested a
different improvement. No installation is pending. Public map and generator are unchanged. The review replaces410 original faces
with2,892 from three complete detailed pallets, retaining12,468 unrelated prop faces exactly. The other single
pallet under the northwest crate is unchanged. Original full ModelDoc physics, all hulls, saved scene and approved
pipe-stack geometry remain untouched. The new mesh adds no collision; retain the original stack box on acceptance.

`build.py` checks the original face sample against the public mesh, snapshots all inputs and approved asset sources,
and stages private comparison models. `stack.py` freezes the original recipe and adapts the approved mesh for the
new rendering. On acceptance, splice only `removed.obj` / `added.obj`, add the `bxps_wood` material remap to the public
ModelDoc/MTL, and hook only this southwest stack in `boxyard_map.props`; preserve its original collision.

`capture.cs.txt` renders actual old/new samples under matched lighting, camera, framing, exposure and floor.
`context.cs.txt` clones saved Boxyard visual roots and substitutes only the candidate props renderer. Temporary
scenes are destroyed, preserving the user's scene/play state. `verify.py` checks hashes, exact retained faces,
unchanged physics, finite UVs/unit normals, nondegenerate triangles and exact old bounds. Native screenshots and
resource compilation complete review. Evidence and snapshots live in local `review/` on C:; no FPS claim.
