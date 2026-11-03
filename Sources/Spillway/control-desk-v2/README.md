# Spillway control desk v2

Created 2026-10-31. **Installed the same day** at the user's word, after an in-engine before and after: see `docs/notes/178`.

The old desks are the four `rv_desk` boxes and floating `schematic` screens in `spillway_map.control_house`, in the upper control room of A1:
a 120 x 70 x 34 box with a flat blue screen hanging in the air in front of it. They sit in `spillway_control.obj`, and that scene's vmdl does build from that OBJ.

This is a hydro plant's operator desk, as it would have grown over the years:

- Steel pedestals with a kneehole, foot rail, vented door, two drawers and a laminate top with a rubber edge.
- A sloped hardwired mimic board in five bays (three units, station control, spill gates): pistol-grip switches, lamps, push buttons, an emergency stop in its guard, and a small touch panel set in later.
- Ten round meters and a chart recorder on the upright panel.
- Three screens on a beam: the turbine from above (which keeps the old screen's ring and blocks of colour), trends and alarms.
- A red direct-line phone, keyboard and mouse, clipboard and an enamel mug.

Same 120 x 70 footprint and origin at floor centre, operator's side +X. Worktop at 31.5 where the old box's top is 34. It stands 85.6 tall, where the old screen's top is 87.5.

- Triangles: about 33,000 / 19,000 / 1,100 (LOD 0-2), thresholds 30 and 80. The old desk and screen are 12 + 2 triangles.
- Three materials: `cd_body` (4096 atlas, 13 px/in), `cd_panel` (4096 x 2048, printed board, 37 px/in across), `cd_glow` (2048 x 1280, screens and lamps, self-lit at 3.0 as the map's own screens are).
- No third-party meshes or textures. Lettering is drawn with Windows' Bahnschrift. No game or brand markings.
- Physics in the vmdl: the old box's footprint up to the worktop, the slope and the screens. It replaced the old 34-tall boxes in the map. The new upper part blocks players and shots, where the old floating screen didn't. The user wasn't asked about this: without it, shots would pass through the screens and board.

## Pipeline

`finish.ps1 -Build` runs all of this at idle priority: `desk.py` (build, bake, export, using the capture flag's mesh toolkit), `paint_desk.py` (every map) and `check_outward.py`.
`capture.py compile` compiles it and checks the installed desks in an isolated scene through `capture_engine.cs.txt`: shots, and rays at one desk's collision. Layout of both panels is in `layout.py`, shared by the build and the paint.

`check_outward.py` reports about ten pieces "inside out" on the final mesh. Those are false: `drop_hidden` removes faces no ray can reach, which leaves open shells whose signed volume means nothing. Before that step the same geometry read 0 inside out. Comment out `drop_hidden` to re-check after changing the geometry. `verify_desk.py` fires rays at the desk from the room instead, and fails if one goes through its shell.

## What the engine showed

- A normal map must be a power of two: `GenerateMips( "HemiOctIsoRoughness_RG_B" )` fails on 4096 x 1280 and the whole model draws the red error checker. The panel is painted at 1280 rows and stretched to 2048, as its UVs are fractions.
- Dark navy read almost black in this dim blue room and needed about twice the paint. The grey old desk reads navy here only because of the room's light.
- The toolkit's packer loses a lot to the long L-shaped strips of big parts' chamfers and to faces shut inside the desk. `drop_hidden` and `split_thin_islands` took the atlas from 9.5 to 13 px/in. Don't split small parts' chamfers: their slivers get no texel of their own and took a neighbour island's colour.
- Lit lamps burned white until their colours came down, as the self-illum factor is 3.
- `drop_hidden` first counted anything reaching the floor as blocked, so it removed every underside: the worktop could be seen through from low in the kneehole. A ray that lands outside the footprint now counts as seen, and big faces are sampled on a grid.

## Not done or not known

- Compiled and checked in place on 2026-10-31 with `capture.py compile`, in a hidden copy of the map with its own light: all four desks draw, the kneehole is closed, and rays hit the model's collision where expected. **Not yet seen in a live match** with the HUD and gun, and players haven't walked into it.
- The fronts sit in the worktop's shadow in this dim room, so their chips and scrapes hardly show. Only the top surfaces show the wear.
- The screens don't change or animate.

## How it was installed

`install_map.py` cut the `rv_desk` and `rv_screens` faces from the live `spillway_control.obj` (the same paint is on the pallet in `spillway_cargo.obj`, left alone) and the four collision boxes from its vmdl. It added the model to the scene at plan (e, 1275, 236) for e in -190, 60, 310 and 500, which is engine (1275, -e, 236), yaw 180. `Tools/spillway_map.py` does the same if rerun. Rollback copies: `output/asset-improvement-20261030/spillway-desk/retired/`.
