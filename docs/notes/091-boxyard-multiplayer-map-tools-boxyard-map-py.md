## Boxyard (multiplayer map, `Tools/boxyard_map.py`)
- The user asked for the car to come out of Shipment and for real textures: "the whole map is basically solid colours"
  (2026-10-08). Shipment is Facepunch's map, made in Hammer, so it can't be edited here, and the user said to remake it.
  Boxyard is our own, on Shipment's layout. It's named Boxyard because "Shipment" is a Call of Duty map's name.
  `Assets/scenes/maps/Shipment/Shipment.scene` is untouched.
- Built by script like Belltower, Railhead and Lowtide (`map_kit`, with `railhead_props`' pallets and crates).
  The script's docstring has the layout. It writes:
  - the models, to `Assets/models/maps/boxyard/`: the yard (the floor, its markings and the perimeter wall), the
    containers, the props, and the backdrop, which is drawn only;
  - the scene, `Assets/scenes/maps/Boxyard/boxyard.scene`, rewritten whole on every run (change the layout in the
    script, not in the editor);
  - the radar picture, `ui/minimaps/minimap_boxyard.png`, and with `--art` a stand-in menu picture, `ui/maps/boxyard.png`
    (a flat-coloured preview: replace it with an in-engine capture).
- The materials are `Tools/boxyard_materials.py`'s, drawn with numpy into `Assets/materials/boxyard/` (its docstring has
  each atlas's layout). Run it before the map script.
  - Each container livery (red, blue and green in two variants, orange, grey) is a 4096 x 2048 atlas of the box's sides,
    doors, front and roof at their real size: marine paint chalked by the sun, rust at the rails, castings and knocks, and
    streaks below. The markings follow ISO 6346 (a made-up owner code ending in U, a serial with its real check digit,
    22G1), with no real owner, lessor or logo.
  - The open containers share one inside atlas: grey corrugated walls, a plywood floor.
  - The rest: the yard's concrete slabs (16 ft, sawn joints, cracks, oil, rust and tyre marks), the wall's precast
    panels, worn floor lines, galvanised and rusty steel, drums, a skip, an IBC's tank, and flat paints for the cones,
    bins and rubber.
- The yard is e -800..800, n -832..832 inside a 128-high wall of precast panels between steel H-posts, with two strands
  of wire on top. Red Team spawns at the west end and Blue Team at the east. Three lanes:
  - North, between the north row (two containers along the north wall, one open) and the north block. Bomb site A is
    its east end, by the angled orange container.
  - Middle, between the north and south blocks (two pairs of containers each, n ±288), with two containers at each
    end by the spawns, one of them angled.
  - South, between the south block and the south row. Bomb site B is its east end, among drums and pipes.
- The containers are ISO 1CC 20 ft boxes at their real size (238.6 x 96 x 102). Their side walls' trapezoidal
  corrugation is geometry, bend by bend, and the paint was drawn to match it. There are 18, and three of them have
  another on top.
  - Six are open, their doors swung back (115 degrees, one leaf of the south row's at 90), with their insides drawn and
    walkable. Each has a dim fill light and its own reflection probe.
  - Shipment's SWAT van is a closed grey container on B (508, -630): a van would have been the car again.
  - Every container's top and the wall's top are player-clipped up to z 1000.
- Props: a crate on a grounded pallet, a skip, crates, cones (one knocked over), two IBC totes,
  205 l drums, wheelie bins, two stacks of rusty pipe, and a stack of pallets. The cones and drums are models placed by the
  scene, with only their collision in the props model (`docs/notes/165`, `docs/notes/162`).
- Forklifts (2026-10-14): the user retired the old Boxyard model from every map. Its geometry and collision were
  removed from Boxyard and both Railhead yards, and its shared `railhead_props` generator and Stillhouse preview
  reference were deleted. Use `Tools/lowtide_forklift.py` for future forklifts; preserve Lowtide's detailed model.
- The backdrop (no collision) is the terminal round the yard: about 2,400 containers in stacks of up to five, with
  roads between blocks, three gantry cranes and four light masts, all on concrete out to 6000.
- Modes: the scene lists TDM and Defuse. It has deathmatch spawns (16), Retakes spawns for each site, Domination flags
  (A west, B middle, C east), five Hot Zones and three Cash Grab points (`ObjectiveSpot`s). It's in `GameUtils`' three
  map lists.
- Every run checks all 76 spots with railhead_map's `check_spots`, `check_reach` and `check_retakes_sight`. On
  2026-10-08 all three passed.
- The navmesh's bounds stop at `NAV_TOP` (98), under the containers' roofs.
- Made offline on 2026-10-08, without the editor, and checked in Cycles renders of the scene with its textures
  (`railhead_render.py` with Boxyard's scene). Nothing has compiled, and the lighting, the navmesh, bots and the modes'
  objects are all unchecked.
- To play it: `dev_mode team_deathmatch boxyard`.

