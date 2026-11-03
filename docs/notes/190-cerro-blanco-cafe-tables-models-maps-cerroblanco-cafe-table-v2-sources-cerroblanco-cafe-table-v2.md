## Cerro Blanco's cafe tables (`models/maps/cerroblanco/cafe_table_v2`, `Sources/CerroBlanco/cafe-table-v2/`, 2026-11-03)
- Replaced all eight at the user's word ("good yeah install"), after a before and after in s&box: four in the cafe, four under the courtyard parasols. The old table was a 20-sided white disc on a six-sided bar.
- `cerroblanco_parts.cafe_table` now records a placement (`Tools/cerroblanco_tables.py`) and keeps the old collision box. The old one is `cafe_table_old`.
- `cerroblanco_map.write_scene` adds a "Cafe Tables" group under "Cerro Blanco", renderers only:
  - `table.vmdl` (the whole table) where no parasol stands.
  - `table_top.vmdl` (top and spider) where `cerroblanco_parasols` recorded one at the same spot. There the parasol's socket tube and base are its pedestal, its spider's hub sits on the parasol's flange, and the parasol's grommet sits on the top.
- The top's surface stays at 29.5, where the fit-out's cups stand.
- Installed with `install_tables.py`, which cuts the old faces from the live `quality-v1/cerroblanco_dressing_v2.obj`: 122 a cafe table, 88 a courtyard one (its disc had gone with the parasols). The map wasn't rerun.
- Checked in an isolated editor scene with the player camera's look, before and after the install, not in a match.
