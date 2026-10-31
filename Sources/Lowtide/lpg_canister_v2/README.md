# LPG cylinder v2

Created 2026-10-30. The user compared it with the old models and told me to replace them, so the Lowtide scene,
`LpgCanister.Visuals.cs` and `Tools/lowtide_canisters.py` now use it and the old models are gone from Assets (rollback:
`output/asset-improvement-20261030/lpg-canister/retired-lpg_canister/`, and git history). The `lt_fl_*` materials stay: the
forklifts use them. The comparison sheets are in `output/asset-improvement-20261030/lpg-canister/`.

## Why this one

Four sit on Lowtide's forklifts and players are meant to shoot them, so they get looked at. The old family is procedural
lathes on tiled "imagegen" metal with no LODs. The burst model has striped insides and strap rings floating in the air.

## What it is

A forklift fuel cylinder as one really is: three-piece welded shell with a foot ring, a valve guard on four welded legs,
a brass service valve with a red handwheel, a relief valve under a rain cap, a bleed screw and a contents gauge, a hose
with a crimped ferrule, and two saddles with rubber-lined straps closed by T-bolts. Pale grey enamel with a red shoulder
band. Lettering is generic and invented: LPG, a flammable-gas placard, a stamped data plate. No brand, real or game.

- **Burst:** a fish-mouth split along the rear with its flaps peeled back and their length kept, the foot end sheared off,
  soot and scale inside, a dip tube you can see through the hole, and the paint scorched back from the tear in 3D.
- **End cap:** the foot-end head with its foot ring and a torn rim.
- The intact bottle carries no impact damage, because the game shows shots with its own leak and fire.

| Model | LOD 0 / 1 / 2 triangles | Old | Atlas |
| --- | --- | --- | --- |
| `lpg_canister` | 19,896 / 8,772 / 2,686 | 4,292, no LODs | 2048, about 22 px/in |
| `lpg_canister_ruptured` | 28,828 / 11,196 / 3,250 | 4,772, no LODs | 2048, about 21 px/in |
| `lpg_canister_cap` | 3,344 / 1,070 | 256, no LODs | 1024, about 32 px/in |

## What the game relies on, kept

- The same three names, with origins at the bottle's centre and the cap's centre. Intact bounds are within 0.15 of the old.
  The burst model differs on purpose: its foot end is gone (y from -13.4, not -17), the flaps reach z 8.88 (old 8.18) and
  x -6.74 (old -6.5). It has no collider, so that only affects culling. The cap sits inside the old cap's bounds.
- The shell profile `LpgCanister.PunctureAt` hard-codes: r 6.3 to |y| 13.5, 5.9 at 15.2, 4.7 at 16.4, 2.3 at 17.
- The valve inside the scene's 1.5-radius sphere collider at y = 17.8, and the hose's end where it meets the truck.
- Physics copied word for word: the intact model's hull file, and none on the burst model or cap, as before.

## Pipeline

`run.ps1` runs Blender in the background at idle priority, 4 threads. Rerunning the build can change the unwrap, so bake and
paint after it: the export refuses to run otherwise.

| Step | Does |
| --- | --- |
| `lpg.py` (`run.ps1 build,bake`) | Meshes, UVs, LODs; position, normal, finish and AO bakes |
| `paint_lpg.py <work> <materials> <variant>` | Every map, in numpy, with wear worked out in 3D |
| `lpg.py` (`run.ps1 export`) | OBJs, vmdls, vmats, the hull copy |
| `verify_lpg.py <root>` | The checks below |
| `render_lpg.py`, `make_sheets.py` | Matched comparison renders and sheets |

Uses `Sources/Gameplay/capture-flag-v2/build.py` and `paint.py` as an imported toolkit, unedited.

## Checked and not checked

Checked from the files by `verify_lpg.py`: LOD 0 of all three has 0 pieces inside out; bounds against the old models; shell
stations; hose end; physics and hulls identical to the old; every texture a vmat names exists; every file a vmdl names
exists; all four bottles in the scene name v2 for their renderer, collider, intact and burst models; the code loads v2's
cap; the old models are gone from Assets and the generator can't write them back.

An editor was open during the install, though the brief assumed it wasn't. It compiled the intact and burst models, their
materials and the scene by itself within a minute, with no errors in the log. The cap only compiles when first loaded.

**Not checked: no one has seen it in s&box.** The images are Blender Cycles renders with ray-traced light, which flatter any
asset. Still unknown in the engine: the materials, the LOD thresholds (estimates), how the burst model's flaps sit against
the forklift's own geometry, and a real rupture in a match.

## Known oddities

- `PlayRupture` launches two caps, one from each end, but only the foot end is really gone on the burst model: the valve end
  stays, because the valve, guard and hose are rooted there. The old burst model kept both ends and still threw two caps.
  In a fireball, at that speed, it shouldn't show. Changing it would need a code change, which this trial doesn't make.
- The burst model's torn shell is dense (about 14,000 triangles of its LOD 0), which is why it costs more than the intact one.
- The hoop-to-leg welds and small bolts drop out at LOD 1 and 2 by design.
- Faint short straight marks show on the valve-end head in close-up. They read as scratches and may be UV island borders; the
  cause wasn't chased. Only about a third of each atlas is filled, because the small parts make about 2,000 UV islands, so a
  tighter packer would raise the texture detail with no new art.
