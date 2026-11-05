# Zombies ammo case v2

Created 2026-10-30 and refined 2026-11-04. The approved detailed case replaces the previous meshes and textures at the
same asset path, which `ZombiesPowerUp.CreateAmmoCase` already loads. Superseded bake and comparison files have been
removed. The current build is in `output/ammo-case-detail-20261104/work/`, with native captures in `after/`.

## Why this one

Every Zombies match places two Ammo Box buy stations, which show this at 2.5 times the size. It's made at runtime from
`models/dev/box.vmdl`, tinted, with three rifle magazines scaled up to 18 inches standing on top. The same code also makes the
Resupply drop and the stand-in workbench's ammo can, but neither shows today: `DropPowerUps` is off and the real workbench
model loads.

## What it is

A pressed-steel ammunition chest with its lid stood open on two stay cables: bands, a rolled rim, riveted angle-iron
corners, skids, draw latches hanging undone, drop handles with rubber grips, a gasket and a packing list inside the lid.
Inside are 23 loaded curved magazines in a slotted tray (black, tan and grey, a brass round on each, four slots empty) and
three cartons of rounds. Olive enamel, yellow stencils. Lettering is generic, with no brand, real or game. The 2026-11-04
detail pass adds physical curved stiffening ribs, reinforced throats and folded feed lips around the cartridges.

- Triangles after the magazine detail pass: 21,548 / 9,422 / 3,078 (LOD 0-2), up from 11,152 / 3,704 / 1,326.
  The extra geometry is concentrated in the contents, which players see enlarged at the two buy stations.
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
| `ammo_case.py` (`export-meshes` stage) | Replace only the three OBJ inputs; preserve the existing ModelDoc and material resources when the editor is open |
| `verify_ammo.py <root>` | The checks below |
| `render_ammo.py`, `make_sheets.py` | Matched comparison renders and the sheet |

Uses `Sources/Gameplay/capture-flag-v2/build.py` and `paint.py` as an imported toolkit, unedited.

## Checked and not checked

Checked from the files by `verify_ammo.py`: LOD 0 has 0 pieces inside out; every LOD's normals agree with its faces, its UVs are
in the atlas and its bounds are near the old case's; every file the vmdl and vmat name exists; no physics; the code loads it
(`verify_ammo.py <root> installed`).

The 2026-11-04 pass was compiled through the native editor (`asset_compile`, full model and material rebuilds) and
inspected in matched native whole-model and contents captures. Bounds are unchanged, and the model still uses one material.
All three LODs pass the offline winding, normal, UV, bounds, reference and installation checks; 325 LOD0 solids face outward.
The native LOD switching thresholds and a live-match view remain to be checked. The approved native captures are in
`output/ammo-case-detail-20261104/after/`; build/bake data is in `work/`. Old comparison files were removed after approval.

## Known limits

- The before image shows the dev cubes as flat tints, because the engine's dev box can't be read offline. The real ones may look
  worse, with a dev texture on them.
- At 2.5 times the size the buy station gets about 6 px/in. If it looks soft there, either rebake at 4096 or use a smaller scale
  at install. At the old size its magazines stood 45 inches tall, which this replaces with real-looking contents.
- The lid sits 0.75 further back than the old handle did, which is about 2 inches at the buy station's size. Check a station
  that stands against a wall.
