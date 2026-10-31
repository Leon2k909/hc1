## Station bin v2 (`models/props/railhead/station_bin_v2`, `Sources/Railhead/station-bin-v2/`, 2026-10-30)
- Replaced Railhead's 29 three-bay bins at the user's word after seeing both side by side in s&box ("right bin is better"): platforms, concourse, footbridges, booking hall and cab rank.
- The scene's "Station Bins" group holds the models, renderers only. `railhead_props.bin` keeps writing the old collision box into the dress models and records a placement in `Tools/railhead_bins.py`. `railhead_furniture.bin` still builds the old look, for comparing.
- That collision box is the old one: 24.4 wide against the bin's 40.2. Both old and new stand about 8 past it on each side, so bullets and players go through the bin's outer ends (a raycast 16 off centre reaches the floor).
- **`railhead_dress_east` and `_west` don't build from the OBJs named after them.** Since the extinguisher swap their vmdls name `extinguisher-v2/east-base.obj`, `west-base.obj`, `east.obj` and `west.obj`. A change in the map scripts' OBJs does nothing there until it's carried across.
- The old bins were cut from what's really drawn, matching every corner to the old model, since a cab rank bollard stands inside one bin's bounds: `install_bins.py` for `railhead_dress_centre`, `install_bins_published.py` for the two `-base` OBJs. No full map run, and `placements.json` holds where they were. Rollback: git for the OBJs and scene.
- Metal is scaled to 0.68 in `paint_bin.py`: full metal drew near black in s&box where Cycles showed bright stainless.
- See the folder's README for what's been checked.
