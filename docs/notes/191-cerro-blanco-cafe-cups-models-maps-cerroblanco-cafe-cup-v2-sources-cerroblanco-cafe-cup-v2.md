## Cerro Blanco's cafe cups (`models/maps/cerroblanco/cafe_cup_v2`, `Sources/CerroBlanco/cafe-cup-v2/`, 2026-11-03)
- Replaced all 16 at the user's word ("ye install them"), after a before and after in s&box. There are two on each cafe table.
- The old cup was a grey 12-sided disc with an open cone on it. The cone vanished from above, because the engine draws only its outside.
- The fit-out no longer draws them. `Tools/cerroblanco_cups.py` places them from the tables `cerroblanco_tables` recorded, so it doesn't depend on the fit-out running first.
- `cerroblanco_map.write_scene` adds a "Cafe Cups" group under "Cerro Blanco", renderers only:
  - `cup.vmdl` (full, a foam heart on crema) at 70 degrees round each table, 6 in out.
  - `cup_empty.vmdl` (drunk, with a teaspoon) at 230.
  - World yaw is the angle less 180, so each handle runs along the table's edge.
- Installed with `install_cups.py`, which cuts 84 faces a cup from the live `cerroblanco_fitout_fine.obj` ("Fit-out Detail"). Another session's changes were uncommitted in that OBJ and in `Tools/cerroblanco_fitout.py`, so the map and fit-out weren't rerun.
- Checked in an isolated editor scene with the player camera's look, before and after the install, not in a match.
