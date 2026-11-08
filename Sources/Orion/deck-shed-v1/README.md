# Orion launch-deck control shed v1 (2026-11-06)

The plain steel box on Orion's launch deck (bomb site A), rebuilt as one standalone model: `models/props/orion/deck_shed_v1/shed.vmdl`
(3 LODs, 1 material). **Installed in the live scene as `ORION control shed` under `Orion`. The user approved it on 2026-11-06 ("new is
much better") and asked for the old box to be deleted: its 12 render triangles are gone from `orion_launch_deck.obj` and the old-shed
archive and the install/revert tooling were deleted, so this is no longer revertible. Nothing is committed.** Part of the three-model trial
(`output/model-trial-20261106/BRIEF.md`): this session's first model was Spillway's floodlight masts
(`Sources/Spillway/floodlight-mast-v1/`); the user then asked for another on a different map and Orion was picked.

## The old shed (deleted)

`Tools/orion_map.py` `launch_deck()` drew it as `box( m, -230, -110, 1290, 1380, G, G + 110, { "default": "oa_steel", "+z": "oa_dark" },
METAL )`: 120 x 90 x 110 in (e -230..-110, n 1290..1380, deck G = 240), 6 quads = 12 triangles inside the merged
`orion_launch_deck.obj` (2 roof triangles in `oa_dark`, 10 wall and floor triangles in `oa_steel`), flat near-black steel with no panel
lines, bevels, vents, fittings or roof detail, no LODs. It is the control shed on the launch deck (bomb site A), centred at plan
(-170, 1335). A 40 x 84 in windowed door (`P.door`, material `rv_door`) is set in its south face with the lamp `Deck shed lamp` above it;
both are separate map objects and stay as they are.

## Where it is now

One `ModelRenderer` object, `ORION control shed`, Position `1335,170,240` (world: +x north, +y west, deck floor z 240), no rotation, no
collider, a child of the `Orion` node in `Assets/scenes/maps/Orion/orion.scene`. The model's origin is the middle of the footprint on
the floor; its +X is north, +Y is west. The collision is unchanged: the box `PhysicsShapeBox` in `orion_launch_deck.vmdl` (origin
1335,170,295, 120 x 90 x 110, surface `metal`) was never opened or edited. Ray tests in the open scene hit it where the old box was
(south face x=1290, also through the louvre and corrugation; east face y=110; roof z=350, also above the render-only air conditioner and
antenna; deck z=240).

`Tools/orion_deck_shed.py` is the generator hook (like `orion_generator.py`): `Tools/orion_map.py` now calls `ODS.collision( m, G )` in place
of the render box (same collision box, nothing drawn) and adds `ODS.scene_object()` to the Orion node, so a map rebuild keeps the shed
and does not draw the old box again. It reads `native-instance.json` (the scene object with its ids and the model's resource id). The
rebuild itself was not run.

## BEFORE / AFTER (native editor viewport, matched)

All in `output/model-trial-20261106/orion/`, 1102 x 455 px, FOV 80, same camera for both pictures of a pair (`camera_poses.json`).

| view | BEFORE | AFTER | camera (world position / angles) |
|---|---|---|---|
| close, 182 in from the door | `before.png` | `after.png` | 1115.05,119.83,304 / 3.8,16.00,0 |
| 12 m (470 in) | `before_far.png` | `after_far.png` | 927.97,-65.00,304 / 1.7,30.00,0 |
| roof and front from 170 in up (editor camera, not a player position) | `before_roof.png` | `after_roof.png` | 1165.65,155.18,430 / 25.2,5.00,0 |

How they were taken: the bridge's `screenshot_game` (a PrintWindow of the editor window), cropped to the 3D viewport (x428 y100 w1102
h455), the editor camera placed by `set_editor_camera`. No temporary camera, cloned or isolated scene, `RenderToBitmap`, changed
exposure, lighting or post settings, Blender render or Computer Use. BEFORE was shot with the old box in the map (20:45-20:46), AFTER
with the shed installed (21:32). 10 s settle; the shed's own textures were requested with `MarkUsed( 2048 )` (nothing else).
Mean luma of the pairs 32.6 / 33.0 (close), 53.4 / 53.0 (12 m), 41.3 / 40.9 (roof); the rest of each frame (gizmos, light icons,
spawn mannequins, zone boxes) looks identical. Four AFTER-only views (east wall, back wall, 21 m, 45 m) were looked at as a sanity check
of the sides and LOD1; they have no BEFORE twin and are not kept.

## Numbers (`Tools/model_stats.py`; JSON in `stats_before.json` / `stats_after.json`)

| | BEFORE (old box) | AFTER (new model) |
|---|---|---|
| LOD0 triangles / vertices | 12 / 24 | 9,622 / 5,821 |
| LOD1 / LOD2 triangles (switch thresholds) | none (baked into the deck OBJ) | 4,604 (38) / 948 (105) |
| Materials / unique texture files | 2 (`oa_steel`, `oa_dark`) / 3, all shared map files | 1 (`shed_body`) / 5, all new |
| Largest texture (px) | 1024 x 1024 (shared `oa_steel` atlas) | 2048 x 2048 (colour, normal) |
| Total texture pixels (MP) | 3.15 (shared) | 11.53 (new) |
| Est. GPU texture memory (MB, RGBA8 + mips) | 16.00 (shared) | 58.67 |
| Compiled `vmdl_c` / `vtex_c` total (KB) | n/a: 12 triangles inside `orion_launch_deck.vmdl_c` (now 1,185 KB for the whole deck) / 1,465 (shared) | 308 / 5,337 |
| Object size (in / m) | 120 x 90 x 110 / 3.05 x 2.29 x 2.79 | 133.1 x 108.5 x 172.2 / 3.38 x 2.76 x 4.37 overall (box body still 120 x 90 x 110; the rest is pipe boots, rain hood and the antenna) |
| Instances in the map -> total LOD0 triangles | 1 -> 12 | 1 -> 9,622 (net +9,610) |
| Collision (hulls/boxes) | 1 box 120 x 90 x 110 | the same box, unchanged (ray-tested) |

BEFORE was measured on the old box's 12 triangles (`old_shed.obj`, deleted with the old shed) plus `oa_steel.vmat` and `oa_dark.vmat`; the
result is kept in `stats_before.json`. AFTER, from the project root:

```
python -I Tools/model_stats.py --label AFTER --vmdl models/props/orion/deck_shed_v1/shed.vmdl --json Sources/Orion/deck-shed-v1/stats_after.json
```

Notes on the table:

- BEFORE textures are the Orion steel atlas (`oa_steel_color.jpg`, `oa_steel_normal.jpg`, `oa_steel_rough.png`, 1024 sq); `oa_dark` has
  no texture. The whole map keeps using them, so taking the old box out frees nothing: the new shed's 5 texture files are all added.
- "Est. GPU" is the brief's worst case (RGBA8 with a full mip chain). In the engine the new colour and normal are compressed; the compiled
  `vtex_c` total, 5.3 MB, is the more realistic footprint. `model_stats` shows roughness and metalness as 0 B compiled because s&box packs
  them into the normal map's generated texture; the AO is its own 1024 sq texture.
- The compiled `vmdl_c` sizes are from the engine's own compile: `shed.vmdl_c` 315,021 B, `orion_launch_deck.vmdl_c` 1,213,330 B after
  the cut (the box's share before the cut was not measured; its source is 12 triangles, 2.1 KB of OBJ).
- LOD thresholds 0 / 38 / 105 (the project's 19 in per unit: LOD1 from about 18 m, LOD2 from about 51 m). The 12 m shot shows LOD0.
- The model is 62 in taller than the old box only because of the roof equipment (the antenna is the highest point, 172.2 in); the roof
  sheet is at 110 in as before.

## The model

A prefabricated steel equipment shelter. Built in Blender 5.1 (background, idle priority) by `shed.py`
(inches, engine axes: +X north, +Y west, Z up, origin at the middle of the footprint on the floor) with the capture flag's mesh toolkit
(`Sources/Gameplay/capture-flag-v2/build.py`), the same pipeline as the Spillway mast. 185 parts, 1,510 UV islands in one 2048 sq atlas.

- a welded base channel frame on eight anchor brackets with bolts; four corner posts, hazard-striped on the front pair
- trapezoidal corrugated sheet on all four walls (the east, west and back walls and the front's two bays; real geometry, 1 in deep, so
  the corrugation shows in the silhouette), flat pilaster and closure channels framing the map's door (the door and lamp are not part of
  the model)
- an eave cap (four bars) with a standing-seam roof sheet inside it (10 bays) and four lifting lugs
- front: a louvred vent (frame, 7 blades, drip hood, bolts), a pale powder-coated electrical cabinet (door, hinges, handle, brass lock,
  rain hood with cheeks), a conduit run up to a junction box under the eave, two stencilled plates (`AUTHORISED PERSONNEL / ONLY - A-2
  CONTROL SHELTER`, `DANGER / 415 V`), clamps and bolts
- sides: flanged boots with rubber collars and eight bolts where the deck's radius-7 pipe passes through the east and west walls (the old
  box just had the pipe run into its plain faces), a gland box with three glands, conduit and a junction box, and a data plate (`CONTROL SHELTER / UNIT A-2 /
  2600 KG`)
- roof: a package air conditioner on a curb (fan under a guard of two rings and six spokes, disconnect), a mushroom vent, an access hatch with hinges and
  pull, and an antenna mast with clamps (to 172 in)

No Call of Duty or other real-world names or markings; "A-2" and the plate texts are invented.

LODs: every part carries a level (0 smallest, 3 largest). LOD1 drops the level-0 parts (some bolts, the air conditioner's guard rings and
spokes, the antenna clamps) and decimates the rest to 55 % (UV and seam borders kept); LOD2 keeps only the level-3 parts (sheet, frames,
casings, roof) at 28 %.

## Textures

`shed_body`: colour and normal at 2048 sq, roughness, metalness and AO at 1024 sq (`materials/orion/deck_shed_v1/`). **Procedural, not
built from the scan sets** (nothing was downloaded): `shed.py` bakes position, normal, part id and AO for every texel, and `paint_shed.py`
(numpy) works the wear out in 3D from them, so it runs across UV seams and is the same size in inches on every island: graphite paint over
galvanised sheet, chalked where the surface looks up, chipped along the corrugation ridges and the posts, rust blooming at the foot where
the deck splashes it and streaked below the eave; black primer on the base channel and posts with hazard stripes; pale powder coat on the
cabinet, louvre and air conditioner; zinc spangle on the roof sheet and fittings; brass lock; three stencilled plates; a dirt layer over everything.

Texel density is the weak point: **about 9.3 px/in on the front sheet, cabinet and door framing, 16.7 on the plates, 8.4 on the louvre, 6.1
on the posts, 5.0 on the base channel, 4.2 on the east wall, 3.7 on the roof, 2.3 on the back and west walls, 4.6 on the roof equipment.**
The project's scan-based surfaces use about 40 px/in, which this does not reach: all 185 parts and all four sides share one 2048 sq
atlas. At the 182 in close pose the screen resolves roughly 3-4 px per inch (FOV 80 across 1102 px, an estimate), so the texture is not
the limit in the pictures, but it is softer than the scan work from a hand's reach.

## Reuse search

Looked for something to adapt before building: the `CLAUDE.md` index, `Sources/Orion/`, `Assets/models/props/**` (including `shared/`),
the other maps' model folders and upgrade READMEs. Nothing existing is a 3 x 2.3 x 2.8 m equipment shelter. The closest are cabinets, all
smaller or a different object (width x depth x height in, from `model_stats`): Collider tool cabinet trial 79 x 42 x 50, Collider west
cabinet trial 48 x 61 x 138, Sewage power cabinet v2 84 x 44 x 122, Spillway service cabinet 36 x 26 x 79, shared kiosk cabinet
30 x 60 x 59. The red 20 ft container beside the shed (the Lowtide container module) is a different object and stays. What was reused:
the capture flag mesh toolkit and the Spillway mast's Blender launcher, bake and paint approach; the colours were matched by eye to the
old box's near-black.

## Install, and what was deleted

Two saved files were changed (by `install.py`, now deleted with the rest of the install and revert tooling):

1. `Assets/models/maps/orion/orion_launch_deck.obj`: the 12 face lines of the old box were cut (found by their exact content). The 24
   vertex lines stay, unreferenced. The editor recompiled `orion_launch_deck.vmdl` by itself (never force-compiled). The collision in that
   same vmdl was not edited.
2. `Assets/scenes/maps/Orion/orion.scene`: the `ORION control shed` object (one `Sandbox.ModelRenderer`, new ids) was inserted as the last
   child of `Orion` by text edit, CRLF like the rest of the file, and the result was checked to equal the old scene plus that one node.

On the user's approval (2026-11-06, "yes delete old, new is much better") the old-shed archive (`old_shed.obj`, `old_shed_lines.json`: the old
geometry and the exact bytes of the cut lines) and the tooling (`install.py`, `install_lib.py`, `install_state.json`, `revert.py`,
`test_install_revert.py`, `extract_old.py`) were deleted. Until then `revert.py` restored the old state byte-identical (dry run on the
live files, and `test_install_revert.py` PASS on scratch copies). The deletion touched no live file. Getting the old box back now would
mean putting the `box( ... )` call shown above back into `Tools/orion_map.py` and regenerating the deck model.

