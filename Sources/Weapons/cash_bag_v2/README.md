# Cash Grab bag v2

Created 2026-10-30. The user compared it with the old bag and told me to install it, so `cash_bag.equip` and the mount, first-person and world prefabs
now use it. The comparison is `output/asset-improvement-20261030/cash-bag/cash_bag_before_after.png`. The old model is a cloud package, so there's no file to
retire. The prefabs keep its package reference, because `ZombiesPowerUp`'s Point Boost still loads it by name.

## Why this one

It's the objective of Cash Grab, which `GameMode.Info.cs` offers on every main-menu map: held in first person, carried on the back and lying
where it's dropped, with a marker on it. The old model is `models/dev/duffelbag/dufflebag_money`, a cloud dev model of 1,464 triangles on
`materials/dev/white_flat`, so in the game it's a plain white shape.

## What it is

A faded olive canvas duffel: piped end panels, a scuffed base panel, stitched seams, a zip standing open along the top on bundles of banknotes
in paper bands, two web handles lying either side of the opening with rubber wraps, and a slack shoulder strap on two D-rings.

- The banknotes are invented: a green "100" with a rosette, no portrait, country or issuer. They copy no real currency.
- Same origin, on the ground under the bag's middle, so the first-person, carried and dropped prefabs hold it the same way. Bounds are x -6.47 to 6.59,
  y -14.52 to 14.12, z 0 to 10.93, against the old -6.45 to 6.45, -14.51 to 14.08 and -0.06 to 12.05: the old one's top was its handles.
- Triangles: 10,528 / 5,264 / 1,890 (LOD 0-2), against 1,464 and no LODs.
- One material, one 2048 atlas, about 24 px/in.
- A simple box hull for physics. The old model has an embedded hull, which can't be copied out of its compiled file.

## Pipeline

`run.ps1` runs Blender in the background at idle priority, 4 threads. Rerunning the build can change the unwrap, so bake and paint after it: the export
refuses to run otherwise.

| Step | Does |
| --- | --- |
| `read_old.py <root> <out>` | Reads the old mesh from its compiled file for the "before", using the HE grenade's reader |
| `cash_bag.py` (`run.ps1 build,bake`) | Meshes, UVs, LODs; position, normal, finish and AO bakes |
| `paint_cash_bag.py <work> <folder>` | Every map, in numpy; each bundle's notes on its own axes |
| `cash_bag.py` (`run.ps1 export`) | OBJs, vmdl, vmat, hull |
| `verify_cash_bag.py <root>` | The checks below |
| `render_cash_bag.py`, `make_sheets.py` | Matched comparison renders and the sheet |

## Checked and not checked

Checked from the files by `verify_cash_bag.py`: LOD 0 has 0 pieces inside out; every LOD's normals agree with its faces, its UVs are in the atlas and its
bounds are near the old model's; every file the vmdl and vmat name exists; all four users name it (`verify_cash_bag.py <root> installed`).

**Not checked: it has not been seen in s&box.** The images are Blender Cycles renders with ray-traced light, which flatter any asset. Not known in the
engine: the materials, the LOD thresholds (estimates), the look in the player's hands and on their back, and how a dropped bag lands on the new hull.
The old model's surface type couldn't be read, so the hull uses `default`.
