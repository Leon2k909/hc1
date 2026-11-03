# Ares control-room utility door

2026-11-03: replaced the scaled cargo-door leaves with a bespoke single utility
leaf, made for the east control-room entrance. No cargo-door model is used.

`build_utility_leaf.py` stages the source mesh; native editor import and compilation
install `models/maps/ares/control-room-door-v1/utility_leaf.vmdl`. The 748-triangle
leaf uses four existing materials, a shallow pressed panel, compact pull and kick
strip. It is 65 by 98 inches, with a 3-inch steel shell.

The assembly stands at world (156,-960,0) and covers the 64 by 96 opening. It reuses
AutomaticSlidingDoor with one moving BoxCollider, no right leaf, and 66 inches
of travel towards the solid rear-wall pocket. Slim fixed trim covers the edges.
`door.json` is retained by `Tools/ares_sliding_doors.py` on map regeneration.

Native verification: 25 closed perimeter traces, 12 clear open passage traces,
and leaf bounds entirely inside the rear-wall pocket. Closed view inspected in
the editor; source model compiled successfully. No live match was run.

The preceding cargo-door assembly is preserved in `before-utility-door.json`.

## Refined version 2 (2026-11-03)

The installed leaf is now `models/maps/ares/control-room-door-v2/utility_leaf.vmdl`.
Reproduce with `build_utility_leaf_v2.py`. It has 14,712 triangles, genuine rounded
panel and handle recesses, a rounded stainless finger pull, and a metal kick plate
with four small fasteners on each face. The first plain mesh remains archived.

The private enamel material uses `materials/ares/control-room-door-v2/enamel_color.png`,
a 1024-square albedo made from built-in ImageGen. Original source image:
`generated-enamel-v2.png`; full generation prompt: `texture-v2-prompt.txt`.
Existing enamel micro-normal and steel/rubber materials are reused. No shared
material was changed. No lights, shadows, labels or hardware are baked in the albedo.

Native material and model compilation passed. Front and angled editor captures were
inspected, 25 closed perimeter checks and 12 open passage checks passed, and the
saved scene plus map-generator source both reference the refined model.
