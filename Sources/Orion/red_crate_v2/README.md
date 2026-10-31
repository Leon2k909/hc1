# Orion red steel crate v2

Created 2026-10-30. Replaced all 10 of Orion's red crates on 2026-10-31, at the user's word after comparing both in s&box ("crate new better"). The Blender sheet is
`output/asset-improvement-20261030/red-crate/red_crate_before_after.png`.

## Why this one

Orion is live, and `OP.red_crate` stands in 10 places, most of them around the cargo yard at eye level. The old one is 134 triangles: a flat red box with four dark corner bars, three flat strips on each long side and a white X. The map's cargo cases were the other candidate, but `P.case` is already properly modelled.

## What it is

A steel transit crate, which is what the old one's code describes:

- Pressed corrugated walls in a welded charcoal frame, with gussets and a centre post.
- Cast corner fittings that stand proud of the lid to stack on.
- Two fork pockets that run right through.
- A lid hinged on a gasket, two over-centre latches, a padlocked hasp, and a yellow wire seal.
- Fold-down end handles with rubber grips, a card in a holder, and a riveted data plate.

The paint is sun-chalked signal red, chipped through primer, with rust bleeding under the rails. Its lettering is the map's own: ORN, Orion's planet-and-orbit mark, GSE-4417. No real brand. No bullet marks.

- Triangles: 13,228 / 5,348 / 1,160 (LOD 0-2), against 134 and no LODs.
- One material and one 2048 atlas, about 12 px/in.
- Same origin, inside the old 44 x 34 x 40 crate's bounds: x +-17.5, y +-22.2, z -0.2 to 40.2.
- No physics: Orion's own box collider for it stays, so cover and bullets behave as they did.

## In the map

- `Tools/orion_parts.py`'s `red_crate()` writes only its old collision box and records a placement, and `Tools/orion_map.py`'s `red_crate_object()` puts the model in the scene with no collider.
- **One model serves the map's five sizes.** 44 x 34 x 40 is three of the ten placements. The rest are 60 x 40 x 50 (three), 40 x 30 x 46 (two), 40 x 30 x 34 and 36 x 28 x 32. Each object's scale is its box's size over the model's, on each axis, so the model fills its old collider exactly with no new atlas or build. The scale isn't uniform, so fittings and lettering stretch a little: up to about 30% between axes, on the 40 x 30 x 46 crates.
- `install_map.py <root> <scratch> <backup> [--copy]` installs it. Orion's OBJs don't come out identical even with no change to the script: tiny corner triangles on five models' containers (`rw_steel_dark`) differ from the 17 October ones. So it takes each live OBJ and removes only the crates' triangles, rather than copying the script's OBJs. A plain rerun of `orion_map.py` will change those corners, and nobody has looked at which version is right.
- The dry run: 0 problems in 93 spots, none cut off. The only scene change is 10 new objects. Exactly 134 triangles per crate went (1,340), and the three models lost only `oa_red` and `oa_letters_light`, which the crates alone used there. No collision lines changed in their vmdls.
- Rollback: `output/asset-improvement-20261030/red-crate/before-install/` holds the three models' files and the scene as they were. The old materials stay in Assets.

## Pipeline

`finish.ps1 [-Build]` runs it all in the background at idle priority.

| Step | Does |
| --- | --- |
| `read_old.py <root> <out>` | Writes the old crate with the map's own generator, for the "before" |
| `red_crate.py` | Meshes, UVs, LODs; position, normal, finish and AO bakes; OBJs, vmdl and vmat |
| `paint_crate.py <work> <materials>` | Every map, in numpy, with wear worked out in 3D |
| `verify_crate.py <root>` | The checks below |
| `render_crate.py`, `make_sheets.py` | Matched comparison renders and the sheet |

Rerunning the build can change the unwrap, so bake and paint after it: the export refuses to run otherwise.

## Checked and not checked

Checked from the files by `verify_crate.py <root> installed`: LOD 0 has 0 pieces inside out; every LOD's normals agree with its faces, its UVs are in the atlas and it's inside the old crate's bounds; every file named exists; no physics; Orion uses it.

Checked in s&box on 2026-10-31, in an isolated editor scene loaded from `orion.scene` (`Sources/Boxyard/ibc_tote_v2/check_config.py` and `capture_installed.cs.txt`; shots in `output/asset-improvement-20261030/installed-check/orion/`):
- The three models and the scene compiled with no errors in the log, and no renderer has an error model.
- All 10 stand in their places with no colliders of their own and the old faces gone. All five sizes were seen, and the non-uniform scale draws and lights properly.
- Rays: at every size, rays with a clear path stopped exactly on the old collision box's face, on surface metal. Others stopped early on a neighbour or a wall.

**Not checked:** a real match, because the editor is shared and play wasn't to be started. So walking into them, bullets and marks, and how they look under the player camera's look. Frame time: 10 crates are up to 132,280 triangles at LOD 0 against 1,340 before, plus five more 2048 maps. The LOD thresholds (estimates) haven't been watched switching, and with the scale they may switch at slightly different distances. LOD 2 keeps the walls' colour but flattens most of their ribs.
