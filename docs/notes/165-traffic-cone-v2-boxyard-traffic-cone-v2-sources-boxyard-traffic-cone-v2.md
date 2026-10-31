## Traffic cone v2 (`models/maps/boxyard/traffic_cone_v2`, `Sources/Boxyard/traffic_cone_v2/`, 2026-10-31)
- Replaced Boxyard's five cones at the user's word after seeing both in a real match, with new collision from the new shape (`cone_collision` in `Tools/boxyard_map.py`). Railhead's and Riverdale's cones are their own code and aren't touched.
- The props model holds only the cones' hulls, and the scene places the model with no collider, as the drums do.
- The old knocked-over cone's axis climbed, so its tip hung about 13 in up inside a crate. The new one rests on the ground, 3 in back along its heading.
- Checked in a real match: rays and walking into them with `dev_force_move`. See the folder's README, including what wasn't checked.
- To apply a map script's change, `install_map.py` is the safe route: scratch run, then a comparison object by object. Move files over with `os.replace`: a plain overwrite of the open scene failed with `Errno 22` and left the map half installed.
