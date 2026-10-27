## Cerro Blanco (multiplayer map, `Tools/cerroblanco_map.py`)
- The user asked for a map as close as possible to MWII's Valderas Museum in looks and layout, under another name
  (2026-10-07). They sent four pictures: the courtyard with its round boulder planter and the stage with a piano, the
  South Gallery's portico with its red sculptures, an overhead of the courtyard (banners, hedges) and the South Gallery
  close up. Cerro Blanco is the Museo Cerro Blanco, a made-up art museum on a white hill over a Mexican town. Its text is
  made-up Spanish, with no Call of Duty name or marking.
- Built by script like Belltower, Railhead and Lowtide (`map_kit`), from three scripts:
  - `cerroblanco_materials.py` draws the museum's own materials with numpy into `Assets/materials/cerroblanco/`.
    Its docstring has each one:
    - cleft-cut travertine walls and honed, filled cross-cut travertine paving, on a 30-inch module;
    - off-white enamelled panels for the upper floors;
    - four exhibition banners with abstract pictures;
    - the museum's name in bronze letters, and the South Gallery's name in grey ones.
    Run it before the map script (`cerroblanco_materials.py [name ...]` redraws only those). The open editor compiles
    each map as it lands and holds the next one's file, so its saves go through a temporary file and retry the rename
    for up to 10 s.
  - `cerroblanco_parts.py` has the pieces:
    - the walls, glazing, stairs, railings and curved walls;
    - the round boulder planter, the red sculptures and the bronze sphere (and the stage, `P.stage`, now unused);
    - benches, cafe tables under parasols, banners and the sign.
  - `cerroblanco_map.py` lays them out and writes:
    - the models, to `Assets/models/maps/cerroblanco/`: the buildings, the grounds, the dressing, the glass, the
      canopies, and the backdrop (the hills and their trees, drawn only);
    - the scene, `Assets/scenes/maps/CerroBlanco/cerroblanco.scene`, rewritten whole on every run (change the layout in
      the script, not in the editor);
    - the flat paints and `cb_glass` (text-only vmats);
    - the radar picture, `ui/minimaps/minimap_cerroblanco.png`;
    - with `--art`, a stand-in menu picture, `ui/maps/cerroblanco.png` (a flat-coloured preview: replace it with an
      in-engine capture).
  - `--preview <dir>` and `--views <dir>` write flat-shaded views (`VIEWS`) for comparing with the pictures.
    Trees aren't drawn in them.
