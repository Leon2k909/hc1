# Reef Hall upper-office workstation — review, 2026-11-04

Rebuild of the desk at plan (1960,780), yaw180, floor208, in the control room's upper glass office. The second
desk and both existing chairs are unchanged. Rounded laminate worktop and edge, steel cantilever feet with pads,
underframe and cable tray, twin thin display housings on articulated arms with VESA plates and cables, keyboard
with individual keys, palm rest, mouse and mat. Reuses approved Reef Hall materials and telemetry screen artwork.
No external assets, new textures, image generation or lights. Desktop footprint and display envelope are retained.

**Accepted and installed.** The public model and generator now use the new workstation at this single placement.
The original desk remains reusable as `models/maps/reefhall/office-desk-v1/legacy_workstation.vmdl`; keep its
`before.*` source assets and frozen original generator for future improvements, as explicitly requested by the user.
`review/retained-variants.json` records both versions. `desk.py` builds a local
workstation and emits it in map coordinates; `original()` freezes the original desk and screens without the chair.
`build.py` requires all96 old desk faces to match the public OBJ exactly. The preview replaces them with5,406 faces,
preserving130,630 unrelated faces exactly. The full public ModelDoc physics suffix is copied unchanged; no collision
is added. The native installer narrowly spliced `review/removed.obj` / `added.obj`, retained all original hulls,
and added a generator hook for this single placement while preserving the original chair code and desktop collider.

`review/` on C: holds guarded snapshots, hashes and native receipts. `capture.cs.txt` renders the actual original and
candidate face samples with identical camera, framing, floor, lighting and exposure. `context.cs.txt` clones saved
Reef Hall visual roots into an isolated scene and substitutes only the candidate control-room render model. The
user's scene/play state is preserved; temporary scenes are destroyed. All3 preview models compiled and loaded
without errors. Geometry, exact retained faces, resource hashes, physics suffix and scene/hull hashes checked.
No full map rebuild, envmap bake, playtest or frame-time benchmark.
