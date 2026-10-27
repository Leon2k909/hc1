## Reef Hall (multiplayer map, `Tools/reefhall_map.py`)
- The user asked for an aquarium map for 10-15 players, built as close to 1:1 as possible from five reference pictures
  (2026-10-01): the rotunda round its central tank, the entrance lobby, the control room behind the big panoramic tank,
  the filter hall and the glass tunnel. No rooms beyond those, except connectors in the same style. The look is modern
  concrete, dark metal, glass, blue tank light and warm downlights: no neon, nothing military.
- Built by script like Belltower (`Tools/map_kit.py`). The script's docstring has the layout and conventions. It writes:
  - one model per room, plus the tanks' insides with no collision, to `Assets/models/maps/reefhall/`;
  - the scene, `Assets/scenes/maps/ReefHall/reefhall.scene`, rewritten whole on every run (change the layout in the
    script, not in the editor);
  - the radar picture, `ui/minimaps/minimap_reefhall.png`.
  The materials are `Tools/reefhall_materials.py`'s (`Assets/materials/reefhall/`, drawn with numpy).
- Layout: Red Team spawns in the lobby (west), Blue Team in the control room (east). Three lanes join them:
  - Middle: the West and East Galleries, lined with small tanks, into the Rotunda. The Rotunda's ring balcony (z 208)
    is reached by two curved stairs and by the upper galleries.
  - North: the Filter Hall, with its two glass filter columns, the catwalk and the mezzanine. Bomb site A is its east
    half.
  - South: the Tunnel Hall, a glass barrel vault under a tank, with a sunken aisle (z -40). Bomb site B is its east
    half.
  - Between: the Rotunda's north and south passages, and four service corridors.
- Modes: the scene lists TDM and Defuse. Domination's flags are A (west), B (Rotunda) and C (east). Its Hot Zones and
  Cash Grab points are the halls (`ObjectiveSpot`). It also has deathmatch spawns (28) and Retakes spawns per site.
