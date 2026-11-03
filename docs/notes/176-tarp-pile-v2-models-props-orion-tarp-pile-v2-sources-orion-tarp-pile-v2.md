## Tarp pile v2 (`models/props/orion/tarp_pile_v2`, `Sources/Orion/tarp_pile_v2/`, 2026-10-31)
- Replaced Orion's tarp pile by B3's corner at the user's word after a before/after rendered in s&box ("Yes, install it"). The old one read as a mossy boulder.
- Its folds come from Blender's cloth solver, run at real scale on a load that fills the old collision box. Moving walls tuck its hem in: a sheet thrown on lands wide and tents.
- `Tools/orion_parts.py`'s `tarp_pile()` writes only its old collision box and records a placement, and `orion_map.py`'s `tarp_pile_object()` places the model with no collider. Cover and bullets are unchanged. Players walk over its skirt and sandbags.
- It covers the bollard at plan (236, 40), which stands 5 in outside the box's corner. The bollard still collides. Clearing it would mean moving the pile about 19 in.
- The model only fits this one placement: it was simulated round this load and this bollard.
- `orion_props` no longer draws `oa_tarp`, so it has lost that material slot. The material stays for the deck's and fuel yard's tarps.
- Installed with `install_map.py`, which cuts only the old pile's triangles from the live OBJ, as a plain rerun of `orion_map.py` also changes container corners (see `docs/notes/171`).
- Rollback: `output/asset-improvement-20261030/tarp-pile/before-install/`.
- Checked in an isolated editor scene, not in a match: see the folder's README. Shots are in `output/asset-improvement-20261030/installed-check/orion-bollard/`.
