# Shutter thresholds — 27 October 2026

All 28 closed shop shutters have a four-inch recess behind the facade. Their
missing bottom returns exposed the ground behind the shop. A fitted stone
threshold now bridges each recess, overlapping the shutter and jambs slightly
and meeting the cobbles at one eighth of an inch above the ground plane.

`Tools/belltower_shop_thresholds.py` is the one-time migration for the installed
bounded shutter imports. It appends 336 triangles across the two roller-grey
OBJ files, preserving every original byte and using the existing `ashlar_grey`
material. The hall and town ModelDocs, collision sources and scene are untouched.
The `shop` branch of `Tools/belltower_map.py::dress` includes the same thresholds
in future complete generation. No full map regeneration was performed.

`editor/import-shop-thresholds-v1.cs.txt` publishes the staged files through the
native editor, checking source hashes and retaining the current scene's dirty
state. The two native model compiles and current-asset checks passed. Native
close views of both sides of town show closed recesses; camera, tone, scene
objects and unsaved edits were restored. `verify.py` and `installed.json` record
the checks. Evidence and backups are in `output/belltower/shop-thresholds/`.
