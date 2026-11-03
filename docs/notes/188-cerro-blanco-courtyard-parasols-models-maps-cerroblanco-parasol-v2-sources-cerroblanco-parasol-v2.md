## Cerro Blanco's courtyard parasols (`models/maps/cerroblanco/parasol_v2`, `Sources/CerroBlanco/parasol-v2/`, 2026-11-03)
- Replaced all four over the courtyard's cafe tables at the user's word ("ye good install it"), after a before and after in s&box. The old ones were four flat triangles on a bar, standing on a black box.
- `cerroblanco_parts.parasol` now only records a placement (`Tools/cerroblanco_parasols.py`); the old one is `parasol_old`. `cerroblanco_map.write_scene` adds a "Parasols" group under "Cerro Blanco": renderers only, turned 0, 90, 180 and 270, as the old ones had no collision. The table's collision box stays.
- Installed with `install_parasols.py`, which cuts by position from the live `quality-v1/cerroblanco_dressing_v2.obj`: 66 faces a table (canopy, pole, and the foot box with the table's base disc). The map wasn't rerun, because other sessions' Cerro Blanco changes were uncommitted in the scene and tools.
- The new pole drops through a grommet into a socket tube on a cast base under the table. The table's own post and disc sit inside them.
- `cerroblanco_dressing.obj`, the collider's model, still has the old faces. Its collision is explicit boxes, so they do nothing, and a rerun of the map drops them.
- Checked in an isolated editor scene with the player camera's look, before and after the install, not in a match.
