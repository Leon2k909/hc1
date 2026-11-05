# Cash Grab bag v2

Created 2026-10-30. The user compared it with the old bag and told me to install it, so `cash_bag.equip` and the mount, first-person and world prefabs
now use it. The 2026-11-04 hardware pass was also approved and remains installed at the same paths. Its old gallery model and label, superseded build folder,
and before/comparison files were removed. Current build inputs and approved engine captures are in `output/cash-bag-detail-20261104/work` and `after`.
The original dev bag is a shared cloud package; its package reference remains because `ZombiesPowerUp`'s Point Boost still loads it by name.

## Why this one

It's the objective of Cash Grab, which `GameMode.Info.cs` offers on every main-menu map: held in first person, carried on the back and lying
where it's dropped, with a marker on it. The old model is `models/dev/duffelbag/dufflebag_money`, a cloud dev model of 1,464 triangles on
`materials/dev/white_flat`, so in the game it's a plain white shape.

## What it is

A faded olive canvas duffel: piped end panels, a scuffed base panel, stitched seams, a zip standing open along the top on bundles of banknotes
in paper bands, two web handles lying either side of the opening with rubber wraps, and a slack shoulder strap on two D-rings.

- The banknotes are invented: a green "100" with a rosette, no portrait, country or issuer. They copy no real currency.
- Same origin, on the ground under the bag's middle, so the first-person, carried and dropped prefabs hold it the same way. Bounds are x -6.47 to 6.62,
  y -14.52 to 14.12, z 0 to 10.93, against the old -6.45 to 6.45, -14.51 to 14.08 and -0.06 to 12.05: the old one's top was its handles.
- Triangles after the 2026-11-04 hardware pass: 12,616 / 5,504 / 1,924 (LOD 0-2), previously 10,528 / 5,264 / 1,890.
- One material, one 2048 atlas, about 24 px/in.
- A simple box hull for physics. The old model has an embedded hull, which can't be copied out of its compiled file.

## Pipeline

`run.ps1` runs Blender hidden in the background at idle priority, 2 threads, using `output/cash-bag-detail-20261104/work`. Rerunning the build can change the unwrap, so bake and paint after it: the export
refuses to run otherwise.

| Step | Does |
| --- | --- |
| `read_old.py <root> <out>` | Reads the old mesh from its compiled file for the "before", using the HE grenade's reader |
| `cash_bag.py` (`run.ps1 build,bake`) | Meshes, UVs, LODs; position, normal, finish and AO bakes |
| `paint_cash_bag.py <work> <folder>` | Every map, in numpy; each bundle's notes on its own axes |
| `cash_bag.py` (`run.ps1 export`) | OBJs, vmdl, vmat, hull |
| `cash_bag.py` (`run.ps1 export-meshes`) | Only the three mesh inputs, preserving the installed ModelDoc, material resource and hull |
| `verify_cash_bag.py <root>` | The checks below |
| `render_cash_bag.py`, `make_sheets.py` | Matched comparison renders and the sheet |

## Checked and not checked

Checked from the files by `verify_cash_bag.py`: LOD 0 has 0 pieces inside out; every LOD's normals agree with its faces, its UVs are in the atlas and its
bounds are near the old model's; every file the vmdl and vmat name exists; all four users name it (`verify_cash_bag.py <root> installed`).

Native full model/material compilation and matched isolated-scene engine captures were checked on 2026-11-04. All three engine LODs load with separate
LOD masks and one draw per LOD. The close hardware pass below was viewed under the same light and cameras as the previous installed version.

**Still not checked:** the LOD thresholds in a match, the look in the player's hands and on their back, and how a dropped bag lands on the hull.
The old model's surface type couldn't be read, so the hull uses `default`.

## Approved hardware details (2026-11-04)

- Added individual plated zipper teeth along the open rim, replacing the painted metal stripe on the canvas. Teeth are omitted beyond LOD 0.
- Replaced the bent rubber pull shapes with open, rounded metal pull tabs and connecting hinges.
- Replaced the solid shoulder adjuster block with a rounded two-slot tri-glide and central bar. It follows the actual strap path and normal.
- Rebuilt and baked the meshes and existing 2048 maps. Kept the installed ModelDoc, material resource, hull, prefab offsets and equipment settings.
- Offline checks passed: all LODs have valid UVs and outward normals, 180 solid pieces with none inside out, bounds close to the original bag, references
  present and all four equipped/carried/dropped users still naming the installed model.
- Approved native renders and current build files: `output/cash-bag-detail-20261104/after` and `work`. The obsolete build folder and before/comparison files
  were deleted after approval. The active scene and play state were preserved by the completed capture.
