# Zombies ammo case v2

Created 2026-10-30. The user compared it with the old case and told me to install it, so `ZombiesPowerUp.CreateAmmoCase` now loads it,
falling back to two plain boxes with a log warning if the model doesn't load. The comparison is
`output/asset-improvement-20261030/ammo-case/ammo_case_before_after.png`.

## Why this one

Every Zombies match places two Ammo Box buy stations, which show this at 2.5 times the size. It's made at runtime from
`models/dev/box.vmdl`, tinted, with three rifle magazines scaled up to 18 inches standing on top. The same code also makes the
Resupply drop and the stand-in workbench's ammo can, but neither shows today: `DropPowerUps` is off and the real workbench
model loads.

## What it is

A pressed-steel ammunition chest with its lid stood open on two stay cables: bands, a rolled rim, riveted angle-iron
corners, skids, draw latches hanging undone, drop handles with rubber grips, a gasket and a packing list inside the lid.
Inside are 23 loaded curved magazines in a slotted tray (black, tan and grey, a brass round on each, four slots empty) and
three cartons of rounds. Olive enamel, yellow stencils. Lettering is generic, with no brand, real or game.

- Triangles: 11,152 / 3,704 / 1,326 (LOD 0-2). The old case is 7 cubes plus three magazines of 6,000 triangles each, so
  about 18,000 with no LODs: this is cheaper as well as better.
- One material, one 2048 atlas, about 16 px/in.
- Same origin. Bounds are x -9.75 to 7.76, y -12.71 to 12.71, z -10 to 18.46, against the old -9 to 8, -12.5 to 12.5 and -10 to 20.
- No physics, as before: the old case has only renderers, and the buy station has its own box collider.

## Pipeline

`run.ps1` runs Blender in the background at idle priority, 4 threads. Rerunning the build can change the unwrap, so bake and
paint after it: the export refuses to run otherwise.

| Step | Does |
| --- | --- |
| `ammo_case.py` (`run.ps1 build,bake`) | Meshes, UVs, LODs; position, normal, finish and AO bakes |
| `paint_ammo.py <work> <materials>` | Every map, in numpy, with wear worked out in 3D |
| `ammo_case.py` (`run.ps1 export`) | OBJs, vmdl, vmat |
| `verify_ammo.py <root>` | The checks below |
| `render_ammo.py`, `make_sheets.py` | Matched comparison renders and the sheet |

Uses `Sources/Gameplay/capture-flag-v2/build.py` and `paint.py` as an imported toolkit, unedited.

## Checked and not checked

Checked from the files by `verify_ammo.py`: LOD 0 has 0 pieces inside out; every LOD's normals agree with its faces, its UVs are
in the atlas and its bounds are near the old case's; every file the vmdl and vmat name exists; no physics; the code loads it
(`verify_ammo.py <root> installed`).

**Not checked: it has not been seen in s&box.** The images are Blender Cycles renders with ray-traced light, which flatter any
asset. An open editor may compile the files when it sees them, so look for `_c` files before saying it was never compiled.
Still unknown in the engine: the materials and the LOD thresholds (estimates).

## Known limits

- The before image shows the dev cubes as flat tints, because the engine's dev box can't be read offline. The real ones may look
  worse, with a dev texture on them.
- At 2.5 times the size the buy station gets about 6 px/in. If it looks soft there, either rebake at 4096 or use a smaller scale
  at install. At the old size its magazines stood 45 inches tall, which this replaces with real-looking contents.
- The lid sits 0.75 further back than the old handle did, which is about 2 inches at the buy station's size. Check a station
  that stands against a wall.
