# Range target v2

Created 2026-10-30. The user compared it with the old target and told me to replace it, so the firing range and
`Tools/gunsmith_range.py` now use it and the old `range_target` model is gone from Assets (rollback: `output/asset-improvement-20261030/range-target/retired-range_target/`, and git
history). The `range_*` materials stay: the range's own model uses them.

The old target was a flat cut-out with flat colours. This one is a hardened steel silhouette, freshly sprayed, behind a
stencilled deflector plate on a welded trolley whose wheels reach the range's track plate (the old model floats 1.9
above it). Its outline, aiming marks and colours are the old target's. It carries no bullet marks, at the user's word: it's there for players to shoot, so any marks should be theirs.
Physics is copied word for word, so hits, the
z = 59 headshot line and the stem's collision don't change. `FiringRangeTarget`'s hit flash still works: the material's
tint amount is 1, as the old ones' were.

- Triangles: 9,254 / 2,850 / 512 (LOD 0-2), against 206 and no LODs. One material, one 2048 atlas, about 19.5 px/in.
- `target.py` builds, bakes and exports; `paint_target.py` paints; `render_target.py` renders the comparison;
  `verify_target.py` checks the files. They use `Sources/Gameplay/capture-flag-v2/`'s `build.py` and `paint.py` as a toolkit.
- Rerunning the build can change the unwrap, so bake and paint after it. The export refuses to run otherwise.

Still owed: it has never been compiled or seen in s&box (the images are Cycles renders, which flatter any asset). Open the
range, shoot it, and check the materials, hit flash, LOD thresholds (30, 90, estimates) and how the wheels look in
moving-target mode.
