# Boxyard RTG cranes — approved and installed

Approved 2026-11-04. All three saved cranes now use standalone LOD models:
`models/props/boxyard/gantry_crane_v1/gantry_01.vmdl`, `gantry_02.vmdl`, `gantry_03.vmdl`.
Original positions/yaws and yellow/yellow/red colours are retained. Labels now identify cranes 01/02/03.
Shared geometry LODs are 34,660 / 21,888 / 6,188 triangles; no added collision or lights.

Exactly 768 original crane triangles were removed from the current backdrop OBJ. Every other face and
all vertex/UV/normal records were retained. The backdrop ModelDoc is byte-identical. The saved scene's
only semantic changes are three added renderer nodes. No whole-map generator was run.
The original block generator, private before assets and obsolete comparison snapshots were deleted.
Shared legacy paint resources remain because they may be used elsewhere.

`Tools/boxyard_gantry.py` is the pure geometry builder. The map writer registers CRANES and emits their
standalone instances rather than embedding the old blocks. `build.py` stages the meshes/materials and
three labelled colour variants. `verify.py` checks installed nodes/resources and all LOD geometry.

The complete rebuild includes articulated wheel bogies, tyres/hubs, tapered/braced portals, twin girders,
trolley/hoist hardware, catwalk/rails/ladder/cage, framed operator cab and container spreader.
Native map-position captures load all three variants and backdrop/yard/container/prop models successfully.
The installed cranes expose three LODs; the old review directory is absent.

Evidence: `output/boxyard/gantry-crane-v1/installed-verification.json` records the exact installation diff;
`installed/validation.json` and images record native model loading and placement. A separate shared-editor
task changed scene/play state during the isolated capture; this task did not reset that state.
Earlier launch/endpoint failures recovered without closing the user's subsequently active editor.
No live-match or frame-time benchmark was run. Review distant LOD cost if profiling identifies a problem.