## Rebuilding

```
powershell Sources/Orion/deck-shed-v1/blender_idle.ps1 Sources/Orion/deck-shed-v1/shed.py <log> <work dir> <project root> build
... same with bake, then:
python Sources/Orion/deck-shed-v1/paint_shed.py <work dir> Assets/materials/orion/deck_shed_v1
... then blender_idle.ps1 ... export (writes the OBJ LODs, shed.vmdl, shed_body.vmat)
```

The editor compiles the textures through the material (`recompile_asset` on the five PNGs, then the vmat, then the vmdl, in that
order, when it has not done so itself). `preview.py` makes Workbench looks at the built model for checking geometry only (not review
evidence).

## Files

Created: `Assets/models/props/orion/deck_shed_v1/` (shed.vmdl, shed_lod0/1/2.obj, shed.mtl, metas, compiled), `Assets/materials/orion/deck_shed_v1/`
(shed_body.vmat, five PNGs, metas, compiled), this folder, `Tools/orion_deck_shed.py`, `output/model-trial-20261106/orion/`.
Changed: `Assets/models/maps/orion/orion_launch_deck.obj` (12 triangles out), `Assets/scenes/maps/Orion/orion.scene` (one object in),
`Tools/orion_map.py` (the import, the collision hook in place of the render box, the scene object), `CLAUDE.md` (one index line).
Deleted on approval: `old_shed.obj`, `old_shed_lines.json`, `install.py`, `install_lib.py`, `install_state.json`, `revert.py`,
`test_install_revert.py`, `extract_old.py` (all in this folder).

