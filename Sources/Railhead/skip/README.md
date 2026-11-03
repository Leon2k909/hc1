# Railhead's skips

**Installed 2026-10-31** at the user's word, on both sides of the map: see `docs/notes/180`. Nothing is committed.

No new art: this is Lowtide's skip (`Tools/lowtide_skip.py`) as a model of its own, at `Assets/models/props/railhead/skip/`, built by `Tools/railhead_skips.py`.

`install_skips.py` does the swap without a map run. Without `--write` it only reports. It can be run again after an interruption, because a file that's already cut is left alone.

To go back, restore these from git and let the editor recompile:

- `Assets/models/maps/railhead/extinguisher-v2/east-base.obj` and `west-base.obj`
- `Assets/models/maps/railhead/railhead_dress_east.obj`, `.vmdl`, and `railhead_dress_west.obj`, `.vmdl`
- `Assets/scenes/maps/Railhead/railhead.scene`
- `Tools/railhead_dress_detail.py` and `Tools/railhead_map.py`

Other sessions' Railhead changes were uncommitted in some of these on the day, so check the diff before restoring. `skip_bin_old` still builds the old skip.
