## Railhead (multiplayer map, `Tools/railhead_map.py`)
- Reference-led fire extinguishers (2026-10-25): `Tools/realistic_extinguisher.py`, delegated by
  `railhead_dress_detail.extinguisher`, supplies the smooth tank, rolled base seam, curved printed label, two levers,
  valve/gauge, safety pin/seal, rubber hose/nozzle, mounting bracket and pictogram sign. The approved image and
  image-generated UV atlas are recorded in `Sources/Railhead/props/extinguisher-v2/`. Six complete legacy assemblies
  were replaced in the published east/west dressing meshes; the generator also upgrades its unpublished wing placements.
  Each is 7,430 triangles. `models/props/extinguisher-v2/extinguisher.vmdl` is the reusable wall assembly, foot at Z=0.
  The guarded native import retained every unrelated OBJ byte and the exact physics nodes; the saved scene and user's
  camera/play state were preserved. Both dressing models and the standalone prop compiled, and all nine materials loaded.
  `railhead_check_extinguisher.py` and `output/railhead/extinguisher-v2/validation.json` record the checks; native matched
  before/after and close views are in `output/railhead/quality/extinguisher-v2-{before,after}/`.
- The user asked for a new AAA map, made without the editor or MCP (2026-10-03). Railhead is Hohenwald Hauptbahnhof
  (Hohenwald Hbf, a made-up city), a German terminus at 14:03 on 3 October. It's built by script like Belltower and
  Reef Hall (`Tools/map_kit.py`), from these scripts:
  - `railhead_station.py`: the structure. It has a real terminus's figures (its docstring has them):
    - 760 mm platforms and standard gauge;
    - a shed of two 30.5 m iron-and-glass spans, like Frankfurt's and Leipzig's;
    - the sandstone head building with its vaulted booking hall and gallery;
    - the footbridge, the platform canopies, the cab roads' arcades, the goods sheds on their loading banks and the
      signal box.
    - The footbridge's inside handrail ran its whole length, so it crossed the top of each stair at waist height (the
      user's screenshot, 2026-10-05). It now stops at each stair's opening and turns into the stair's handrails,
      which run on 6 over the deck to meet it. It has no collision, so it never blocked anyone.
    - Each footbridge stair's upper flight starts at its landing (z 106), and nothing filled the space under it. From
      under the bridge you could walk into it between the parapets, and see out through the flight's undrawn underside
      (the user's screenshot, 2026-10-05). Now that space is solid (a collision box), closed by a concrete face at the
      deck's end under the girder. The hall's gallery stair was already walled in.
    - The wings' doors from the concourse had arches up to 220, over the wings' ceiling (208), so each arch's head
      opened into the ceiling slab, whose edges aren't drawn: the sky showed through it (the user's screenshot,
      2026-10-05). The doors now end at 200 and the windows at 204 (`WING_DOOR_CROWN`, `WING_WINDOW_CROWN`). The info
      sign that hung in the doorway, where its ceiling plate looked to float, hangs 60 further in (n 1420), its rod
      going up behind the arch.
    - The footbridge's and the platform canopies' lights were boxes whose whole underside glowed (48 by 8 on the
      bridge); the user found them blocky (2026-10-05). They're now `luminaire`s: slim surface-mounted LED battens
      (1.5 m by 75 by 60 mm aluminium, chamfered, with end caps) whose lit part is a narrow opal lens.
  - `railhead_props.py`: the track and its equipment, the rolling stock, containers, furniture and yard clutter. Its
    docstring has each prop's API, conventions and triangle and collision budget.
    - Track: UIC 60 rail, crossovers, buffer stops, Ks signals and the overhead line.
    - Rolling stock: two-car double-deck EMUs, a locomotive and coaches, and wagons.
      - The EMU (`emu`) was a low single-deck unit until 2026-10-05, when the user asked for it to look like a picture
        of a German double-deck regional train: a raked, wrap-round windscreen under a black visor, headlight clusters,
        grilles either side of an automatic coupler, two decks of windows, a light grey stripe low down and a grey roof.
        It's 4.63 m tall (182.3) and still 1540 over the couplers, with its open doors where the old one's were. Its
        visors show the departures board's trains in dot-matrix LEDs drawn as geometry (`EMU_FONT`, `destinations`):
        RE München at Gleis 3, RE Nürnberg at Gleis 4. The picture's operator logo was left out.
      - The luggage cart got round tyres on rims, a plank deck, a drawbar fork with a towing eye, slatted crates,
        strapped suitcases and a kit bag (2026-10-05).
      - Both were checked only in offline WebGL renders of the generators' output with the map's textures, not in the
        engine: rerun `railhead_map.py` to rebuild the models.
    - The grey car parked at each cab road's south end (n -900) is `suv` (2026-10-05, from the user's picture of a
      modern crossover): a lofted body (`_suv_profile`) shaded smooth per part (`_Smooth`), black cladding and arch
      flares, a honeycomb grille, an LED light bar with boomerang intakes, dark 19-inch alloys, roof rails, wrap-round
      tail lights and German plates ("HW K 318", `PLATE_FONT`). No maker's badge. The taxis and the red and blue
      cars are still the old `car`.
    - The white van on the east and west cab roads (e ±1940, n -900) is `van` (2026-10-05, from the user's picture of
      a modern large panel van): 5.99 m long, 2.04 m wide and 2.36 m tall. Like `suv`, it's lofted through
      `_road_body`, which both share. It has:
      - a steep windscreen over a short bonnet, and a grille of four bars leaning back between slim headlights;
      - a black bumper and sill band, with a silver sill strip;
      - a cab door, a sliding door with its rail, and glazed rear doors;
      - tall black mirrors, steel wheels and vertical tail lights.
      No maker's badge.
    - The parked cars and vans sat on the station's ground level (z 0), 6 above the cab roads' carriageway, so they
      floated. They now stand on it (`railhead_station.ROAD_Z`, -6), stand-ins included.
    - Car paint is `railhead_materials.PAINTED` (`rw_car_grey` and five more): vmats only, a flat tint on
      `materials/default/default_color.tga` with one roughness, since every texture's dirt and the trains' panel seams
      looked wrong on a car. The signals' dark lenses and the lamps' opal glass are PAINTED too. The vmats were written
      straight from `painted_vmat`; `railhead_materials.py` writes the same ones.
    - Furniture and clutter: benches, machines, kiosks, shelters, hanging displays and signs, clocks, lamps, fences,
      pallets, cars and vans.
    - The concourse's bin stood 1.6" into its bench's end, its slots to the wall, and the booking hall's back-to-back
      benches met at their backrests (the user saw the first, 2026-10-05). The bin is now at e 622 facing the
      concourse, and the hall's benches are 24 apart like the platforms'. A check of every piece `use` places, by the
      bounds of what it draws, found no other overlaps.
    - The kiosks (`kiosk`; `railhead_map.KIOSKS`: the concourse's two, 100 by 80, and the centre platform's, 100 by
      120) were rebuilt on 2026-10-05 after the user's picture of a modern station kiosk: "dont stop until its really
      AAA like the img". The old one was a dark box with a hatch and coloured blocks for goods.
      - The body: anthracite cladding (`rw_steel_dark`) in 24 in panels with shadow gaps, split at counter height, on
        a recessed black plinth. On top, a fascia proud of the walls under a flat roof slab, with warm LED strips under
        its overhang.
      - The fascia reads "Kiosk" and "Zeitschriften · Getränke · Snacks" in white on the front and both ends. A pier
        left of the window has line icons: a newspaper, a bottle and a crisp packet.
      - Under the window, a light stone counter (`rw_kiosk_stone`) on vertical oak slats, with an LED strip under its
        front edge. On the counter: a trailing pothos in a white pot (`_plant`, `VINES`), a card terminal and a pen
        cup.
      - Behind the counter, three bays of lit wood shelves on a warm white back: magazines, then sweets in trays and
        crisp packets (foil pillows, `_packet`), then 0.5 l bottles (`_bottle`, lathed).
      - The right end has a menu board and a framed poster, the left end the staff door, the back a louvred vent.
      - Two lights each (`kiosk_lights`, in `lights()`): one in the window over the shelves, and a small one under the
        counter washing the slats.
      - `Tools/railhead_kiosk_art.py` draws the rw_kiosk atlas: the lettering, icons, menu, poster, the covers, packets,
        labels and wrappers, and the card terminal's screen. It's plain Python (it reads the fonts' glyf outlines and
        fills them itself), so it runs without numpy or PIL. The lettering is alpha-tested and self-lit, along with
        the screen. railhead_materials lists the atlas (`ATLASES`, `OWN_SCRIPT`) but doesn't draw it. Its counter,
        shelf, plant and bottle paints are PAINTED.
      - The atlas's four PNGs aren't in the repository: the session that made them couldn't upload to its LFS store
        (the storage host was blocked there). `railhead_map.py` draws them when they're missing (~12 s), so a run
        brings them back. Commit them from a machine that can push LFS.
      - Every name on it is a plain German word (REISEN, Chips, Wasser...): no real title, brand or logo.
      - Checked only in offline WebGL renders of the generator's output with the textures, not in the engine. Rerun
        `railhead_map.py` to rebuild the models.
    - The snack machine on each outer platform (`vending_machine`, n 300 against the shed's wall) is a modern black
      one, rebuilt on 2026-10-05 as close as it could be to the user's picture of one. It's 990 x 850 x 1830 mm:
      - the glass door shows five shelves of four slots in their spirals, each slot's code (A1-E4) in white on the
        dark rail under it: crisps, chocolate, biscuits and sweets in pillow packs (`_pillow`), four 500 ml cans and
        a bottle of water (`_vlathe`);
      - LED strips light the window's top and sides, the cabinet's top corners and the pick-up bay's PUSH flap;
      - a brushed steel panel holds the touch screen ("SELECT YOUR ITEM", in English as in the picture), the keypad
        (1-9, a red cross, 0, a green tick), the contactless reader under its LED and the card slot.
    - Its pictures are the `rw_vending` atlas (`railhead_materials.vending`, `VENDING_GOODS`), the goods self-lit a
      little as from the machine's LEDs (`VENDING_GLOW`). Every brand is made up. The picture's SunBite, Chunky,
      Twisties, Mintel and Citra are real names or close to them, so those are SolBite, Chunko, Knotties, Mintle and
      Citraze. The cabinet is `rw_satin_black` (PAINTED): `rw_black`'s scuffs read as dirt over a whole cabinet.
      `VENDING_COLUMNS` is in both scripts: change them together. 5.4k triangles each.
    - The atlas's four PNGs aren't in the repository: LFS uploads were blocked in the session that drew them, as for
      the kiosk's. `railhead_map.py` draws them when they're missing (`railhead_materials.vending_missing`, ~15 s),
      so a run brings them back with the models. Commit them from a machine that can push LFS.
    - Checked only in offline textured software renders of its OBJ beside the picture, not in the engine. Rerun
      `railhead_map.py` to rebuild the dressing models.
    - `--preview <dir>` renders its showcase.
  - `railhead_backdrop.py`: the city round the station. Its docstring has the layout and the sources.
    - The play area's east and west walls are rows of five-storey Gründerzeit (1880-1910) tenements across the cab
      roads (`edge_blocks`, the only backdrop model with collision). Each side is built in place, in its own colours,
      so its shop signs read the right way round: don't mirror it.
    - North: the Bahnhofsplatz with its tram stop, the hotel and office block facing the station, and the cab roads
      running on north. The east cab road's view ends at a minster's twin spires (76 m), the west's at a brick hall
      church (71 m).
    - South: the line runs out in a cutting to a tunnel portal at n -8000. The cutting has a road overbridge
      (n -3100) and a railcar depot, with a machine works, a gasholder, allotments, a village on the hill and woods
      beside it.
    - The Rotunde (`rotunda`, 2026-10-05) stands on the hill over the tunnel, in its park. Seen down the west cab road
      past the goods shed, the hills there were one big flat-shaded green mass (the user: "the shitty green hill").
      The user sent an AI-made picture of that view with a grand iron-and-glass hall there and sky above, and asked
      for it "as close as possible".
      - It's an exhibition rotunda like Vienna's of 1873 (108 m): a drum 107 m across on the line's axis
        (`ROTUNDA`, centre n -10400), 51 m to its zinc cornice.
      - The drum is 36 bays of two lights, iron framed (`rotunda_light`), with three tiers: tall arched windows
        with tracery, a gridded clerestory, and a latticed frieze. Its roof is a low zinc cone with a glazed ring,
        under 10 degrees so the rim stays its skyline from the streets.
      - The south hills beyond the portal are gone (`south_z`): the park is level round it (`ROTUNDA_BASE`, 700),
        then low farmland and woods roll to ~1300 out to the ring hills. Oaks ring the park, and three big trees by
        the overbridge's west ramp (`ramp_trees`) frame its lower half from the cab road, as in the picture.
      - Its paints are PAINTED (`rw_rotunda_glass`, `_iron`, `_panel`, `rw_zinc`), vmats only. 7k triangles; the
        south model is 21.5k of its 80k.
      - The user's screenshot was fitted from the station's arches and the vanishing point: eye (-1845, 1080, 58),
        71.5 degrees horizontal, 3.3 east of south and 5.3 up (`VIEWS` `cab_west_south`). From there its rim is 15
        degrees up and its centre 9 east of south, as in the picture.
      - Checked only in offline textured renders of every model (a C rasteriser in a scratch session), from that
        camera and from the east cab road, the footbridge, the throat, the portal and the air. Not seen in the engine;
        rerun `railhead_map.py`.
    - Round it all: a skyline of 55 m blocks out to ~600 m (the city's ground ends at 24500, `R0`), with a Baroque
      onion dome, a 1970s office tower (104 m), a slab block, a brewery chimney and a water tower, then hills rising to
      86 m by the world's edge (40000, ~1 km).
    - 188 trees are Facepunch's cloud oaks and beech bushes, in the scene's `__references` as Belltower's are.
    - The junctions' traffic signals (`traffic_light`) were black boxes with square red and green lamps, both lit (the
      user: "these traffic lights look terrible", 2026-10-05). They're now German signals at RiLSA's sizes:
      - a galvanised pole 114 mm across and 3.6 m tall;
      - a head of three 200 mm lenses, each under its visor, in a black backplate with a white edge;
      - one lens lit (`lit`: red at both junctions) and the others dark tinted glass (`rw_lens_*`).
    - The candelabra's lanterns were glowing cubes, and the street lamps' undersides glowed too, at 14:03 on a sunny
      day. The lanterns (`lantern`) now have four opal panes, iron corner posts and a pyramid roof, and every street lamp
      is off (`rw_opal_glass`).
    - Both were checked only in offline renders, not in the engine.
    - `--preview <dir> [view ...]` renders its own 31 views, with the station from `railhead_station`.
    - The map script lays the corridor's track, ballast and overhead line from the throat to 20 m into the tunnel,
      and the depot's lead off track C (`depot_lead`). The depot pit's wall splays out from the bridge to `THROAT_E`
      so the lead runs in beside it, and the lead's sleepers stop where C's are under them.
  - `railhead_materials.py`: the rw_ paints, drawn with numpy into `Assets/materials/railhead/`, and their atlases
    (`ATLASES`, `rect_uv`): signs, displays, posters, shop signs and the bronze lettering. The texts are German words,
    generic train categories (RE, RB, S, IC) and made-up places, with no real operator's name, logo or clock.
  - `railhead_sky.py`: Belltower's sky baked again with Railhead's sun (38 degrees up, 15 west of south: 14:03 summer
    time on 3 October at 48 N, 11 E). The scene's sun takes the same angles.
  - `railhead_preview.py`: flat-shaded views for `--preview`.
- The map script dresses the station (where every train, sign, bench and lamp goes) and writes:
  - the models, to `Assets/models/maps/railhead/`;
  - the scene, `Assets/scenes/maps/Railhead/railhead.scene`, rewritten whole on every run (change the layout in the
    script, not in the editor);
  - the radar picture, `ui/minimaps/minimap_railhead.png`.
  - `--preview <dir> [view ...]` writes the views and the reach grid's picture, and `--backdrop` puts the city in them.
    With `--art` it also writes the menus' stand-in picture, `ui/maps/railhead.png`, from the aerial view. Replace that
    with an in-engine capture.
- The layout is mirrored across e = 0. Red Team spawns on the west cab road and Blue Team on the east. There are three
  lanes:
  - North: the concourse across the platforms' heads, with the booking hall behind it. Bomb site A is the concourse's
    east end.
  - Middle: the platforms under the shed, crossed by the footbridge. Trains stand at four of the six tracks.
  - South: the platform ends under their canopies, the throat round the signal box, and the goods yards. Bomb site B is
    in the east goods yard, among the containers.
- Modes: the scene lists TDM and Defuse.
  - Deathmatch has its own spawns.
  - Retakes has spawns per site, as Belltower's are.
  - Domination's flags are on the outer platforms (A west, C east) and the centre platform (B).
  - The Hot Zones and the Cash Grab points are `ObjectiveSpot`s.
  - It's in `GameUtils.MainMenuMapOrder`, `IsMainMenuMap` and `IsMatchReadyMap`.
- Every run checks all 97 spawn, objective and cash spots, as Belltower's does:
  - room for a player and a floor under each;
  - a walk to each from the spawns (`check_reach`, a 2.5D grid that stands in for the navmesh);
  - that no Retakes Red spawn can see a Blue one.
  On 2026-10-04 all three passed.
- The navmesh:
  - Its bounds stop at `NAV_TOP` (420): over the footbridge's deck, the highest floor anyone walks on, and under the
    shed's roofs.
  - The canopies' glass and the goods sheds' roofs are in `railhead_glass`, tagged `navskip`, which the NavMesh's
    `ExcludedBodies` leaves out. On their own they'd be islands.
  - Islands left below NAV_TOP are the roofs of the trains, the platform canopies, the footbridge, the wings' closed
    upper storeys, and the kiosks and shelters. Nobody can reach them, and bots check their paths.
- Theater doesn't record it: there's no MapInstance for playback to load.
- To play it: `dev_mode team_deathmatch railhead`.
- Made offline. When the editor next opened on the project (2026-10-04), it compiled the scene, the 15 models, the 68
  materials (~275 MB of PNGs) and the sky with no errors.
  - The log's one Railhead error, `Error loading resource file "prefabs/game_modes/team_deathmatch.prefab,
    prefabs/game_modes/bomb_defusal.prefab_c"`, is harmless. The engine's dependency scan reads the scene's
    `GameModes` metadata (`MapInformation`'s ", "-joined list) as a path, and every scene with two modes gets it.
  - None of it was checked in the engine then. The AAA pass (below) checked the navmesh and the look.
- The AAA pass (2026-10-16/17, the user's goal "get railhead AAA with a workflow"). Round 1 was a workflow of five
  areas (materials, structure, props, dressing, backdrop), each building into its own stage
  (`output/railhead/stage/<area>`, `railhead_map.py --stage DIR`) and judged from Cycles renders
  (`railhead_render.py`), then merged into Assets and judged again from engine captures. The user then asked for no
  more subagents, for the usage, so round 2 was done directly. What each area added:
  - Materials (`railhead_materials.py`, `railhead_finish.py`, `railhead_scanned.py`):
    - milky, sooty rolled roof glass;
    - a light marble terrazzo in panels with brass strips and matte walking lanes, and a coursed sandstone ashlar.
      Round 1's small chips mipped to a vinyl-like speckle; round 2's large Venetian chips, a quarter of them dark at
      full colour on a darker matrix, read as gravel from 3 m in the engine. Round 3 (`TERRAZZO_CHIPS`,
      `TERRAZZO_MATRIX`, `TERRAZZO_GROUND`): mostly light chips, the dark and red ones a scattering, ground part of the
      way to a lighter matrix, so it's calm at a distance and still terrazzo close up;
    - dressed stone in beds with iron blotches and chisel marks (round 2: it read as painted MDF);
    - lime plaster (plain, sooted and dado) and a Reichsformat brick in cross bond (`railhead_finish.py`);
    - riveted iron with rivet rows and chipping, and powder-coated steel;
    - basalt ballast with dark voids, oil-soaked sleepers, paired granite kerbs and granite setts;
    - the asphalt. Round 2 took its baked wheel paths back to two faint ones (`ASPHALT_WHEEL_PATHS`): with the
      dressing's they read as four black scribbles a lane. Its sealed cracks are off (`SEALED_CRACKS` 0), as they
      repeated down the road every tile.
    - Tile sizes changed (paving 240, sandstone 192, steel 128, glass roof 192, kerb 96): rebuild the models after a
      material change, since their UVs come from `paints()`.
  - Structure (all drawn only: every station box and hull is as it was, east and west 322/38, centre 193/134, roof
    0/142):
    - `railhead_architecture.py`: one-casting shed columns with bases, capitals and spandrel brackets, the valley
      girder's flanges and rivets, the canopies' structure, and the booking hall's pilasters, entablature, dado,
      archivolts and doors. Its shapes come from `railhead_profiles.py`.
    - `railhead_structure_detail.py` (round 2), after the engine captures showed a flat dark footbridge, blank white
      stair parapets and plain punched wing fronts: the footbridge's riveted plate-girder sides, precast parapets
      with V joints, the goods sheds' braced sliding doors on roller hangers, the wings' cab-road fronts (archivolts,
      Lisenen, window surrounds, a dentilled cornice), and soot run-off on the shed's arcade.
    - `railhead_ironwork.py` (bridge and column details) and `railhead_structure_paints.py` (parapets, roof sarking,
      the footbridge's panels, the goods shed's doors).
  - Props:
    - `railhead_running_gear.py`: wheelsets and bogies for every rail vehicle.
    - `railhead_roof_kit.py`: the EMU's roof equipment and cab doors.
    - `railhead_vehicle_kit.py`: the road vehicles' set-in glazing, cab interiors and lamps.
    - `railhead_ohl.py`: DB Re 200 overhead line and the Ks signals' fittings.
    - `railhead_furniture.py`: street, platform and yard furniture.
    - `railhead_prop_materials.py`: their materials, with the buffer stops', train's, ticket machine's and
      luggage's own scripts.
  - Dressing (`railhead_dress_detail.py`, `railhead_map.py`):
    - a working station's wall kit: conduits, City-Light posters, a help point, signs and notice boards;
    - gullies and manholes, more lights (168), and the cab rank with taxis, bollards and a taxi post.
    - Two Retakes spawns at site A moved, so `check_retakes_sight` is 0 (it was 2).
    - Small props collide, as everything drawn on the map does: benches, 1 m bins, bollards, lamp posts, a skip,
      tyres, drums, the info pillars, and the bins beside the footbridge's stair openings.
    - The cab roads' cycle stands (`railhead_dress_detail.cycle_stand`, four a side at n 1335) are one swept tube
      now (`tube`: mitred rings, carried along without twist, smooth normals, u along it), in `rw_stainless`, with a
      rosette at each foot (2026-10-25). They were 15 separate open rods in `rw_steel`, and the wedge each joint left
      round the bend showed the paving through as white bands (the user's screenshot). Use `tube`, not a chain of
      `rod`s, for anything bent. `Tools/railhead_stage_cycle_stands.py` swapped just their triangles in the
      installed dress OBJs (it finds the old stands by vertex and refuses if any are missing). Checked in offscreen
      editor captures (`output/railhead/cycle-stands-v2/after/`), where the probes don't render, so the metal reads
      darker than it will in a match. Not yet seen in a match.
  - Backdrop (`railhead_backdrop.py`, `railhead_backdrop_art.py`): the tenements' balconies, awnings and fascias,
    the near shops, and a far city in place of grey boxes. The Rotunde card is rebaked in Cycles by
    `railhead_rotunda_rebake.py` (one GPU render at a time, `output/railhead/stage/.gpu-lock`).
- Rebuilding into Assets, in this order (A = the absolute path of Assets):
  1. The materials: `railhead_materials.py [names]`, `railhead_finish.py --stage Assets --only`,
     `railhead_structure_paints.py <A>`, `railhead_prop_materials.py --out <A>`, `railhead_buffer.py --out <A>`,
     `railhead_train.py --out <A>`, the ticket machine's and luggage's scripts, `railhead_backdrop_art.py <A> --force`,
     `railhead_sky.py` and `railhead_rotunda_rebake.py <A> --samples 128`. Run `railhead_finish` after
     `railhead_ironwork`, which writes the old scanned brick.
  2. `python Tools/railhead_map.py` (~10 min).
  3. In the editor, `Sources/Railhead/editor/compile-stale.cs.txt` (run_csharp; `output/railhead/compile.json` picks
     `only`, `limit` and `force`): the materials (in batches of ~80 under the CLI's timeout), then the models, then the
     scene. The open editor's file watcher compiles each model and the scene as the build writes them.
     - Don't force-compile the models. On 2026-10-17 that held the editor's main thread for over two minutes ("Stall
       detected") on the 2.5 million triangles, and the editor closed and was reopened.
     - Check them instead with `model-check.cs.txt`, which only loads the compiled models. It writes each one's
       collision hulls (a box is a hull) and materials to `output/railhead/model-check.json`, to compare with the
       build's counts and the vmdls' remaps. A remap whose `usemtl` group has no faces isn't in the compiled model
       (the roof's `rw_steel`).
     - The file watcher can compile a model from its new OBJ before its new vmdl is written. The check catches that.
  4. `capture.cs.txt` (views in `output/railhead/captures/config.json`, textures at 1024) and `navmesh-check.cs.txt`.
- An anchored paint (`ANCHORED`: its picture's foot at z 0) with a v scale (`TEXCOORD_SCALE`: the containers' 48 x
  102 in walls) also needs a v offset of minus the scale (`g_vTexCoordOffset`, written by `vmat()`). The engine flips
  v on import (1 - v) before `uv * g_vTexCoordScale + g_vTexCoordOffset`, so without it the picture started 48/102 up
  the wall, and the bomb B container wore its rail's dark band and rust across its middle (z 48). Containers stand
  only at z 0 and 102 (stacked), where the anchor holds.
- An alpha-tested picture must be a power of two on both sides: the engine can't make the alpha-weighted mips of
  `bd_vinyl`'s 256 x 384 ("Cannot filter non-power-of-two texture"), and the material fails. It's 256 x 512 now.
- The open editor compiles a changed picture as it lands and holds it while it does, so writing one in place failed
  (OSError 22). `railhead_materials.save_image` writes through a temporary file renamed over the picture, retried for
  up to 10 s.
- The indirect light (`Sources/Railhead/lighting`, `Assets/lighting/railhead/daylight-v3`: grid 30,21,8, intensity
  2.4) was baked on 2026-10-14, before the AAA pass. To rebake: open Railhead in the editor (ask first: it's shared),
  run `bake-lighting.cs.txt` (`output/railhead/quality/bake-config.json` names the folder), then
  `python Tools/railhead_quality_lighting.py <folder>` and rebuild the scene.
- Checked in the editor on 2026-10-17, after rounds 2 and 3:
  - every compiled model matches the build (`model-check.cs.txt`);
  - 37 views captured (`output/railhead/captures/round2`, the round 3 fixes in `round3`);
  - the navmesh check found complete paths from both teams' first spawns to all 99 spawns, sites, objectives and cash
    spots.
  Not checked yet:
  - a match played on it, its bots, and the modes' objects in play;
  - the indirect light rebake.
  Still open from the critique: the road vehicles' plain bodies, the EMU's flat red paint, and the yard's skip.
- The cab roads' cars are off (2026-10-25, `railhead_map.ROAD_VEHICLES_ENABLED = False`): the user will rework them, so
  their code and placements (`cab_road_vehicles`; `railhead_props.car`, `suv`, `van`) are kept. Set it True to bring
  them back. Their collision was in the dressing models, not the scene, and the spot, reach and Retakes checks pass
  without them (the taxi rank's lettering, posts and oil stains stay).
- The head building wings' City-Light poster (Alpen east, Fahrrad west) and extinguisher are on the wing's inner wall,
  the hall's side wall at e ±640.5 (`railhead_map.wing_wall_kit`, n 1540 and 1400), facing the cab road's door. They
  were on the outer wall, which has no run wide enough between its door (`WING_DOOR`, 1430..1530) and windows: the
  poster hung in the doorway (the user: "floating sign") and the extinguisher's sign in front of the window at 1380.
  - Published on 2026-10-25 by a splice, not a rebuild: `output/railhead/wing-poster/stage_wing_poster.py` builds the
    old and new pieces with the generator's own code, finds the old triangles in the installed dressing OBJs by
    material and each corner's v/vt/vn text, drops them and appends the new ones, and its `--apply` refuses a file
    that changed since staging. That day several sessions spliced the same dressing OBJs (the cycle stands, the
    footbridge's signs, the cars), so stage from the files on disk, never HEAD or a copy read earlier.
  - Checked in isolated-scene renders of both wings (`output/railhead/wing-poster/after/`), not yet in a match.
- The platform bench (`Tools/railhead_bench.py`, 2026-10-25, the user: the armrest "looks quite low poly/blocky" and
  the slat ends looked broken):
  - The slats are eased boards (`slat`: 7 mm round edges, square-cut ends). rw_wood is a scan of planks with dark gaps,
    so each face maps onto one plank of it (`PLANKS`: the picture's columns between the gaps), and the ends show end
    grain (`rw_wood_end`, `railhead_prop_materials.write_bench`: the gunsmith range's oak end grain, tinted). Mapped by
    world projection, every slat had a black line along it and across its end.
  - The middle armrest is one swept casting (`armrest`): a rounded-square section along a spline from a foot plate on
    the front slat, widening over the hand rest, into the backrest. It was four square bars with a gap at the bend.
    `railhead_furniture.bench_details` draws it when the bench passes its backrest, else the old bars.
- `railhead_buffer.bevel_box`'s eight corner triangles were drawn at points on the box's edges b from its corner, which
  stood out past the bevels as shards and left the corners open (the user saw them on the slat ends). They now join
  the broad faces' corners, so the box is closed. It's used all over Railhead's props (bins, cases, plates, the
  vehicles' and trains' kit), which changed with it. The luggage trolleys' and the signal frame's own models
  (`railhead_luggage`, `railhead_signal_frame`, written only when missing) still have the old corners.
- The footbridge's ceiling battens hang from the undersides of the two purlins they cross
  (`railhead_architecture.BRIDGE_PURLIN_D`); flush with the roof they ran through them. The platform canopies' battens
  are one in each bay between the cantilevers (`railhead_station.CANOPY_BATTENS_N`, still over the canopy lights'
  n), where they ran through the cantilevers, and the outer canopy's west line, which lay inside a purlin, hangs under
  it (`railhead_architecture.canopy_purlins`).
- The footbridge's notice frames are A3 on the steel panel under the handrail (deck + 11 to 28.5, under the brackets'
  wall plates at 30.5). As A1 frames from deck + 22 they ran past the handrail onto the glass.
- `railhead_map.py --stage DIR` also draws the radar picture into the stage.
- Several sessions edit Railhead's generator and its installed OBJs at once, so publish a change as a splice, not a
  rebuild: a rebuild would publish everyone's half-finished generator edits and drop their spliced faces.
  `output/railhead/cars-bench-20261025/splice.py` builds the affected models twice from one code snapshot ("new", and
  "old" with the change patched back at run time), takes the faces only one of them has, and applies just those to the
  files on disk: every face, remap and collision box it removes must be there. `Sources/Railhead/editor/
  import-staged.cs.txt` copies a publish list (`output/<folder>/publish.json`, the folder named in
  `output/publish-target.txt`) into Assets, refusing any file changed since it was staged.
  - Since 2026-10-25's extinguisher-v2 import, `railhead_dress_<side>.vmdl` renders
    `extinguisher-v2/<side>-base.obj` plus `extinguisher-v2/<side>.obj`; `railhead_dress_<side>.obj` is the base plus
    the extinguishers and isn't rendered. Splice into both.
  - Never import every Tools module to freeze the snapshot: `railhead_rotunda_padding.py` pads
    `Assets/materials/railhead/rotunda_impostor.png` at import (it happened on 2026-10-25 and was put back from git),
    and `railhead_civic_asset.py` and `railhead_rotunda_bake.py` do work at import too.
- Published on 2026-10-25 by that splice: the cars off (and off the radar picture), the bench, the corner fix, the
  battens and the footbridge's frames. The six footbridge bins were left to the "Bridge sign overlap" session's own
  splice. Checked in offscreen editor renders before and after (`output/railhead/cars-bench-20261025/captures/`), not
  yet in a match.
- The footbridge's bins (`railhead_map.footbridge_kit`, 2026-10-25, the user: "a lot of overlapping of signs and stuff
  on railhead bridge"). The bin is railhead_props' double one, 40.2 wide (`BIN_HALF_WIDTH`), not the ~28 the code had
  allowed for: the two centre-stair bins (e ±8) stood inside each other mid-bridge and 4 into both stair openings, the
  outer stairs' bins stood in their stair's handrails, and every lid went 0.35 into the bridge's handrail.
  - Now each stands 4 past its stair's parapet (the centre stairs' beyond their Gleis plate, e ±179.6) and 13.5 off
    the panel, its back 1.15 in front of the handrail. Their `taken` entries are unchanged, so the notice frames are
    the same 7 a side.
  - Published by `output/railhead/bridge-bins/stage_bridge_bins.py` (both OBJs a side, and the bins' collision boxes in
    the vmdls). `check_installed.py` there finds no dressing piece on the bridge cutting into its structure. Checked
    in isolated-scene renders before and after (`output/railhead/bridge-bins/{before,after}/`), not yet in a match.
  - From the bridge's north end a platform bracket clock (`outer_wall`, n -140, z 252, 90 past the glass) shows right
    behind the Gleis 6 plate. It's a sightline, not an intersection, and was left as it is.

