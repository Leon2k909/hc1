# Boxyard's wheelie bin v2

Created 2026-10-30. Replaced Boxyard's three bins on 2026-10-31, at the user's word after comparing both in s&box ("bins new better"). The comparison sheets are in `output/asset-improvement-20261030/wheelie-bin/final/`, and the model is in
`Assets/models/maps/boxyard/wheelie_bin_v2/`.

## Why this one

The old bin, `boxyard_map.wheelie_bin`, was truly weak: four flat quads, two boxes and two ten-sided wheels in flat paint, with no texture at all. Three of them stand in the middle lane where every player passes.

## What it is

A 240 l moulded bin the same size: a tapered body with pressed panels and ribs, two stiffening bands, a rolled rim, pockets for its wheels, a lifting bar, a lid on four knuckles, a grab bar, and rubber tyres on an axle.
Chalked by the sun, scuffed pale, dirt thrown up from the ground, dark runs from under the rim. Lettering is made up: "BAY 7" sprayed on the front, "07" on the sides, "240 L" moulded in.

- One mesh and one 2048 atlas, about 19 px/in, with a colour map per colour: `wheelie_bin_green`, `wheelie_bin_grey`, `wheelie_bin_blue` (a vmdl and vmat each, as the map's three paints).
- 6,076 / 2,734 / 930 triangles by LOD. The old one was about 60, so three of these are a real cost compared with before, though small for the map.
- Origin on the ground at its middle, +Y its front, its hinge and wheels at -Y.

## In the map

`Tools/boxyard_map.py`'s `wheelie_bin()` writes only its old collision box into the merged props and records a placement, and `bin_object()` puts the model in the scene with no collider, at engine position `(n, -e, 0)` with yaw `heading - 90` (`Frame`'s heading runs from +e towards +n).
It went in with the IBC totes, by `Sources/Boxyard/ibc_tote_v2/install_map.py`. That folder's README has the dry run, the rollback and the engine check.

## Pipeline

`wheelie_bin.py` builds, bakes and exports; `paint_bin.py` paints; `finish.ps1` paints, exports, renders and checks; `render_bin.py` renders the old and new bins where the map puts them, the old ones cut from the merged
`boxyard_props.obj`. Rerunning the build can change the unwrap, so bake and paint after it: the export refuses to run otherwise.

## Checked and not checked

Checked from the files by `verify_bin.py <root> <work> installed`: 0 of its 28 pieces inside out; within 0.25 in of the old bin's size; every file named exists; Boxyard uses it.

Checked in s&box on 2026-10-31, in an isolated editor scene with Boxyard's own light: all three load with no errors, stand where the old ones stood with no colliders of their own, and rays with a clear path stop exactly on the old box, on surface plastic. Shots are in `output/asset-improvement-20261030/installed-check/boxyard/`.

**Not checked:** a real match, so walking into them, bullets and marks, and the player camera's look. Frame time, with three of these against about 180 triangles before. The LOD thresholds (0, 30 and 80, copied from the oil drum) haven't been watched switching.
