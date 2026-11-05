# Railhead east-yard cable reel — installed 2026-11-04

Approved new geometry with the original wood finish. One reel at plan (1878, -1632, 0.3), axle along e. The public east dressing ModelDoc imports `cable-drum-v1/east_without_drum.obj` and `cable-drum-v1/installed_cable_drum.obj`, with distinct `rh_cd_` material aliases. Existing barrier and extinguisher imports/materials are preserved. Only the old reel's 260 render triangles are removed; unrelated mesh records, ModelDoc physics and the saved scene stay unchanged.

New model: 28,904 triangles, eighteen planks, chamfered rims, open axle bore, metal sleeve/fasteners, twelve continuous cable windings. Original wood material text and texture scale retained; the grain follows the physical boards. `Tools/railhead_cable_drum.py` freezes the approved geometry and mapping; the east-only hook preserves the original box collider. West uses the existing helper.

Sources: `Sources/Railhead/cable-drum-v1/`. Guarded native installation and actual-play receipt: `output/railhead/cable-drum-v1/installed.json`. Saved public model compared against the approved standalone in one session: timber-face mean pixel error 0.557/255, cable 0.401/255. All six materials loaded, one player, zero error models, editor state restored. No full Railhead rebuild or performance benchmark.
