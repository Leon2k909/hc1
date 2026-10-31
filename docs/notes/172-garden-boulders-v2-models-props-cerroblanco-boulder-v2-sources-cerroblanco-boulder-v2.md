## Garden boulders v2 (`models/props/cerroblanco/boulder_v2`, `Sources/CerroBlanco/boulder-v2/`, 2026-10-31)
- Cerro Blanco's garden has six boulders round bomb site B. The user wanted all three shapes in use, so four are the two new stones and two stay the old faceted shape (`Tools/cerroblanco_boulders.py`'s `NEW` says which).
- The scene's "Garden Boulders" group holds the new ones, each with a `ModelCollider` on the model's own convex hull. `cerroblanco_map` records them and writes neither faces nor a hull for those four.
- The scene draws `quality-v1/cerroblanco_dressing_v2.obj` but collides with `cerroblanco_dressing.vmdl`, so `install_boulders.py` cut the old stones from both, and their hulls from `cerroblanco_dressing_hulls_default.obj`. No full map run. Rollback: git for those files and the scene.
- The old helper `cerroblanco_parts.boulder` also draws the bronze bust upstairs. That's unchanged.
- Checked in a hidden copy of the map's scene: all six stand right, and traces hit each stone's own collision. **Not yet seen in a live match**, and bot cover and the navmesh round the new shapes haven't been checked. See the folder's README.
