# Boxyard IBC tote v2

Created 2026-10-30. Replaced Boxyard's two totes on 2026-10-31, at the user's word after comparing both in s&box ("ibc new better"). The Blender sheet is
`output/asset-improvement-20261030/ibc-tote/ibc_tote_before_after.png`.

## Why this one

Boxyard is in the map rotation, and the two totes stand by the north-east stack in the middle of the fight. The old one, `boxyard_map.ibc`, is 382 triangles: a plain box with a tiled plastic texture, inside bare rods on a concrete-textured slab, and a box for a valve.

## What it is

A 1000 l tote as it really is: a blow-moulded tank with rounded edges and rib lines, a screw cap with a vent, a welded galvanised tube cage with every crossing modelled, a pallet on three runners with feet, and a butterfly valve with a red lever and a capped outlet on a tether. The liquid's level shows through the milky wall, with algae low down. Its printing is generic: a litre scale, "T-14", "INDUSTRIAL USE ONLY". No brand.

- Triangles: 10,842 / 3,128 / 1,146 (LOD 0-2), against 382 and no LODs.
- One material and one 2048 atlas, about 11.5 px/in, because the tank is big. It's fine for a map prop, but the print is soft from a foot away.
- Same origin, on the ground under its middle, inside the old footprint: x +-19.7, y -24.2 to 23.6, z 0 to 45.8.
- No physics: Boxyard's own box collider for it stays, so cover and bullets behave as they did.

## In the map

- `Tools/boxyard_map.py`: `ibc()` writes only its old collision box into the merged props and records a placement, and `ibc_object()` puts the model in the scene with no collider, as the drums do. The bins went in the same way, at the same time.
- `install_map.py <root> <scratch inside the project> <backup> [--copy]` runs the map script into the scratch folder and compares every model file, the props model material by material, and the scene object by object. It copies across only if each difference is an expected one. The radar picture isn't copied: it never comes out identical and the collision didn't change.
- The dry run: with the script unchanged, every file came out identical to the live ones. With this change, 0 problems in 76 spots, none cut off, the only scene change is 5 new objects, and the props model lost only the old props' 1,028 triangles and 7 materials those props alone used. Its collision files didn't change.
- Rollback: `output/asset-improvement-20261030/ibc-tote/before-install/` holds the props files and the scene as they were. The old materials stay in Assets.

## Pipeline

`finish.ps1 [-Build]` runs it all in the background at idle priority.

| Step | Does |
| --- | --- |
| `read_old.py <root> <out>` | Writes the old tote with the map's own generator, for the "before" |
| `ibc_tote.py` | Meshes, UVs, LODs; position, normal, finish and AO bakes; OBJs, vmdl and vmat |
| `paint_tote.py <work> <materials>` | Every map, in numpy, with wear worked out in 3D |
| `verify_tote.py <root>` | The checks below |
| `render_tote.py`, `make_sheets.py` | Matched comparison renders and the sheet |

Rerunning the build can change the unwrap, so bake and paint after it: the export refuses to run otherwise.

## Checked and not checked

Checked from the files by `verify_tote.py <root> installed`: LOD 0 has 0 pieces inside out; every LOD's normals agree with its faces, its UVs are in the atlas and it's inside the old footprint; every file named exists; no physics; Boxyard uses it.

Checked in s&box on 2026-10-31, in an isolated editor scene loaded from `boxyard.scene` (`check_config.py`, then `capture_installed.cs.txt` through `sbox-cli --call run_csharp`; shots in `output/asset-improvement-20261030/installed-check/boxyard/`):
- The props model, the scene and the new models compiled with no errors in the log, and no renderer has an error model.
- Two totes and three bins stand where the old ones stood, with no colliders of their own and the old faces gone.
- Rays: every ray with a clear path stopped exactly on the old collision box's face, on surface metal for totes and plastic for bins. Others stopped early on a neighbouring prop or started inside a container, so those faces weren't tested from that side.

**Not checked:** a real match, because the editor is shared and play wasn't to be started. So walking into them, bullets and marks, and how they look under the player camera's look. Frame time. The LOD thresholds (estimates) haven't been watched switching. The tank is opaque, so the liquid is painted on: walking round it, the level won't shift the way a real translucent tank's does.
