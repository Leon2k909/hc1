# Railhead station clock v1 (2026-11-03)

User approved and requested installation after the matched play-mode comparison.
The central platform clock at plan `(0,1110,240)` now has a smooth rolled case,
recessed double-sided dial, raised indices and hands, shallow glass and hanger
fittings. Its 14:03 time and original collision remain unchanged.

`Assets/models/maps/railhead/railhead_dress_centre.vmdl` imports
`clock-v1/dressing_without_clock.obj` and `clock-v1/station_clock.obj`, with five
private materials plus existing `rw_case_glass`. Only the old clock's 124 render
triangles were removed. The full original ModelDoc physics section is identical;
the original OBJ, other render geometry and scene were not changed.

`Tools/railhead_station_clock.py` retains the approved 16,572-triangle mesh.
`railhead_map.py` appends it at the original central placement and retains the
old housing collision on rebuild. Other clock placements keep their old helper.

The installed public model was checked during actual offline Railhead play with
a local player and no error models. Front/side screenshots use the player's post
effects, normal streaming and matching exposure. The editor's prior scene and
stopped state were restored. No frame-time benchmark was made.

Sources: `Sources/Railhead/clock-v1/`. Receipts and final screenshots:
`output/railhead/clock-v1/installed.json` and `runtime-installed/`.
