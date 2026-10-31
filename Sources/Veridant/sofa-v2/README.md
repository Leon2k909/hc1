# Veridant lounge sofa v2

Installed 2026-10-31 at the user's word after comparing both in s&box ("sofa new better"). Nothing is committed. The old sofas' faces are cut from `lounger-v2/veridant_buildings-base.obj`, which `veridant_buildings.vmdl` builds from, and the scene's "Sofas" group places 9 models with renderers only. The old boxes stay in the merged model as their collision. `docs/notes/167-*` has how.

Why this one: the old sofa is eight plain boxes in two flat colours, repeated nine times across the lounge, the gallery, the ops lobby and reception, with
no rebuild of its own, though the chairs, tables, benches and loungers around it have had one.

The new one keeps the old ivory and tan: a soft frame with rounded arms and back, loose seat and back cushions with crowned tops and piped seams, a teal and an
ochre scatter pillow, on a recessed dark plinth with a brass trim.

- Three models, one per length the map uses: `sofa_84` (6 placed), `sofa_96` (2 placed), `sofa_120` (1 placed).
- Triangles, LOD 0-3: 84 in 10,502 / 3,610 / 1,864 / 776; 96 in 10,682 / 3,610 / 1,864 / 776; 120 in 12,782 / 4,190 / 2,190 / 938. Each old sofa is 96 triangles.
- Same footprint: within 0.6 in of the old x +-18 and y +-length / 2. The scatter pillows stand 0.9 in above the old top of 33 in, which nothing depends on.
- Collision is the old box: 36 x length x 30 centred 15 in up, surface `fabric`.
- One material per length, with colour, normal and roughness at 2048 and metalness and AO at 1024. About 9-10.5 px/in, so the weave is soft from a foot away.
  Three 2048 sets is a real memory cost, not measured in the engine.

## Files

- `sofa.py` builds, bakes and exports one length. `paint_sofa.py` paints. `render_sofa.py` and `make_sheets.py` make the sheets. `verify_sofa.py` checks the files.
  `finish.ps1 [-Build]` runs them in order at idle priority.
- Toolkit: `Sources/Gameplay/capture-flag-v2/`'s `build.py` and `paint.py`, imported, not edited.
- Work files, renders, sheets and the export are in `output/asset-improvement-20261030/sofa/`. `sofa_v2/` there is laid out like Assets.
- Rerunning the build can change the unwrap, so bake and paint after it. The export refuses to run otherwise.

## Checked

Seen in s&box in an isolated editor scene (`output/asset-improvement-20261030/pew-sofa-shutter-check/`): 6, 2 and 1 of the three lengths, none failing to load, each of the nine looked at. Rays in that scene stop on the old faces with surface fabric, and one above the old 30 in box passes.

From the files, before installing: `verify_sofa.py` passes for all three lengths: `check_outward.py` reports 0 inside out on LOD 0, bounds fit, the collision box is the old one, every texture and file
the vmat and vmdl name exists, and the old reception sofa's 96 faces are as committed. The 84 and 120 were rendered against the old ones; the 96 wasn't rendered.

## Not checked

- Not seen or walked into in a real match. Rays are the only collision test.
- The LOD switches (30, 80, 180, about 14, 39 and 87 m) were set from the note on props at distance, and no switch has been watched.

## To undo it

Git for `Tools/`, the OBJ and the scene, or the originals in `output/asset-improvement-20261030/sofa/before-install/`. `install_sofas.py <root>` reports without writing, and refuses if any corner or count doesn't match.
