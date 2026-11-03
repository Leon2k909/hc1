## Cerro Blanco's cafe chairs (`models/maps/cerroblanco/cafe_chair_v2`, `Sources/CerroBlanco/cafe-chair-v2/`, 2026-11-03)
- Replaced all 20 at the user's word ("looks good", to the install question), after a before and after in s&box: three at each of the cafe's four tables, two at each courtyard table.
- The old chair was a teak slab on four square bars with a board for a back.
- `cerroblanco_parts.cafe_chair` now records a placement (`Tools/cerroblanco_chairs.py`) and keeps the old 14 x 14 x 18 collision box. The old one is `cafe_chair_old`.
- `cerroblanco_map.write_scene` adds a "Cafe Chairs" group under "Cerro Blanco": renderers only, at world yaw = plan yaw less 90, since the model faces its +x.
- Installed with `install_chairs.py`. It cuts 72 faces a chair (`cut_compare.faces_to_cut`) from the live `quality-v1/cerroblanco_dressing_v2.obj`. The map wasn't rerun, because other sessions' Cerro Blanco changes were uncommitted.
- The teak is the forestbase `wood_planks` scan, laid along each slat clear of the scan's butt joints and its tile seam.
- Checked in an isolated editor scene with the player camera's look, before and after the install, not in a match.
- The Bash tool's sandbox refused writes to `Tools/cerroblanco_parts.py` with EINVAL (though it wrote other files), so the tool edits went in through the editor tools.
