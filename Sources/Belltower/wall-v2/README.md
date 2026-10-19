# Belltower town wall, 18 October 2026

The material described here is superseded by `../wall-v3/README.md`. The buried
town-wall geometry cleanup and its validation remain current.

The original small rubble scan produced a strong repeated pattern of pale stones
and dark joints on the fortifications. The updated `rubble` material uses the
existing original CC0 `medieval_blocks_03` colour, normal, roughness and AO maps.
A 2.75 metre tile gives approximately 55 cm courses. Lower saturation, reduced
AO and continuous world-space weathering soften the pattern without shifting UVs
or introducing tile boundaries. Its nearly flat displacement map does not justify
a parallax ray march, so relief depth is zero for this material. The cobblestone
material retains its existing parameters; new shader controls default to their
previous response.

`Tools/belltower_quality_materials.py` owns the material definition and
`Sources/Belltower/shaders/belltower_relief.shader` owns the shader. Both were
published through native editor scripts, then compiled successfully before the
geometry import. The checked material capture is
`output/belltower/quality/wall-v2/material-v1.png` and its original comparison is
`before.png` in the same folder.

`Tools/belltower_wall_cleanup.py` removes town-wall render faces inside the
playable ground. It follows the street at 0, the garden at -48, and the spawn
road ramp between them. Visible walls overlap the floor by two inches. Wholly
buried faces are removed, while the blocked gate's stone threshold and the
outward west, north and south foundations are retained. Collision is untouched.
`Tools/belltower_map.py::town_walls` runs this cleanup during normal rebuilds.

The one-time integration tool `Tools/belltower_stage_wall_cleanup.py` matches the
original town-wall triangles against backups of the existing west/east OBJ files,
then changes only those faces. This preserves unrelated edits in the large map
meshes. Its original inputs live under
`output/belltower/quality/wall-v2/before-assets`. A normal full model rebuild uses
the map generator directly and does not require these integration backups.

The checked native geometry import removed 4,444.65 square metres of hidden
surface across both halves. Following the floor profile adds 16 triangles to the
two-million-triangle source meshes. This is hidden-surface cleanup, not a measured
FPS improvement. Polygon checks confirmed positive winding and a retained gate
threshold; file checks confirmed identical scene, ModelDocs and collision hulls.
The native import and all captures preserved the selected document and running
Ares match.

Geometry manifests, before captures and verification are under
`output/belltower/quality/wall-v2`. After the editor recovered from a long hotload,
native `asset_info` confirmed both models and the material compiled and up to
date. Final native captures check the main wall, both mirrored ramp joins, the
underfloor corner, and the preserved exterior. The runtime material also loads
without an error. No gameplay scene or collision resources were changed.
