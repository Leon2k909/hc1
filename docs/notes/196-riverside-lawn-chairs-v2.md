## Riverside lawn chairs v2 (2026-11-03)

- Installed all four after the user's approval: green in the yard, green and red on the porch, green on the raised trailer's roof.
- Models: `models/props/riverside/lawn_chair_v2/lawn_chair_{green,red}.vmdl`. Woven webbing, splayed aluminium frame, plastic arms/glides, dirt and weathering. LOD triangles 27,696 / 8,040 / 1,508.
- `Sources/Riverside/lawn-chair-v2/install_chairs.py` removed exactly 68 old face lines per chair from `riverside_dressing.obj`, `riverside_terrace.obj` and `riverside_levee.obj`. No collision changes. Backups and installed captures: `output/asset-improvement-20261030/lawn-chair/`.
- Created and serialized the objects inside the editor, saved Riverside through `Editor.Asset.SaveToDisk`, without changing the active scene or play state. Native isolated renders checked all four actual placements; every model loaded successfully, zero chair colliders. No live match check.
- `riverside_parts.LAWN_CHAIRS`, `lawn_chair`, `carry` and `riverside_map.lawn_chair_objects` preserve the placements on future rebuilds. Do not regenerate the whole map for installation (shared kit drift, note 094).
- Native save added light/probe version metadata and made the probes' existing realtime mode explicit; all other prior scene values are unchanged.
