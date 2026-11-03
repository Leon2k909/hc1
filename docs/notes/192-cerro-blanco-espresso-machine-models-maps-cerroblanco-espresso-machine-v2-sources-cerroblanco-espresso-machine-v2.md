## Cerro Blanco's cafe espresso machine (`models/maps/cerroblanco/espresso_machine_v2`, `Sources/CerroBlanco/espresso-machine-v2/`, 2026-11-03)
- Replaced at the user's word ("Install it"), after a before and after in s&box. It stands on the cafe counter at plan ( 575, 615 ), on the top at 42.
- The old machine was a steel box with two chrome stubs and black sticks, and open cones for cups.
- `cerroblanco_fitout.cafe` no longer draws it. `Tools/cerroblanco_espresso.py` places the model, and `cerroblanco_map.write_scene` adds it as "Espresso Machine" under "Cerro Blanco": a renderer only, as the old one was drawn only.
- **Facing:** its working front (groups, wands, gauges, drip tray) faces plan north, world yaw 0, toward the barista behind the counter, as real cafes set them. The customers see its stainless back. The user installed it facing that way.
- Installed with `install_machine.py`, which cuts the old machine's 318 faces from the live `cerroblanco_fitout_fine.obj`. Another session's changes were uncommitted in that OBJ and in `Tools/cerroblanco_fitout.py`.
- Checked in an isolated editor scene with the player camera's look, before and after the install, not in a match.
- A capture without a warm-up drew its first view green-cast and the dials blank, while another session's play ran in the editor. Warm up the first view before trusting a render.
