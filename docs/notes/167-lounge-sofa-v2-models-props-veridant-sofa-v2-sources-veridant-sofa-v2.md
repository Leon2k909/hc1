## Lounge sofa v2 (`models/props/veridant/sofa_v2`, `Sources/Veridant/sofa-v2/`, 2026-10-31)
- Replaced Veridant's 9 lounge sofas at the user's word after comparing both in s&box ("sofa new better"). An upholstered frame with piped loose cushions and two scatter pillows, on a dark plinth, in three models for the map's three lengths: `sofa_84` (6), `sofa_96` (2), `sofa_120` (1).
- The scene's "Sofas" group under Veridant holds the models, renderers only. `veridant_parts.sofa` keeps writing the old collision box, records a placement in `Tools/veridant_sofas.py`, and draws nothing.
- **`veridant_buildings.vmdl` doesn't build from `veridant_buildings.obj`.** It names `lounger-v2/veridant_buildings-base.obj`. `install_sofas.py` cut the old faces there, each corner matched to an old sofa, 96 triangles a sofa, with no full map run. Rollback: git, or `output/asset-improvement-20261030/sofa/before-install/`.
- The scatter pillows stand 0.9 in above the old top of 33 in. Nothing depends on that, and the collision is unchanged.
- LOD switches are 30, 80 and 180, about 14, 39 and 87 m.
- See the folder's README for what's been checked.
