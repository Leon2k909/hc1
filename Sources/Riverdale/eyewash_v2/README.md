# Riverdale's eye wash v2

Created and installed 2026-10-31. The user sent a screenshot of the old one ("this needs to look better"), then approved the new one after seeing both side by side in s&box ("Yes, replace them"). All 5 of Riverdale's eye washes draw this model: east and west walls at n 560, north wall at e 962, south wall at e +-880. Not committed.

The old one is a pipe, a shallow turned dish with a flat steel disc for a top, two black stubs, and a plain green box for a push plate. This one has a dished bowl, stainless inside and green outside, on a bolted bracket with gussets; a drain strainer; twin spray heads under yellow flip-off dust caps on straps; a brass ball valve with a green push paddle, its "PUSH" and arrow printed on; a green riser with clamps, a coupling and a brass union; and a chrome waste trap into the wall.

- Triangles, LOD 0-2: 5,780 / 3,330 / 900, against about 230 for each old one. One 2048 atlas at about 42 px/in.
- Its width is +X and +Y comes out of the wall. It stands on the wall's epoxy band, 0.25 in out from the wall, or the band swallows the bracket's plate. Its sign stays in the map's model. It has no collision, as the old one had none.
- The surface comes from real scans in `Assets/materials/forestbase/scans/`, at their true scale: `metal_plate_02` for the shapes of the chips, scratches and dull patches, and `container_side` for a faint mottle in the enamel. Procedural work only says where wear goes.
- `eyewash.py` builds, bakes and exports, `paint_eyewash.py` paints. `install_eyewash.py` installed it, and `verify_eyewash.py` checks it. `compare_config.py`, `installed_config.py` and `capture_compare.cs.txt` shoot it in a hidden copy of the hall.

What seeing it in s&box showed that Blender wouldn't have: strong scan mottle read as moss on the pipe, 0.78 metal at more roughness read as grey plastic, and the wall's epoxy band hid the bracket. All three are fixed.

Checked on 2026-10-31:
- `verify_eyewash.py`: 0 of the old faces left at any spot, the signs still there, the scene's five the same as what the hall's code records, renderers only, and each compiled model newer than its OBJ.
- All five looked at in a hidden copy of the hall, with no error models and no old pieces showing. Before installing, nothing else in the hall's models stood in the new one's space at any spot. Shots are in `output/asset-improvement-20261030/eyewash/engine/installed/`.

Not checked: a real match with the player camera's look, or a LOD switch being watched. The LOD distances (30, 80) are estimates.