- The museum stands round its courtyard: travertine below and warm off-white panels above (grey joints), with flat roofs
  and parapets.
  - The rotunda is the entrance hall, two drums in the white panels, as in the pictures:
    - The lower drum (to `ROT_TOP`, 352) has a 3 x 3 gridded window towards the courtyard (`ROT_WIN`, 186-320) over a
      band of panels, with the ground floor glazed under it, and a second window to the west.
    - A smaller drum is set back on its roof (`ROT_UP`: radius 290, about three quarters of the lower's, up to 540).
      Its walls are 26 deep (`ROT_UP_WALL`), and its twelve 1.5:1 windows (`ROT_UP_WIN`, 424-488) are set into them,
      so their reveals show. It has a glazed lantern on top. The roofs round it are a pale membrane (`P.ROOF`,
      `cb_roof`).
  - The cafe's upper room (the GLASS ROOM callout, `cafe_upper`) is over its south half, the block behind where the
    pictures' stage is, at the galleries' height, as in the pictures:
    - Over the courtyard, a curtain wall of 11 x 6 milky, pale green-white panes (`CAFE_GRID`, `P.FRIT`, `cb_glass_frit`)
      in white mullions. The frit is glass.shader's rough glass (roughness 0.45, AlbedoAbsorption 0.9), so ~40% of its
      colour is lit and the rest is the room blurred through. Plain `cb_glass` there read black.
    - A skylight with a white curb and bars (`CAFE_SKYLIGHT`), a roof unit with a fan, two plinths and a picture
      inside, and a door and a window from the terrace.
    - The terrace is the cafe's roof north of it (`CAFE_UP`, 340), still up the stair from the courtyard.
    - The pictures' large 2 x 2 window at that block's north end is left out.
  - The West Gallery (two storeys, an L, a stair inside) is on the courtyard's west side. Its east front has the
    pictures' curved balcony (`west_balcony`): a slab along the first floor with a rounded south-east corner, a steel
    rail, slim columns and a canopy, with five banners hanging from it (`BALCONY_BANNERS`). On the courtyard's east side
    are the cafe (its roof a terrace, up a stair from the courtyard), the North Gallery (two storeys) and the East Hall,
    with its mezzanine.
  - The South Gallery (one tall storey) closes the courtyard's south side. Its front is the pictures' (`south_front`):
    - an enclosed balcony box in white panels over the entrance, its south-west corner rounded, on fat round columns;
    - over it a flat white roof on slim columns, open in louvres at its east end;
    - "galería sur" in grey letters on the wall under the balcony (`P.lettering`, `cb_label_sur`, drawn by
      `cerroblanco_materials.labels`);
    - a travertine planter of shrubs against the glass west of the entrance.
    All of it but the columns and the planter is in the canopies' model, out of reach.
  - In front of it, on the south plaza, the two red sculptures: a tall curved spike with a fin on a travertine block
    (`spire_sculpture`, two bowed steel sheets) and box beams welded into a zigzag beside a post (`zigzag_sculpture`).
    A smaller zigzag stands in the east garden.
    - The spike's sheets are crescents in section. Their normals come from each ring's own tangent: from the ring's
      middle they pointed into the concave face, which then drew inside out (only its edges showed).
  - In the courtyard, which has no trees (they hid the rotunda, where the pictures' courtyard is open):
    - the round two-tier planter with its boulders, seven low plants round its rim and a rounded beech shrub on top;
    - the hedges, benches and the cafe's tables.
    - The pictures' stage along the cafe's west wall, with its grand piano, speakers and cases, came out on 2026-10-09
      at the user's ask ("remove the piano area"). `P.stage` is still in the parts script, unused. The STAGE callout
      went with it.
  - The backdrop is the hills and their trees. The low-poly town on the slopes below (170 boxes with tiled roofs) came
    out on 2026-10-09 too, at the user's ask ("the low poly buildings").
  - The hedges (`P.hedge_box`) are Facepunch's `beech_hedge_96x128` (its mesh is 48 x 141 x 90, `HEDGE_SIZE`), cut to
    length in a travertine trough with a honed coping, over a clipped core box that is their collision.
  - The stone's colours are within a few per cent of each other (`TRAVERTINE`, the honed stone's jitter), so from a
    distance the walls read as one even cream, as in the pictures, not a checkerboard. The panels are a warm off-white
    (212, 207, 198) and the sculptures signal red (`RED`).
  - The paving and the honed stone (2026-10-09). The user found the floor "too bright" and not good enough: a near-white
    cream (mean 225, 214, 193) that the sun blew out, blurry wood-like bands, a checkerboard from slab to slab, harsh
    dark grout, dark specks, and a repeat every 10 feet. Now they're honed, filled cross-cut travertine after years
    outdoors (`honed_face`):
    - A warm beige (`PAVING`, mean about 186, 174, 152: an albedo of ~0.45-0.5), whose beds show as soft clouds of
      ivory and walnut. Each slab is cut from its own part of the block (`strata`, `sample_strata`), turned any of the
      eight ways.
    - Small filled pores in a greyer cement, most in the porous beds, a few lost and open; a fine grain and sparkles of
      calcite; weathering, grime by the joints, a few spills and paths worn by feet.
    - 3/16-inch sanded grout a shade under the stone, eased and chipped arrises, and each slab a hair proud or out of
      level.
    - The paving tiles every 240 inches (8 x 8 slabs, 4096 px, `PAVE_TILE`, `PAVE_SIZE`; `P.TILED[PAVE]` 240), the same
      17 px an inch as the other stone.
    - Checked in the script's lit sheet and at full resolution, not in the engine: the editor was closed when it was
      written.
  - The materials script saves each picture through a temporary file and retries for 10 s
    (`cerroblanco_materials.save_image`), and the map script writes the radar and menu pictures through it.
  - The banners (`BANNERS`) read the right way round: `banner` swapped them for a viewer's left and right
    (fixed 2026-10-08).
- The sky is its own (`Tools/cerroblanco_sky.py`, on belltower_sky's code): cloudless and deep blue, as in the
  pictures, baked with the map's sun. `--width 2048 --supersample 1` is plenty for a gradient.
- The clear glass (`cb_glass`) is rw_glass with a museum's low-e tint (0.78, 0.84, 0.85): it passes ~80% of the light,
  a little cool, so the rooms behind it read darker than the sunlit outside and its reflections show.
  - What it reflects comes from the probes (`PROBES`): one per room and the courtyard (priority 1), and `GROUNDS_PROBE`
    over the whole play area (priority 0, reach 20000, far 60000), which gives the outside of every pane the sky, the
    hills and the town.
  - Without the grounds' probe, the panes outside every room's and the courtyard's box (the rotunda's front, the upper
    drum, the galleries' outer windows) had no probe and read flat grey. The courtyard's box runs to e 496, past the
    Glass Room's curtain wall (e 489), so those panes reflect the courtyard.
  - Checked offscreen in the editor on 2026-10-09, with the probes forced (`CreateTexture`, then `RenderCubemap`, by
    reflection), from the forecourt, the courtyard, the stage (since removed) and the South Gallery: the panes show the dark rooms and
    the sky, and the frit and the balustrades are unchanged.
- Offline renders (railhead_render through Blender's Cycles, with the scene's sky and the models'
  textures) were compared with the pictures on 2026-10-08: the courtyard and stage, the West Gallery's balcony and
  banners, and the South Gallery's front with its sculptures from the pictures' angle.
- Red Team spawns on the forecourt at the north, by the car park and the museum's sign. Blue Team spawns on the south
  plaza, past the portico.
  - The car park has no cars: the user had them taken out (2026-10-09). Its asphalt, bays, kerbs, island and trees
    stay. The eight cars, SUVs and van were railhead_props' (`R.use`), ~33,800 of the dressing's ~50,700 triangles.
    Without them the spot checks still pass. The editor recompiled the dressing; it hasn't been seen in-game.
- Three lanes:
  - West: the West Garden's lawns, the West Gallery, then the garden circle round its bronze sphere (bomb site B) and
    the south-west lawns.
  - Middle: the rotunda and the courtyard, then the South Gallery.
  - East: the promenade, the cafe and its terrace, the North Gallery, then the East Hall (bomb site A), the covered
    walkway and the east terrace.
- Modes:
  - The scene lists TDM and Defuse, and it's in `GameUtils`' three map lists.
  - It has deathmatch spawns (35, one in the Glass Room) and Retakes spawns for each site.
  - Domination's flags: A at the rotunda, B in the courtyard, C at the South Gallery.
  - Hot Zones and Cash Grab points are `ObjectiveSpot`s.
- Every run checks all 96 spots with railhead_map's `check_spots`, `check_reach` and `check_retakes_sight`. On
  2026-10-09 all three passed.
- The navmesh's bounds stop at `NAV_TOP` (300): over the first floors (180) and under the roofs (330-360). The glass and
  the canopies are tagged `navskip`.
- Made offline on 2026-10-08. On 2026-10-09 the editor compiled every model, material and the scene with no Cerro
  Blanco errors in its log, and the user played a match on it.
  - The scene was loaded offscreen in the editor (a `new Scene()`, its objects deserialised from the file, the game
    modes' prefabs left out): all 359 renderers loaded, none of them an error model.
  - Renders from there (a camera with the scene's tonemapping and bloom) were compared with the pictures: the overhead,
    the courtyard and stage, the West Gallery's balcony and the South Gallery's front. They led to the even stone, the
    courtyard without trees, the planter's plants and the brighter red.
  - The rotunda's drums and the Glass Room compiled on 2026-10-09 with no errors, and were compared offscreen with the
    pictures from the courtyard, the stage and overhead.
  - When a run adds a material, a model can compile before it ("Missing vmat"): `recompile_asset` the vmat, then the
    vmdls.
  - Played in the editor on 2026-10-09 (`dev_mode team_deathmatch cerroblanco`; starting play stalled the editor for
    about 5 minutes first):
    - The navmesh generated in play, with complete paths from Red Team's spawn to the Glass Room, the cafe's terrace
      and Blue Team's spawn.
    - 9-10 bots fought a TDM across it: 48 kills in the first 3 minutes.
    - The rotunda's drums and the museum's sign were seen from the forecourt, and the Glass Room from inside (its
      panels, the curtain wall with the sky through it, the plinth, the door to the terrace).
  - The modes' objects were checked on a navmesh generated offscreen in the editor on 2026-10-09 (the scene's colliders
    in a `new Scene()`, with the scene's agent, excluded tags and bounds):
    - All 81 spawns (team, deathmatch and Retakes), both bomb sites, the Domination flags, the six Hot Zones and the
      three cash and extraction points are on it, with complete paths from both team spawns.
    - 40 random navmesh points in each bomb site and buy zone: all reachable from both spawns, except a few in Blue
      Team's buy zone. Those are on top of the spire sculpture's travertine block (76 high, with a 4-high lip round it)
      and a bench (32), which only mantling reaches. Bots check their paths, as on the other maps.
    - The scene's mode objects match Belltower's: 2 bomb sites, 2 buy zones, 9 `ObjectiveSpot`s, 3 cash and 3
      extraction points, and the same `GameModeObject` filters.
  - Defuse was played in the editor on 2026-10-09 (`dev_mode bomb_defusal cerroblanco`, 5 v 5 with bots), through six
    rounds of about a minute each:
    - Both bomb sites were active (A in the East Hall, B at the garden circle). Red Team spawned on the forecourt with
      the C4.
    - The C4 was planted on site A by a bridge script. That was the player's own `DefuseC4`, deployed and started by
      reflection: `CanPlant` held, and the planted bomb spawned. The HUD showed DEVICE ARMED 0:40, team chat
      "Leon (A SITE) Planting bomb", and Blue Team's bots closed on it.
    - It went off at 0:00, and the next round started 5 s later.
    - Bots never defuse, on any map: `Code/GameLoop/Bots` has no defuse logic.
    - While the win banner was up, every hit threw a NullReferenceException in `DamageIndicator.OnHit`. MainHUD takes
      the indicator off for the banner, and `Current` still pointed at the deleted panel. Fixed the same day; the fix
      hasn't been seen in a match.
  - Not yet checked: a Retakes, Domination, Hot Zone or Cash Grab match played on it.
- Visual upgrade in progress (2026-10-15, `Sources/CerroBlanco/`):
  - `Tools/cerroblanco_quality_materials.py` and `cerroblanco_quality_geometry.py` stage their outputs under
    `output/cerroblanco/stage`. Import and apply with the native scripts in `Sources/CerroBlanco/editor`; copy these
    scripts into the current sbox-cli exchange directory before `run_csharp`. They require Cerro Blanco to own the
    editor window and play to be stopped.
  - The retained imagegen travertine source and courtyard target, with their prompts, are under
    `Sources/CerroBlanco/generated`. The material's relief/normal/roughness are artistic derivatives of that source,
    not measured scans. `cerroblanco_stone.shader` varies each slab's cut and orientation, fades close relief with
    distance, and attenuates its analytic bevel below a pixel to avoid dotted distant joints.
  - Three render-only detail models add sills, thresholds, coping, drains, stair nosings and gallery fixtures. The
    dressing renderer uses `quality-v1/cerroblanco_dressing_v2.vmdl`; its original collider stays. The corrected
    picture UVs show 22 individual artworks, and the hedge core is recessed under the leaf silhouettes.
  - The accepted first lighting pass has 28 gallery/soffit spotlights and a 34 x 27 x 6 indirect-light grid (5,508
    probes). Both native bake passes completed. Irradiance, distance and relocation textures are saved under
    `Assets/lighting/cerroblanco/daylight-v1/`; these compiled textures are explicitly tracked. Relocation is serial
    on the main thread, and Scene.Push scopes must never cross an await.
  - Eleven real room/courtyard static reflections are compiled, assigned and saved under
    `Assets/lighting/cerroblanco/daylight-v1/reflection_*.vtex_c` (512-square cubes, eight mips). Retain these ready-to-load
    copies and the panorama sources. Do not enable realtime probes or call EnvmapProbe.Bake/CubemapRendering.Filter
    on this driver. Captures reapply position, rotation, FOV 90 and square CustomSize before every render; the editor
    otherwise resets its camera between frames. AO is temporarily disabled during capture and restored afterward.
    ACES inverse/sky calibration has 0.055% channel disagreement and less than 0.1% clipped pixels on every face.
  - Native checks pass all 96 spawn/objective floor, clearance and connected-path checks, with no missing models or
    materials. The extraction checks subtract the intentional 32-inch trigger-center offset. Offline comparisons
    also confirm the six model collision descriptions and all 546 spawn/objective/collision components are unchanged.
    A local TDM test spawned the player and nine moving bots, with nav ready and the player camera selected. Three
    short 1920x1080, 8x MSAA samples ran at 77-88 FPS with no sample hitches; exterior draw counts reach 3,555 and
    remain a performance caveat. Samples are editor measurements, not a standalone benchmark. Shared Aimable and
    bot SpotScratch hotload errors appeared during the test; no Cerro asset errors or compile failures were reported.
    Play/network are stopped and `output/cerroblanco/test-state.json` records restored settings.
  - Twelve final native views are in `output/cerroblanco/final`; the courtyard is the saved menu preview. Exterior
    glass still needs its coated-glass comparison. `Tools/cerroblanco_quality_glass.py` stages a candidate under
    `output/cerroblanco/glass-stage`, retaining source under `Sources/CerroBlanco/glass-v1`; it is not published yet.
    The candidate applies the same adjustable dielectric reflectance to lighting, transmission and depth shading.
  - `Tools/cerroblanco_quality_state.py` exports the saved editor visual state into
    `Sources/CerroBlanco/quality-state.json`; the base map generator reapplies it so regeneration retains these
    materials, details and lighting. Export it again after accepting further editor changes. Its preservation check
    is idempotent and leaves the base collision/gameplay components unchanged.
- Fit-out, landscape and panels (2026-10-15, the user's "get blanco map AAA"), on top of the quality pass:
  - `Tools/cerroblanco_art.py` draws the shows into `materials/cerroblanco/fitout/` (about 4 minutes; `--only text
    signs letters` skips the paintings):
    - 16 made-up works: portraits for ROSTROS, seascapes for MAREAS, plateau landscapes for TIERRA ROJA, charcoal
      studies for FORMA Y VACÍO (a torso and a pierced reclining figure, under mats) and two colour fields. Each is
      flat shapes painted over with brush dabs that follow its edges, bristle streaks and a canvas weave; its normal
      and roughness come from the same strokes.
    - Each show's wall text in Spanish, the works' labels, the room plates, the wayfinding panels, the cafe's menu,
      the opening hours, the green SALIDA exit signs and the galleries' names for the façades.
    - `layout.json` there holds every rectangle on the sheets, for the fit-out's UVs.
  - `Tools/cerroblanco_fitout.py` dresses the rooms. `cerroblanco_map.build()` records the walls, stairs, plinths and
    pictures as it builds them (`Log.recording`), and the fit-out works from those:
    - It hangs works with frames and labels in the clear runs of the rooms' walls and down both sides of the
      freestanding display walls. Each gets a warm spot on the ceiling aimed at it (`Art Lights` in the scene, 72
      with the wall texts' own).
    - On the ceilings: lighting tracks with spot heads, diffusers, detectors and cameras. By the doors: exit signs
      over the ones out, room plates beside them. Each room also gets an extinguisher and a return grille.
    - Benches and vitrines, with collision, kept clear of every spot, stair, plinth and the map's own collision.
    - The lobby: banners hung in the rotunda, a mobile in its clerestory, queue stanchions, screens on the desk.
    - The cafe: the espresso machine, grinder, pastry case, pendant lights, menu board, and cups on the tables.
    - Outside:
      - wall lights by the doors, the façade lettering, and blinds behind half the upper windows;
      - wayfinding totems, agaves in pots and pole lights on the promenade (with collision);
      - cameras, downpipes and the roofs' plant;
      - bike stands and three flags on the forecourt.
    - The bike stands (`bike_stand`, 2026-10-25; the user saw seams at every bend) are Sheffield stands at their real
      size: one 48 mm stainless tube swept in a piece (`P.sweep`), 700 mm long and 800 mm tall with 150 mm bends,
      root-fixed into the paving, a metre apart in a row ending at e 1040. They were ten six-sided bars each, 18 wide.
      Base plates were tried: the paving's relief (`cerroblanco_stone.shader`) buries anything within about 0.4 of
      the ground, so plates showed only as slivers. Drawn only, as before. Published by splicing just their faces into
      the installed `cerroblanco_fitout_fine.obj` (`output/cerroblanco/bike-stands-20261025/stage_stands.py`), and
      checked in offscreen editor renders there, not yet in a match.
    - Two models: `cerroblanco_fitout` (with collision) and `cerroblanco_fitout_fine` (drawn only).
    - The façade banners (`banners()`) are drawn in the fine model. The glass install (`cerroblanco_glass.install`)
      had rebuilt the buildings' model without them. The quality pass overrides the buildings' materials by slot, so
      a new paint in that model would shift every override.
  - `Tools/cerroblanco_landscape.py` replaces the backdrop:
    - It keeps the old lie and adds detail on it: rolling ground, gullies, limestone outcrops, ridges and the sierra.
    - It's a tensor grid 100 apart near the play. Every quad is one material, `cbf_land.vmat` on
      `cerroblanco_land.shader`, which height-blends the terrain's dry meadow, meadow, dirt and rock by a painted
      1024 splat (`land_splat.png`: R green, G dirt, B rock, A broad light and dark), so the ground has soft edges
      instead of a paint per quad. The splat's texels follow the grid's three zones (`map_axis`, the shader's MapAxis).
      Painting it adds ~25 s to a run; `--preview <dir>` writes it and its views.
    - The woods are `Tools/cerroblanco_trees.py`'s alpha-tested cards cut from Belltower's generated tree atlas
      (`forest-trees-v1.png`, three tints): ~6,000 trees and ~5,700 scrub, facing the play, in their own model, which
      casts no shadows (`Backdrop Woods`), plus 300 cloud oaks. The old crown loop still draws its random numbers
      (`BLOB_DRAWS`) into nothing, so the oaks stay where they were.
  - `Sources/CerroBlanco/shaders/cerroblanco_panel.shader` draws the enamelled panels (`quality-v1/cb_panel.vmat`,
    written by `cerroblanco_quality_materials.py`):
    - each panel a little tilted and pillowed, so a façade reflects the sky unevenly, as real panels do;
    - open joints box-filtered over the pixel's footprint (a fine tone from afar, not dotted lines), and faint rain
      streaks under some of them.
  - `cerroblanco_stone.shader` filters its joints the same way. The paving is warmer and darker (`0.93 0.91 0.86`),
    with ±7.5% between slabs and one slab in twelve from a denser bed (`g_flSlabVariation`, `g_flOddSlabs`).
  - The quality details' trims (`cerroblanco_quality_geometry.py`) are pale anodised (`cb_white`) or stone, at least
    1.5 tall: copings, sills, heads and the cladding trim were sub-inch black lines that dashed and outlined every
    roof. Thresholds are honed stone; the stair and threshold grooves are gone. The plinth and skirting follow the
    floors (`floored()`), so none crosses the cafe or a two-storey façade.
  - The forecourt's three flags hang from outrigger arms, facing north, with soft folds.
  - Lighting (2026-10-17, after a critique of the captures): the rooms' fills at half (their patches in
    `quality-state.json`), the indirect light at 1.1, the art spots 2.7x brighter and narrower (13/28), and the
    exposure's range up to 4.5 so interiors adapt (it was 3: in-game the galleries were grey and evenly lit).
  - How it's published:
    - `cerroblanco_map.py --stage <dir>` writes everything under a folder laid out as Assets.
    - `Tools/cerroblanco_publish.py` copies what differs into Assets, with `--scene` for the scene. It leaves out the
      accepted glass and the unused base glass and dressing render models.
    - It lists what it copied, in compile order, for `Sources/CerroBlanco/editor/compile-v2.cs.txt`.
    - `capture-isolated.cs.txt` renders `output/cerroblanco/captures-v2/config.json`'s views into the config's
      `folder`. It uses an isolated scene, so the open scene is untouched. The probes keep their saved textures, and
      it updates the indirect light by hand.
    - `navmesh-check-v2.cs.txt` paths both teams' first spawns to every spot in an isolated scene.
    - `Tools/cerroblanco_compare.py <before> <after>` makes side-by-side sheets.
  - Every run of the map script passes all 96 spots, the reach check and the Retakes sight check with the fit-out's
    collision in.
  - Another session reworked the hedges and bollards in place (the dressing_v2 OBJ, hedge fill objects in the
    scene). Before a scene publish, run `cerroblanco_quality_state.py` so the staged scene keeps them, and diff the
    staged scene against the saved one; the stage's `cb_panel.vmat` and panel shader must match Assets' newer ones.
  - Status (2026-10-17): published and compiled with no failures; every model loads with valid materials. Isolated
    captures (`captures-v2/after-v3`, `after-v4`) were reviewed, and the navmesh check passed 98 of 98 paths. Captures
    pin exposure (4 outdoors, 5 indoors), above the game's; nothing of this pass has been seen in a match yet. The
    critique's other findings are still open: doorways' black reveals, the art's look, sparse rooms and roofs, the
    indirect light not covering the spawns or site B, the sierra's colour, and the perimeter wall.
- Tree pits (2026-10-25, the user's screenshot of a black square under a tree). `cerroblanco_parts.tree` drew each
  paved tree's "steel grate" as a flat `cb_black` 60-inch square, while the medium oak's trunk flare is 79 across where
  it meets the paving (`TRUNK_FLARE`, cut from the models' triangles in the editor), so the roots spilled over it.
  - Now `tree_pit`: soil (`soil`, 0.4 over the paving) inside a 4-wide honed travertine kerb 1.0 over it, its inside a
    foot clear of the flare, rounded up to 6: 108 square for the full-size medium oaks, 96 at scale 0.9, 60 for the
    small oaks. No collision (a 1-inch step). All 20 paved trees have one, with nothing else within 5 feet of them.
  - Published by `Tools/cerroblanco_tree_pits.py`, a splice of `quality-v1/cerroblanco_dressing_v2.obj` only, as the
    bollards' was: it removes exactly the 20 old squares and appends the pits; the vmdl (which already remaps `soil`
    and `cb_honed`) and both colliders are unchanged. The base dressing OBJ, which only collides, still has the
    squares. Checked in isolated-scene renders (`output/cerroblanco/tree-pits/after/`), not yet in a match.
- The garden circle's lawns (bomb site B, `cerroblanco_map.lawn_quarter`, 2026-10-24): each quarter's grass runs up to
  the two cross paths, its straight sides parallel to them, in a honed kerb (8 wide, 3 high) on all four sides. They
  were annulus sectors with radial sides, so a wedge of gravel, widening outwards and with no kerb, lay between each
  lawn and its path (the user: "the grass shouldnt stop where it is"). The gravel is now only the walk round under the
  hedge (474-540). Drawn only, like the old lawns. `Tools/cerroblanco_stage_garden_lawns.py` swapped just those
  triangles in the installed `cerroblanco_grounds.obj` (it finds the old lawns by vertex and refuses if any are
  missing); its materials and slots are unchanged. Checked in isolated-scene captures
  (`output/cerroblanco/garden-lawns/{before,after}/`), not yet in a match.
- The bronze spheres (2026-10-24, the user's screenshot: "this looks bad"): the garden circle's (r 58) and the South
  Gallery's (r 40) were near black and faceted. `cb_bronze` was a flat paint at metalness 0.9 tinted (92, 66, 40): as a
  metal its colour is its reflectance, about a tenth, so it mirrored the garden dimly and had no lit side, and the
  sphere was 24 x 12.
  - `Tools/cerroblanco_bronze.py` makes it patinated outdoor bronze: a tiling 2048 x 1024 texture set (umber to tobacco
    browns, soft grey-green run-off down it, a few rubbed spots; metalness 0.55 in the patina, 0.92 where worn,
    roughness ~0.44) on complex.shader with `F_METALNESS_TEXTURE`, and `sphere()`, 64 x 32 with UVs once round and once
    pole to pole. `bronze_sphere` calls it, and `cerroblanco_map.write_materials` writes the material through it
    (`CB_PAINTED`'s BRONZE entry is only the previews' colour). The busts use the same material.
  - Published by `output/cerroblanco/bronze-sphere/stage_bronze_sphere.py`, which swapped just the spheres' faces in the
    installed `quality-v1/cerroblanco_dressing_v2.obj` (1056 out, 7936 in) and refuses a file changed since staging.
    The hulls are unchanged. Checked in isolated captures (`output/cerroblanco/bronze-sphere/{before,after2}/`), not yet
    in a match.
- Ground-floor windows under an upper floor end at `GROUND_HEAD` (150), under the slab (2026-10-25, the user's
  screenshot: "this looks a bit mad"). Twelve of them (the West and North Galleries', and the East Hall's beside its
  mezzanine) took `glass()`'s default head of 190, over the first floor's top (180), so a 10" strip of glass, with the
  ground outside seen through it, ran along the foot of the upper rooms' walls. Give a new one there `z1=GROUND_HEAD`.
  - The fit-out took each strip for a door out of the upper room and hung an exit sign over it. A wall face lists every
    opening up the wall, so every ground-floor door and window also got a sign and a room plate from the room over it:
    stray signs at 159 over the 150-high windows, one over the cafe's inside door to the North Gallery, and a second sign
    on each ground-floor door out. `door_fittings` now takes only openings that start at the room's floor: 30 exit signs
    and 34 plates, from 57 and 51.
  - Published by `Tools/cerroblanco_stage_window_heads.py` and `Sources/CerroBlanco/editor/import-window-heads.cs.txt`:
    the buildings model (and its collision boxes), the three detail models, two new pane models and the scene's
    Breakable Glass group (359 panes from 392; the panes renumber, so their ids shift) from a fresh build, each checked
    to be the old build's before; the stray signs and plates taken out of the installed `cerroblanco_fitout_fine.obj`,
    every other line kept. The import puts the same glass group into an open, unchanged Cerro Blanco document. Its
    panes asked for the two new models before they had compiled and got error models until those were compiled again.
  - Checked in isolated renders (`output/cerroblanco/glass-strip/after/`): the upper walls meet the floor along an
    unbroken skirting, the façades' ground windows end under a stone band like their neighbours. Not yet in a match.
- To play it: `dev_mode team_deathmatch cerroblanco` (or `dev_mode bomb_defusal cerroblanco`).

