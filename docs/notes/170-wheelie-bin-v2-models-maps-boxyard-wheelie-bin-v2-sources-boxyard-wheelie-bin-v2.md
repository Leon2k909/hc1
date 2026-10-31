## Wheelie bin v2 (`models/maps/boxyard/wheelie_bin_v2`, `Sources/Boxyard/wheelie_bin_v2/`, 2026-10-31)
- Replaced Boxyard's three bins in the middle lane at the user's word after comparing both in s&box ("bins new better"). Green, grey and blue as before, each its own vmdl and vmat on one mesh.
- `Tools/boxyard_map.py`'s `wheelie_bin()` writes only its old collision box into the merged props, and `bin_object()` places the model with no collider, at yaw `heading - 90`.
- Installed with `Sources/Boxyard/ibc_tote_v2/install_map.py`, and rolled back the same way: `output/asset-improvement-20261030/ibc-tote/before-install/` holds what both replaced.
- Checked in an isolated editor scene, not in a match: see `Sources/Boxyard/ibc_tote_v2/README.md`. Shots are in `output/asset-improvement-20261030/installed-check/boxyard/`.
