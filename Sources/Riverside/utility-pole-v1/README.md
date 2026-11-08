# Riverside utility poles v1 — real timber poles (installed for review, 2026-11-06)

**Status: approved by the user on 2026-11-06 ("keep the new poles in the map but also keep the old asset"). New poles installed, old poles kept as utility_pole_original. Not committed.**
- New: `models/props/riverside/utility_pole_v1/pole_2arm.vmdl` (the six west-side poles) and `pole_1arm.vmdl` (the three
  east-side poles), placed by the scene's **Utility Poles** group (nine objects "Utility Pole 1-9", one `ModelRenderer` each).
- Old, kept unused: `models/props/riverside/utility_pole_original/pole_2arm_original.vmdl` (136 triangles) and
  `pole_1arm_original.vmdl` (100 triangles), the old poles as the dressing mesh drew them, same origin and facing as the new
  models. Both load with no errors. The dressing mesh and scene exactly as they were before the install are in
  `output/riverside/utility-pole-v1/install-before/`, and `revert.py` (tested for real, see below) puts the old poles back.
- `Tools/riverside_parts.py` and `Tools/riverside_map.py` now match what is installed: `pole()` registers the pole in
  `UTILITY_POLES` and draws no shaft, crossarm or brace (its collision hull, insulator taps, transformer cans and lamp arms are
  unchanged), the scene writer adds the **Utility Poles** group, and `OLD_POLES_IN_DRESSING = True` brings the old poles
  back into the dressing. Checked offline (`gen_check.py`): nine poles registered; with the flag on the polygon counts equal
  the old ones. **The generator was not run** (it rewrites the whole map); the dressing OBJ and scene were edited in place as
  described below, which is what the generator now produces for them.

## Why this prop

Nine poles line the lane the players run along from the spawn pad (the first two stand at pad height): eye level, main
route, passed every life.
The old pole (`riverside_parts.pole`, 136 / 100 triangles baked into `riverside_dressing.obj`) was four 8-sided tapering
shaft segments, two plain box crossarms and four 1.4 in square braces, all in a flat 512 px paint at 8 px per inch.

## What changed

| | before | after |
|---|---|---|
| geometry | 1,116 triangles inside `riverside_dressing.obj` (756 `rs_pole`, 360 `rs_steel`): 136 per 2-arm pole, 100 per 1-arm pole, one LOD | `utility_pole_v1/pole_2arm.vmdl` LOD0 1,951 / LOD1 327 / LOD2 128 triangles; `pole_1arm.vmdl` 1,567 / 291 / 92 (switch 0 / 35 / 90) |
| trunk | four 8-sided tapering boxes | 24-sided trunk with a butt flare, a faint sweep, out-of-round growth and a pitched top, smooth-shaded, grain turning a fifth of a turn up the pole |
| crossarms | plain boxes | chamfered 4 x 5 arms with a carriage bolt through each (domed head, square washer, nut and bolt end behind) |
| braces | 1.4 in square rods | flat steel angle braces with bolts |
| hardware | none | ground wire stapled down the trunk into a half-round guard to 8 ft, climbing steps (bolts) up one side, an aluminium tag, an earth mound at the foot in Riverside's mud paint (small hardware on LOD0 only) |
| texture | `rs_pole`, 512 x 512, 8 px/in | new `pole_wood`: real brown_planks_03 scan crops tone-matched to creosote, 1024 x 2048, 27-37 px/in (`make_textures.py`) |

Unchanged: every pole's position, height (430 in west, 400 in east), taper, crossarm heights, the crossarm tops the pin
insulators sit on, the insulators, wires, transformers, lamp arms, and **all collision** (the dressing's hull files were not
touched). Materials reused: `materials/lowtide/lt_steel.vmat` (steel), `materials/riverside/rs_alu.vmat` (tag),
`materials/riverside/rs_mud.vmat` (mound).

