## Reef Hall bench v2 (`models/maps/reefhall/bench_v2`, `Sources/ReefHall/bench_v2/`, 2026-10-31)
- Replaced all 8 of Reef Hall's benches at the user's word after comparing both in s&box ("reef hall bench new better"): rotunda 2, galleries 2, lobby 2, tunnel 2. The benches on other maps are their own code.
- `Tools/reefhall_map.py`: `bench()` writes only its seat and two leg boxes, with no faces, and appends a prop. `write_scene` places each as "<Room> Bench <n>" under "Aquarium", with no collider. `mirror_model` turns a placed model end for end on a single flip, because it can only turn, so its front still mirrors.
- **Moved:** both rotunda benches slid 42 in along their length, with their collision, because each ran 27 in into a display case's plinth. They now clear it by about 2 in. The one at polar(205, 420) is now at plan (-362.9, -215.6), and the one at polar(335, 420) at plan (362.9, -215.6).
- **Turned:** the lobby's two are end for end (yaw 180 in `lobby_north`), in the same collision volume, so the plaque side faces the balcony and not the wall 28 in away.
- Installed with `install_map.py`: scratch run, comparison object by object, then copying only what changed. An unchanged run matched every live model and scene object first, so a rerun of this script is safe. It stubs `write_tank_materials` and leaves the radar picture alone.
- The engine showed a fault Blender hid: the slat edges' wear read as regular pale dashes, from fine noise and a hard threshold. It's now long soft runs. Only `bench_color.png` changed.
- Checked in an isolated editor scene, not in a match: see the folder's README. Shots are in `output/asset-improvement-20261030/bench-bollard-check/reefhall/`.
- `rh_laminate` and `rh_gunmetal` stay: the map's other things use them.
