# Firing range shooting bench v2

Created 2026-10-31. **Installed 2026-10-31** at the user's word after an in-engine before and after ("Install it now"): see `docs/notes/179`.

Edinburgh and Shipment aren't played (neither is in `GameUtils.IsMainMenuMap` or `IsMatchReadyMap`), so this comes from the front-end instead: the firing range the gunsmith opens for testing a build (`scenes/gunsmith_range.scene`). Its four benches were a flat top on four square posts, and the player spawns right behind one.

The new one keeps the old 170 x 30 footprint and the 34 high top:

- A laminated oak top, painted from the old bench's own photos in `Sources/GunsmithRange/bench/`, tied with rods and nutted on its edges.
- A welded navy steel frame: three trestles, aprons, a stretcher, diagonals, knee plates, and foot plates with bolts.
- On top, a rubber mat with a diamond tread, two canvas rests, a steel tray with two magazines, a carton and brass, more spent brass, and a worn DOWNRANGE stencil.
- Below, a slatted shelf with two ammo cans and a spare bag, ear defenders on a hook, and an orange FIRING POINT sign on the apron.

No gunshot marks on the top. No real maker's names or anything from another game.

- Triangles: see `verify_bench.py`'s report (about 26k / 6k / 1k), against 224 for one old bench, which had no LODs.
- One material, one 4096 x 2048 atlas, so a stave's 170 inches gets about 18 px/in. `share()` in `bench.py` sets how much of the atlas each island gets by what the player sees.
- `bench.py` builds, bakes and exports; `paint_bench.py` paints; `make.ps1` runs them at idle priority; `verify_bench.py` checks the files.
- `cut_compare.py` writes temporary models to `shooting_bench_v2/compare/`, `capture.py` and `capture_engine.cs.txt` render in an isolated editor scene with the player camera's post stack, and `sheet.py` makes the image.

Not done: not seen in a match or from the player's real camera with a gun in hand. The model has no physics of its own: its collision is in `bench_collision` in `Tools/gunsmith_range.py`.

`install_range.py` did the install and `capture_installed.cs.txt` checks it in s&box. `cut_compare.py` and `capture_engine.cs.txt` were for the before and after, and their temporary models have gone, because the live range no longer has the old bench to cut.

To go back, restore `level()` and `scene()` in `Tools/gunsmith_range.py` from git and rerun that tool. See `docs/notes/179`.