- Every run checks all 89 spawn, objective and cash spots (room, floor, a walk from both spawns), as Belltower's does,
  and that no Retakes Red spawn can see a Blue one (railhead_map's `check_retakes_sight`).
- The padded transport cases (blue padded panels in a brass frame, `crate` / `crate_stack`) came out on 2026-10-12,
  everywhere they stood, with their cover and collision. The user: "they look awful". Each room still draws the random
  numbers the cases did (`skip_cases`), so nothing else in it moved.
  - Without the stack at (700, -1200) in the Tunnel Hall, site B's Red planter at (700, -1440) could see a Blue
    attacker in the Rotunda. It's at (850, -1440) now.
  - The baked navmesh (2026-10-02) still leaves out the cases' footprints. That's harmless: bots path round empty
    floor. It goes when the navmesh is next baked.
  - Not yet seen in-game.
- Tank glass: `shaders/hc1_tank_glass.shader`, one material per tank (`rh_tank_glass_<tank>.vmat`, with the tank's
  surface height and depth). It reads the depth behind the pane and puts the water in between:
  - Beer-Lambert absorption by the water path, and the water's own scattered light;
  - moving caustics and light shafts;
  - a little refraction, a glass reflection, and acrylic's green at a glancing angle.
  The panes are 8 thick with the `glass` surface: they stop bullets and players, and bots can't see through them.
  Railings' glass panels are 1 thick, so rounds go through.
  - It finds what's behind the pane with `Depth::GetWorldPosition( screen pixel )`, which returns the absolute world
    position. It used to invert the normalised depth itself, which read every pixel as far away, so from a few metres
    off every tank looked solid blue (fixed 2026-10-02).
  - Absorption is kept low (`g_vWaterAbsorb` 0.006/0.0012/0.0006 per inch, turbidity 0.0006): the references' water is
    clear right to the tanks' backs.
- The reef in each tank is the script's own (`rock`, `rock_arch`, `CORAL_KINDS`, `kelp`, `sea_grass`): the big tanks
  get a rock arch, as the references' do. The tanks' insides come to about 1 million triangles in all.
- Light: each tank's lamps (`COOL`) are over its water, and a window 120 or more wide also throws its blue into the room
  (`SPILL`, a light on the room side). Every wall light (`sconce`) has a small unshadowed warm light just off it
  (`SCONCE`, radius 130), so it washes its wall as in the references. `build_mirrored` collects them.
- `hc1_reefhall_views [filter] [exposure]` (`Editor/Hc1ReefHallQa.cs`) renders the views to compare with the
  references into `output/reefhall/`, and `hc1_reefhall_shot name e n z e n z [fov]` one view, eye and target in plan.
  Offscreen renders skip post-processing and screen-space reflections, so the floor's gloss doesn't show in them.
  Run in play mode, they render the play scene, with its bots and the floors' gloss.
- Each room against its reference (2026-10-02):
  - Control room: the panorama is four panes between 64-wide concrete pillars, with a concrete lintel over them. The
    ceiling has a coffer with a warm cove and downlights round it, and the consoles are steel.
  - Filter Hall: each column stands on a concrete base under a steel cap with gunmetal bands, and a pipe rises from
    it to the ceiling. Concrete pilasters with wall lights stand on the south wall between the doors. Downlight lines
    run over the floor and the catwalk.
  - Rotunda: six steel columns stand round the drum, and its lid is a dark disc (`lamp_lid`; `ring=True` adds the old
    white LED ring, which glared). The ceiling's cove round the drum is `rh_frosted_lit`: `rh_led_cool` glared white.
  - Lobby: the coral display's corals sit on the mound's surface and round its foot.
- Control-room consoles (2026-10-14): `reefhall_map.console` delegates to `Tools/reefhall_consoles.py`.
  The three banks now have satin worktops, cabinet access doors and vents, keyboards, trackballs, physical button
  panels and chamfered monitor housings with rear vents/cables. The full-width glowing desk and white base strip
  are gone. Sixteen LCDs sample four quadrants of the ImageGen atlas in
  `materials/reefhall/consoles/rh_console_screen_atlas.png`, with self-illumination 0.85. The source prompt is in
  `Sources/ReefHall/consoles/screen-atlas-prompt.txt`; preserve the atlas when rebuilding materials.
  - `Tools/reefhall_console_refresh.py --out output/reefhall/consoles/staging` stages just the Control model and
    the console materials. Import through the editor when it is open; it does not rewrite the scene or other rooms.
  - The whole Control model is 130,726 triangles after the monitor-back pass below; its original 122 collision boxes and 41 hulls are byte-for-byte
    equivalent. All three banks keep their placement and cover height. The other rooms, tank model and lights
    are unchanged. Cabinet vent bands share a tessellated front plane instead of overlapping thin decal geometry.
  - Materials and model compiled through native MCP. Checked five offscreen engine views, including front/detail,
    rear and room overview, in `output/reefhall/consoles/`. These renders do not reproduce full gameplay postprocessing.
    The menu kept running and the existing Reef Hall scene tab was not edited.
  - Monitor backs (2026-10-14): the user picked a mix of ImageGen concepts 1 and 2. `Tools/reefhall_monitors.py`
    builds eight charcoal/slot-vent monitors and eight graphite/perforated monitors with aluminium stands, in
    paired runs across the three banks. Their rounded shells, recessed vents/ports, VESA plates, tilt barrels,
    rounded feet, service labels and curved cable pairs are actual geometry. Fine shared polymer and brushed-metal
    normal/roughness maps are generated by `reefhall_console_refresh.py` alongside the six `rh_monitor_*` materials.
    The LCD faces/UVs, desk surfaces, lights and collision are unchanged. Import staged materials/textures before
    the Control OBJ/MTL/VMDL through the editor when open. The screen atlas is not regenerated.
    All seven resources (six materials plus Control) compiled through native MCP; four offscreen engine captures
    and the geometry/collision report are in `output/reefhall/consoles/monitor-backs/`. The captures use a temporary
    visual scene, destroyed afterward, and do not reproduce a live match's full postprocessing. No editor scene
    tab or play state was changed by this pass.
- The lobby's west wall (Red Team's spawn side) has three pairs of glass entrance doors, as close as could be got to the
  user's picture of them (2026-10-08). They used to be self-lit frosted panels (`frosted_door`). Now:
  - Each pair (`door_pair`, `DOOR_PAIRS` n -197.5, 0 and 197.5) has dark grey anodised frames (`rh_anodised`) with
    4.5" stiles and 6" rails, and clear glass (`rh_glass`). It also has stainless pull bars on the meeting stiles, a
    closer's cover on the head and a threshold (`rh_stainless`), all in an anthracite portal (`rh_portal`).
  - The picture's doors look about 3 m tall, so they're drawn at 1.25 times a real 95" leaf (`DOOR_S`).
  - Frosted vinyl on the glass (`rh_film`, alpha tested): two wavy lines across both leaves and a plain jellyfish on
    each right leaf. `reefhall_materials.film` draws the film as one picture across the pair (`FILM_W`, `FILM_H`,
    `FILM_WAVES`, `FILM_JELLY`). `door_pair` maps each leaf's glass onto its share of it (`uv_quad`), so the waves run
    on from one leaf into the other.
  - The wall round them is satin cladding with shadow gaps (`clad`, `rh_panel` / `rh_panel_b`), with a downlight and a
    warm wash over each pair.
  - Between the pairs stand tapered bronze planters (`bronze_planter`, 46" tall) with dracaenas (`dracaena`: strap
    leaves in `rh_leaf`). Each planter has a metal hull.
  - The doors are shut for good: one glass box fills each opening. Behind them is a closed gallery (`door_gallery`,
    `DOOR_GALLERY` e -3200..-2920, n -400..400), there only to be seen through the glass:
    - four tanks in its back wall and one in each end wall, stocked like the rest;
    - a dark column, and a raised planter with a dracaena, behind each pair;
    - cool lights, so every pair shows blue from the lobby.
    It has no spots. The navmesh stops short of it, and the minimap leaves it out.
  - Checked only in offline Cycles renders of the OBJs with their textures (a scratch wrapper round
    `railhead_render.py`, with the tank glass as tinted water and no fish). Not yet seen in the engine.
