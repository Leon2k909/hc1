## Stacked tyres v2 (`models/props/railhead/tyre_v2`, `Sources/Railhead/tyre-v2/`, 2026-10-31)
- Replaced the 18 tyres in Railhead's six stacks against the goods shed, at the user's word after seeing old and new side by side in s&box ("New is better").
- The scene's "Stacked Tyres" group holds one model per tyre, renderers only. `railhead_dress_detail.tyre_stack` keeps writing each stack's collision box and records its tyres in `Tools/railhead_tyres.py`. `tyre_stack_old` still builds the old look, for comparing.
- `install_tyres.py` built each old stack with the map's numbers and cut 5,184 triangles a side, matching every corner, from `extinguisher-v2/east-base.obj` and `west-base.obj`, which are what the east and west dress models build from, and from the generator's OBJs. No full map run. Rollback: git for the OBJs and scene.
- Checked in a hidden copy of the map's scene. **Not yet seen in a live match.** See the folder's README.
