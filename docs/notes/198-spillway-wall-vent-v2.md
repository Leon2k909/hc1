## Spillway's turbine wall vent v2 (`wall_vent_v2`, installed 2026-11-04)

- Approved with the yard hose after matched s&box before/after views. Replaces the first west turbine hall wall vent, 386 old faces;
  the second unit at plan n 1150 is unchanged. New folded-metal housing, two banks of drainable blades, backing mesh, rain cap, bolts,
  service panel and EXTRACT T1 plate, with weathered blue-grey paint and dull alloy blades.
- Asset `models/maps/spillway/wall_vent_v2/wall_vent.vmdl`, 5,096 / 2,548 / 238 triangles, LOD thresholds 30 / 80, one 2048 atlas.
  Scene object `Turbine Wall Vent 1` under `Spillway` at engine `220,1328,25`, no rotation, one renderer and no collider.
- Installed through the native editor's resource API while Spillway was closed; active Riverside document preserved. The saved scene
  differs from its backup only by the new object. Only the 386 selected west OBJ faces were removed; all other mesh lines and both
  west collision hulls were retained. No new collision. The old solid envelope is plan e -1328..-1310, n 170..270, z 25..118.
- `Tools/spillway_map.py` retains that invisible metal box, leaves the second vent drawn, and places the first replacement on rebuild.
  Unrelated service-cabinet changes were preserved. The map generator was not rerun.
- Native validation on engine 26.11.03a: west model compiled; one valid vent and one retained hose; no added colliders or error models.
  Five rays match the old vent front, its top, the floor in front, the unchanged second vent's top and the hose's floor. Three installed
  captures checked. Forced LOD 2 and outward faces checked during review. No match playtest or FPS benchmark.
- Twelve temporary comparison sources/metadata/caches archived, shared `models/compare_old/hidden.vmat` retained. Sources and reruns:
  `Sources/Spillway/wall-vent-v2/README.md`. Native receipts, installed captures and rollback copies:
  `output/asset-improvement-20261030/spillway-vent/`, with originals under `retired/`.