- `map_kit.write_text` retries the final rename for up to 10 s: the editor or OneDrive can hold a file being replaced.
- Doorways have no doors, since bots can't open doors. The lobby's glass entrance doors are shut for good (above).
- The Rotunda's curved stairs (`round_stair`) had both side faces pointing into the steps, so the near side was
  culled. The user saw the alcove tank through the stair (2026-10-12). Now the inner side faces the centre and the
  outer side away from it. A check of every face's normal against the steps' solid found 0 of 210 facing in (104
  before). Not yet seen in-game.
- `map_kit.write_obj` now reads `tile_overrides` before `BT.tile_units`. Before, `dict.get`'s default called
  `tile_units` even for an overridden paint, which fails for paints `building_textures` doesn't know.
- Never let the editor compile a vmdl whose OBJ has no faces: it hangs for good, with one thread at 100% and nothing
  logged. The service rooms have no tanks, so `reefhall_service_tanks` was an empty OBJ.
  - On 2026-10-01 it froze the editor until Windows killed it.
  - On 2026-10-02 it froze every editor start, at the startup asset compile.
  - Now `map_kit.write_model` writes no empty model and deletes any old one (`is_empty`, `delete_model`), and
    `write_scene` leaves out a room's Tanks object when it has none.

### Reef Hall's animals (`TankFauna`, `hc1_fish.shader`, `Tools/reefhall_fauna.py`)
- The user asked for realistic fish in every tank, suited to it, alone, in small groups and in schools, that never
  swim into the glass, rocks, plants or each other (2026-10-02). They sent pictures of 14 species. All but one are
  here, life size, in real colours, alongside the grey reef sharks and manta rays from before:
  - blue tang, yellow tang, copperband butterflyfish, red lionfish, regal angelfish, mandarinfish;
  - white-spotted puffer, blue-green chromis, yellow-and-blueback fusilier, Banggai cardinalfish;
  - Indo-Pacific sergeant, Moorish idol and ocellaris clownfish.
  The freshwater angelfish is left out: every tank is a reef. The Filter Hall's two glass columns are sand filters, so
  they hold no fish.
