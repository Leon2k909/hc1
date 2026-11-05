# Spillway trench grates — 2026-11-04

Replaced the cargo yard's five flat textured grate quads with fitted metal perimeter frames, separate removable
welded panels, individual chamfered load bars, lower cross ties, captive bolts/washers and lifting eyes. Four
private materials use authored fine galvanized-metal color, normal and roughness maps. No external assets or
image generation. The dark backing masks the existing floor through the openings; the floor is not excavated.
All visual geometry stays within the former rectangle and under one inch above the existing walking surface.

`build.py` stages private comparison assets. The original sample is matched against the published OBJ, then
translated with its original UVs/normals/material retained. `capture.cs.txt` renders before/after through native
s&box with identical camera, floor, light and exposure. `prepare_context.py`/`context.cs.txt` render the public
model inside an isolated copy of Spillway's saved visual roots. Temporary scenes are destroyed. The final
installed context and integration reports check the user's editor/play state without switching their scene.
The first context capture observed Belltower play state changing back to Riverside during rendering;
the capture reported that difference. The script does not switch, save scenes or control play state.

`prepare_install.py` creates a guarded snapshot and exact face splice. Native `install.cs.txt` publishes only
the cargo OBJ/MTL/ModelDoc and two offline generator files. Exactly10 original quad triangles are removed,
37,394 replacement triangles added and39,906 unrelated faces preserved exactly. Complete ModelDoc physics,
all hull sources, saved scene, lighting and nearby props remain unchanged. The cargo generator calls the
retained `Tools/spillway_trench_grates.py` helper instead of drawing the five old quads. No full map rebuild.

Evidence and rollback snapshots: `output/spillway/trench-grates-v1/`. `before.png`/`after.png` are actual native
renders; `context/grate-installed.png` shows the map installation. `verification.json` checks file hashes, exact
retained faces, byte-identical physics, unchanged scene/hulls, finite/nondegenerate triangles, height envelope
and generated geometry matching the installation. `check_public.cs.txt` validates the loaded public model and
all four new material bindings. The unused `before.*` review files are retired outside Assets with a hash
receipt in `retirement.json`; do not rerun the historical review import after retirement. No frame-time benchmark.