Installed as scene root **Utility Poles** > nine **Utility Pole N** objects at the old poles' bases, yaw from
`map_kit.plan_yaw(facing)`. The old poles' 1,116 triangles were cut out of the dressing OBJ face line by face line (vertices
stay, CRLF kept) by exact vertex fingerprint and by region: the dressing goes from 108,552 to 107,436 triangles.

## Before / after

Real editor viewport captures (`bridge_call screenshot_game`, cropped to the viewport pane: x 428, y 100, 1102 x 456), same
camera pose and same scene for each pair, nothing retouched; the editor's light gizmos show in both. World poses (engine
x, y, z, pitch, yaw; z is the camera height above the ground, 64 in is standing eye height):

| pair | pose | what it shows |
|---|---|---|
| trunk | 1015.5, 204.3, 64, -18, 75.7 | 3.6 m from a lane pole, looking up the trunk |
| foot | 1017.9, 214.1, 64, 2, 75.7 | 3.3 m from the same pole, level, the foot and the steps |
| arms | 890, 130, 64, -53.4, 52.7 | 6.7 m, looking up at the crossarms and the lamp |
| mid | 550, -60, 64, -13.3, 38.7 | 16 m from the same pole, standing |
| far | 500, 40, 64, -8, 0 | down the lane at the row of poles |
| padmid | -430, -315, 160, -14.1, 45.0 | from the spawn pad deck (z 160 = deck 96 + 64) at the first pole, 15 m |
| east | 850, 250, 64, -14.4, -31.9 | 13.5 m from an east-side pole |

`captures/before-*.png` and `captures/after-*.png` are the raw captures; `comparison-*.png` put each pair side by side
(`compose.py`); `comparison-arms-zoom.png` is a 4x enlargement of one region of the arms pair (labelled as such, not a new
shot). All in `output/riverside/utility-pole-v1/` (`captures/superseded/` holds an earlier, partly wrong-scene take, kept
only because nothing was deleted). The captures come from two installs of the same model: BEFORE mid, arms, far, padmid and
east were taken with the old poles, AFTER mid, arms, trunk, far, padmid and east right after the first install; then
`revert.py` and `install.py` were run for real, and BEFORE foot and trunk (old poles, after the revert) and AFTER foot and
trunk (re-install, `after-trunk-recheck-after-reinstall.png`) were taken at the same poses. The poles look the same across the
round trip: in the 65 pixel columns round the trunk, 506 of 29,640 pixels differ by more than 24 levels between the two old-pole
trunk takes (sky and star noise), 123 between the two new-pole takes, 7,595 between old and new.
The editor's fires and smoke animate, so they differ between the two halves of the east pair.

## Files

- `make_textures.py` writes `Assets/materials/riverside/utility_pole_v1/` (colour, normal, roughness PNGs and the vmat).
- `build.py` writes `Assets/models/props/riverside/utility_pole_v1/` (three LOD OBJs per variant, two vmdl) and
  `output/riverside/utility-pole-v1/manifest.json` (counts, 0 inward faces and 0 wound or flat faces on every LOD, sha256).
- `legacy_poles.py` redraws the old poles exactly as `riverside_parts.pole` drew them (1,116 triangles) to find them in the
  dressing mesh, and writes the kept `utility_pole_original/` models.
- `prepare_install.py` stages the cut dressing OBJ and keeps `install-before/`; `install.py` / `revert.py` / `editor.py` do the
  editor work through `sbox-cli --call` (Riverside is brought to the front only for the few seconds each takes, under the
  shared lock `output/editor-lock`, then the scene that was in front goes back).
- `compose.py` makes the comparison sheets.

Shared tracked files this change touches (compare against `install-before/`, not `git diff`: both were already modified by
other sessions):

| file | sha256 before | sha256 now |
|---|---|---|
| `Assets/models/maps/riverside/riverside_dressing.obj` | `16570b1f…92ac7e38` | `8e3a2c5c…ad8d4c0b` |
| `Assets/scenes/maps/Riverside/riverside.scene` | `2616f03e…c6ab3d1f` | `a1df5e1d…1f59f4bd` |
| `Tools/riverside_parts.py`, `Tools/riverside_map.py` | generator edits described above | |