- They're scenery: each machine runs its own, nothing is networked, and nothing runs on a dedicated server.
- `Tools/reefhall_fauna.py` builds the 15 animals (lofted bodies, lens-shaped fins, colours painted with numpy from
  where each texel is on the fish) into `Assets/models/maps/reefhall/fauna/`, with `fauna_species.json` (each one's
  reach, height, length and nose). Its docstring has the sizes and the texture layout. `--preview <dir>` renders them.
  How each species swims is its `SPECIES` entry: speed, turn rate, response, climb, bank, depth band (`low`/`high`, a
  share of the water's height; `above`, inches over the sand), how often it goes to a rock, a home's radius, how often
  and how long it hovers, its group and spacing, and its tail and fin beats.
- `shaders/hc1_fish.shader` swims them in the vertex shader:
  - A fish's wave runs from head to tail, growing towards the tail. A ray flaps its wings, the wave running back.
  - The pectorals (the texture's U 0.5-0.58 strip) scull from their roots.
  - TankFauna drives each one's `SwimPhase`, `SwimAmount`, `FinPhase` and `FinAmount` (`SwimDriven` 1): the tail beats
    harder when it speeds up or turns and barely when it hovers, when the pectorals scull instead.
- `Code/Maps/TankFauna.cs` (one per tank's water) moves them. Each species is a `Groups` entry, "key=value" pairs
  (`Species.Parse`), written by `reefhall_map.fauna_spec`.
  - The water is a box or an upright cylinder, less a glass tube (the tunnel) and the tank's rocks, coral and kelp
    (`Obstacles`: cones, which kelp's negative taper widens upwards).
  - Groups: `solo`, `pair`, `shoal` (loose, milling) or `school` (tight, aligned). A group follows an invisible leader
    that turns more slowly than its fish and keeps the whole group's room clear. Each fish holds a drifting place round
    it, so the group keeps a loose shape and turns together. Where a group doesn't fit, its fish live alone.
  - Lone fish and leaders swim to points they can reach in a straight line: in their depth band, or beside a rock
    (`rocks`), near a home (`home`: the clownfish's and Banggai cardinals' patch of reef). On arriving, some hover
    for a while (`pause`), turning slowly to look about.
  - Steering: back towards the depth band and home, away from the walls, glass, sand and rocks within a soft margin,
    and away from other fish (the smaller gives way, and every fish keeps well clear of a shark or a ray; leaders take
    their group out of a big animal's way). It feels ahead, and when that's blocked it looks round a fan for the open
    way nearest where it wants to go and turns into it, slowed down. Turns ease in and out (`response`), and pitch and
    bank are limited per species, so big animals turn wide and slow.
  - Hard limits: each body keeps its reach clear of the water's edges and the rocks, and a move that would end deeper
    in is taken back. `Separate` then pushes any two bodies that overlap apart (a segment from nose to tail with its
    half-thickness and half-height each, `BodyLine`), the smaller one most, never into glass or rock.
  - Past `FarDistance` from the camera a tank updates 4 times a second, and small fish aren't drawn past
    `CullDistance` (260 lengths, 800-3000).
  - In the editor nothing is culled (`Scene.IsEditor`): its view is the editor's camera, which the scene can't see.
    The scene's `Scene.Camera` there was the minimap's capture camera (`MinimapRenderer`, 7500 over the map), so every
    tank counted as far off and only the sharks and rays showed (the user: "wo sind die fische?", 2026-10-02). That
    camera is no longer a main camera (`IsMainCamera` false).
  - The fish are life size, so most are 2-6" long: from the middle of a gallery they're specks, and they're best
    seen from the glass.
- `reefhall_map.py` stocks each tank by its size (`fauna_class`: small, mid, big, huge), from that class's mixes
  (`FAUNA_SMALL` ... `FAUNA_HUGE`), neighbours taking different ones. A group shrinks until it has open water in its
  band (`FAUNA_ROOM`, `free_share`); a species with none is swapped for a small one that fits. The scene has 74 stocked
  tanks and 1439 animals (since the door gallery's six tanks, 2026-10-08): 6 sharks, 3 mantas, 492 chromis, 218
  sergeants, 176 fusiliers, 156 Banggai cardinals, 109 yellow and 71 blue tangs, 78 clownfish, 33 mandarins, 32 Moorish
  idols, 19 copperbands, 18 puffers, 15 regal angels and 13 lionfish.
- `hc1_fauna_check [seconds]` (in play mode: it reads `Game.ActiveScene`) runs every tank that long at once and logs:
  how far any body comes into glass or rock, how often two bodies overlap (and which kinds), fish stuck outside their
  hovers, and each species' mean speed against its cruise.
- Checked with `hc1_fauna_check 20` in play mode on 2026-10-02 (68 tanks, 1363 animals, about 545,000 fish-steps a run):
  - No body came more than 0.010 into glass or rock (none of the steps over 0.05).
  - 60-120 fish-steps a run had two bodies overlapping by over 0.05 (about 0.02%), at most 0.35 deep, all in the dense
    chromis, sergeant and fusilier schools.
  - 0-1 fish stuck (`Check` counts one that swam under 15% of its cruise outside its hovers): a slow puffer.
  - Mean speeds near cruise: chromis 4.2 (cruise 4.3), fusiliers 12.4 (13.6), mantas 21-26 (30.3), sharks 28-29
    (42.7: they slow in their wide turns), Banggai cardinals 1.0 (1.4), mandarins 0.7 (1.0).
  - Every tank's step together took 1.24 ms, all of them close up and none skipped. In play only the near tanks run every
    frame.
  - The check needs a scene whose tanks are the current ones. With two editors open on the project (both answer the
    bridge, in turn), one kept a stale scene resource with the old 45 tanks that `load_scene` and `recompile_asset` didn't
    refresh. Loading a copy of the scene under another name did.
- `hc1_reefhall_views` / `hc1_reefhall_shot` make their camera the scene's main camera while they render, since
  TankFauna culls the small fish and slows the far tanks by the distance from `Scene.Camera`. The renders on 2026-10-02
  showed the lionfish by its rock, a chromis school, fusiliers and a tang in a lobby tank, and the sharks and a manta
  in the control room's panorama.
- Checked in the editor on 2026-10-02:
  - The navmesh is baked (`reefhall_scene_data/navmesh/baked.navdata`). `get_navmesh_path` reaches all 88 spawn,
    objective and cash spots from both team spawns, and every level: the Rotunda's, lobby's and control room's
    balconies, the office, the Filter Hall's catwalk and mezzanine, the tunnel's aisle and the upper galleries.
  - A TDM with 9-10 bots of every play style: they fought across the map, and the frame took 9.65 ms (p50).
  - Renders of every view against the references, in and out of play mode.
- The menu picture (`ui/maps/reefhall.png`) is an editor capture of the Rotunda from its balcony
  (`hc1_reefhall_shot art 700 -300 272 -300 300 260 90`).
- Not yet checked: the fish seen by a player in a match (swimming, the schools' turns, the shader's tail beat), sightlines
  with players, and the cost of the 394 lights and the tanks' ~1.1 million triangles on a slower machine.

