## Church pew v2 (`models/props/belltower/pew_v2`, `Sources/Belltower/props/pew-v2/`, 2026-10-31)
- Replaced Belltower's 12 church pews at the user's word after comparing both in s&box ("pew new better"). Panelled oak with fielded panels, shaped ends, a hymn rack and red seat pads, about 5,000 triangles against 24.
- The scene's "Church Pews" group under Town holds the models, renderers only. `belltower_map.church` keeps writing the old two boxes per pew as collision and draws nothing, and `Tools/belltower_pews.py` holds where they go. The front is closed because the pews are cover, so the model still matches its collision.
- **`belltower_centre.vmdl` doesn't build from `belltower_centre.obj`.** It names `fountain-ornaments-v2/centre/centre_NNN_<material>.obj`. `install_pews.py` cut the old faces from `centre_013_planks.obj` and `centre_014_planks_dark.obj`, each corner matched to an old pew, 24 triangles a pew, with no full map run. Rollback: git, or `output/asset-improvement-20261030/pew/before-install/`.
- A map run after this writes `belltower_centre.obj` and the scene the same way, but doesn't carry anything into those split OBJs: see the fountain ornaments in Belltower's note.
- LOD switches are 30, 80 and 180, about 14, 39 and 87 m.
- See the folder's README for what's been checked.