## Not verified

- Not seen in a running match: only the editor viewport, with the editor not playing. Shadows from the new model, bots' behaviour around it
  and the navmesh were not checked (the collision is the same box, so the navmesh should not change; it was not rebaked).
- The roof equipment (air conditioner, vent, hatch, antenna) is render only, as the collision must stay the box. A player who gets onto the
  roof (the red container beside the shed is 102 in tall, 8 in lower) walks through it. Not tested whether that route is reachable.
- The map generator hook was syntax-checked and the hook module imported, but `Tools/orion_map.py` was not run.
- No scan-based textures and density far below 40 px/in (see Textures); the back and west walls are the softest and are rarely seen (the
  west wall is a 10 in gap from the container).
- LOD1 was looked at in stills at 21 m and 45 m in the editor (both inside LOD1's range by the 19 in per unit rule); LOD2 (from about
  51 m) and the switches in motion were not looked at.
- The collision was ray-tested on the south (also through the louvre), east and roof faces and the deck beside it; the north face test
  started inside the deck's north player-clip and the west face was not tested (the box is unchanged).

## Verdict

Clearly better than the old box in all three pictures: a flat dark block became a shelter with readable construction (corrugated
cladding, louvre, cabinet with plates and a hazard post, eave cap, base channel; and from above a standing-seam roof with air
conditioner, vent, hatch and antenna) and it keeps the old one's near-black colour and wear contrast. Weaker: it is a heavy asset for one
shed (9,622 triangles and 58.7 MB estimated texture memory against 12 triangles and shared textures), the textures are procedural and soft
compared with the project's scan work, and the roof gear is render only (walk-through if the roof can be reached). The user kept it
("new is much better") and had the old box deleted.