(Full hashes: `install-plan.json`.) The scene differs from the saved original by the Utility Poles block and one
prefab-instance GUID pair the editor rewrites whenever it saves (around line 14844).

## Revert

```
python Sources/Riverside/utility-pole-v1/revert.py --check          # looks, changes nothing
python Sources/Riverside/utility-pole-v1/revert.py                  # deletes the nine objects, restores the dressing OBJ
python Sources/Riverside/utility-pole-v1/revert.py --delete-assets  # ...and deletes utility_pole_v1/ models and material
python Sources/Riverside/utility-pole-v1/install.py                 # puts the new poles back after a revert
```

`revert.py` only swaps a file back while it is still exactly what `install.py` wrote (sha256), compares the editor's copy
of the scene with `riverside.scene` object by object before saving, and never deletes `utility_pole_original/`. **It was
run for real on 2026-11-06** against the live editor (objects gone, dressing back to 108,552 triangles, byte for byte
the original OBJ), then `install.py` again (107,436 triangles; `revert.py --check` afterwards: objects installed, mesh
installed, editor copy equals `riverside.scene`, 451 objects, 0 differences). The group's GUID changed with the second install
(`native-objects.json` holds the current ids). By hand: delete the "Utility Poles" object in Riverside and save, copy
`install-before/riverside_dressing.obj` over the dressing OBJ.

## Cost, new vs old (measured 2026-11-06 with `Tools/model_stats.py`; `stats_before.json`, `stats_after.json`)

| | old | new |
|---|---|---|
| triangles per pole (2-arm / 1-arm) | 136 / 100 | LOD0 1,951 / 1,567, LOD1 327 / 291, LOD2 128 / 92 |
| nine poles | 1,116 (always) | 16,407 within about 17 m, 2,835 to about 43 m, 1,044 beyond |
| pole textures | `rs_pole` 3 x 512 x 512 (0.79 MP, 4 MB uncompressed estimate, 0.37 MB compiled) | `pole_wood` 3 x 1024 x 2048 (6.3 MP, 32 MB uncompressed estimate, 3.45 MB compiled colour + normal; roughness is packed) |
| draws | part of the merged dressing mesh | 9 model objects, up to 4 materials each (3 on LOD1, 2 on LOD2) |

LOD distances use the project's measure (about 19 in per threshold unit at 1080p / 90 degree FOV). `rs_pole` is still
used by other Riverside geometry (64 faces left in the dressing, 8 ModelDocs), so the new texture set adds to the old one
rather than replacing it; steel, tag and mound textures are shared with models that are already loaded. **The new poles
are the heavier option on all three counts**; they buy detail within a few metres, and from about 43 m the cost is about
the old one's.

## Verdict (honest)

The old poles were not crude, and this is a subtle upgrade. Within about 7 m the new poles are clearly better: a round
trunk with real grain, silvering and dark creosote bands instead of faceted stripes of one repeated blotch pattern, step
bolts, bolt heads on bevelled arms, silver V-braces in place of thin dark rods (3.3 m, 3.6 m and the 4x crop of the 6.7 m
pair). At 13 m and beyond (mid, far, padmid, east) at night the pairs are close to indistinguishable. If that is too small a
gain for the extra cost, reject it with `revert.py`; a cruder prop (guard-tower frame about 316 triangles, water-tower
legs, the plank fence run, the neon sign pole) would show more.

## Still to do

If approved, commit together: `Assets/models/props/riverside/utility_pole_v1/`, `.../utility_pole_original/`,
`Assets/materials/riverside/utility_pole_v1/`, `Tools/riverside_parts.py`, `Tools/riverside_map.py`, this folder and the
CLAUDE.md line. The dressing OBJ and `riverside.scene` also hold other sessions' uncommitted Riverside work, so committing
them takes that along.
