## IBC tote v2 (`models/props/boxyard/ibc_tote_v2`, `Sources/Boxyard/ibc_tote_v2/`, 2026-10-31)
- Replaced Boxyard's two totes by the north-east stack at the user's word after comparing both in s&box ("ibc new better"). Valve at the same end as before.
- `Tools/boxyard_map.py`'s `ibc()` writes only its old collision box into the merged props, and `ibc_object()` places the model with no collider, as the drums do. Cover and bullets are unchanged.
- `install_map.py` covers the totes and the bins: a scratch run, then a comparison of each file, of the props model material by material and of the scene object by object.
- Rollback: `output/asset-improvement-20261030/ibc-tote/before-install/` holds the props files and the scene as they were. The old materials stay in Assets.
- Checked in an isolated editor scene, not in a match: `capture_installed.cs.txt` with `check_config.py`. See the folder's README for what that covered and what it didn't. Shots are in `output/asset-improvement-20261030/installed-check/boxyard/`.
