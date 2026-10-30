## Riverdale (multiplayer map, `Tools/riverdale_map.py`)
- The user asked for a new AAA nuclear reactor map "as close as possible" to two reference pictures (2026-10-14): a
  reactor hall round a glowing cyan fuel pool (crane with "RIVERDALE NUCLEAR" and "SWL 125 T", mast in the pool,
  glass control room upper left with a stair, B1/B2 blocks, slogans and the logo on the far wall, water purification
  tanks, cases with the logo), and a wet plant yard at sunrise (A1 with "> REACTOR HALL", B1 with a stair up to a
  double door, the UNIT 1 containment dome, two cooling towers, a red container "02", barriers, a forklift, pipes,
  snowy mountains and pines). Riverdale Nuclear, its "A" logo (a triangle with an orbit swoosh, drawn by
  `riverdale_materials.logo`) and every marking are the map's own.
- Scripts, run in this order:
  - `Tools/riverdale_materials.py`: the rv_ materials in `Assets/materials/riverdale/` (numpy, Boxyard's helpers):
    formwork concrete, the hall floor, the wet yard with puddles, grating, yellow and grey steel, pipe jacketing, the
    pool liner, glowing fuel racks, hazard stripes, cases, and three atlases: lettering (`LETTERS`, white on alpha,
    tinted by `rv_letters_dark` / `_light`), signs (`PLATES`: the caution sign, UNIT banners, placards) and the control
    room's screens (`SCREENS`, self-lit). `rv_pool_water` is Reef Hall's `hc1_tank_glass.shader` looking down.
  - `Tools/riverdale_sky.py`: a golden morning on belltower_sky's code, the sun 16 degrees up 33 degrees north of east
    (riverdale_map's SUN_PITCH, SUN_YAW), warm at the horizon, more cumulus near the sun. ~2 min.
  - `Tools/riverdale_map.py [--preview <dir>] [--views ...] [--no-scene] [--no-models] [--art]`: everything else, with
    `riverdale_parts.py` (pipes with bends, railings that add player clips, stairs on one wedge hull, tanks, jersey
    barriers, cases, atlas quads, lamps that add point lights), `riverdale_hall.py` (the hall) and
    `riverdale_backdrop.py` (domes, towers, terrain, pines, the tower crane, outer blocks; drawn only). The scene is
    rewritten whole on every run.
- Layout (plan e, n, z inches; mirrored across e 0; play e -2300..2300, n -1750..2450): Red spawns west, Blue east.
  - The hall (e -1000..1000, n -200..2000, roof 1000): deeper than wide so its south end frames the reference. Pool R
    520 round (0, 900), water at -30, liner to -520, racks and a lit mast in it; railing round it clipped to the roof.
    Upper level at 288: a control room on each side wall (n 660..1200, glass on its pool and south sides) on columns,
    a stair from the south deck (n 160..580) to a landing, walkways along the side and north walls, the B1/B2 blocks
    (n 1300..1640) flush with it. Crane girders at n 840/960, z 836. Doors: west/east (annexes), south (yard apron),
    two north (lane). Tanks south-east, logo cases south-west.
  - Annexes on the hall's sides: A1 east (the reference's), A2 west, south faces with the sign, louvre, hazard jambs.
  - Yard: C1 in the middle (core with an upper room, wings and stairs both sides, a pipe bridge to the hall), the
    turbine annex south of it with generators either side breaking the south lane's sightline, a turbine block with
    its sign on each yard's south edge, containers (east red 02, west blue 04), barriers, the forklift
    (`lowtide_forklift`), cases, light masts.
  - Spawn buildings B1 (east) / B2 (west): a stencilled wing, a stair up to a double door into an upper room, against
    the boundary building. The hero yard view is from C1's east stair looking east (VIEWS "yard_reference").
  - North lane between the hall and the perimeter wall, under a pipe rack; courts north of the annexes.
  - Sites: A on the hall's east deck under the east control room, B in the east yard round the red container.
- Backdrop (`riverdale_backdrop.py`): UNIT 1 dome at (4400, -1150) and UNIT 2 at (-4400, -1150), over each yard's far
  end and clear of the B1/B2 spawn building, with the logo, name, red banner (17 degrees round from the logo) and
  beacons on the face towards their yard, vent stacks, auxiliary blocks and pipe bridges; cooling towers at
  (±10300, 4160) and (±14240, 2150), placed so the east yard's view finds them over A1; a heightfield ring of forested
  hills and snowy massifs (the ridge field blurred round the ring, snow painted per quad: per triangle it made rows of
  white teeth); 2600 pines from 6000 out (nearer, they stood over the roofline as black spikes). Domes and towers cast
  no shadows (the low sun would put the yards in their shade).
  - Its gravel ground is a ring round the play area (whose own ground runs 400 past its edges). It used to be one slab
    over the whole map at z -30..-24, which capped the fuel pool (water at -30): from the deck the pool read as an
    opaque teal sheet, the cyan lamps lighting the slab's top.
- The look (`look_object`, `HAZE`): AO, a warm grade, a vignette, bloom (0.32 over 1.15), screen-space reflections and
  ACES with auto exposure 1-2.5; volumetric haze in the hall (0.35) and a light one over the yards (0.06).
- The pool's light (2026-10-15, the user in a match: "riverdale pool lighting is mad bright"). It read as a white
  sheet with glare blobs round its rim. Now:
  - water scatter 0.03/0.32/0.46 and deep 0.006/0.10/0.20, shafts 0.35, caustics 0.9 (were 0.1/0.95/1.35,
    0.02/0.3/0.55, 0.7 and 1.4). The shafts add up to 2.1 times the scatter, so they were most of the white;
    the scatter was already down from 2.9 blue;
  - the 24 lamp strips at the waterline (`rv_lamp_cyan`) glow 3 (was 14: those were the blobs), the racks 2.5 (8),
    the mast's core (`rv_cyan_glow`) 2 (6);
  - the 8 pool lamps under the water 0.10,0.42,0.52 and the 6 glow lights over it 0.05,0.27,0.38, about half, as they
    light the haze over the water.
  - Checked in the offscreen captures (`pool_close`, `hall_reference`): deep teal water with the racks and mast seen
    through it. Not yet seen in a match: the materials recompiled into the user's running one, the lights only come
    with the next load of the map.
- Checks (`check_spots`, `check_reach`, `check_retakes_sight`) pass for all 95 spots.
- `Sources/Riverdale/editor/` (run each with the native MCP's run_csharp, `{"path": ...}`):
  - `compile-stale.cs.txt` force-compiles every riverdale material, model and the scene whose sources are newer than
    their compiled files. The file watcher misses some of a run's rewrites (the backdrop's 35 MB OBJ, the flat paints),
    and `CompileIfNeeded` doesn't look at a model's OBJs.
  - `capture.cs.txt` renders the views offscreen into `output/riverdale/captures/` without touching the open scene,
    as `config.json` there says (`views`, `width`, `height`, `settle_frames`, `stream_frames`, and `hide`: objects
    to leave out by name). It marks every texture used at full size and waits ~3 s first: straight after loading the
    lettering sampled low mips and read as black blobs. A capture that overlaps an asset reload can show a green sky;
    run it again. Long captures (1920x1080, several views) can outlast the CLI's timeout.
- The menus' picture, `ui/maps/riverdale.png`, is the capture's `map_art_hall` view (1920x1080): the hall from the
  south deck, the crane, the far wall and the glowing pool. `--art` would overwrite it with the old flat-shaded stand-in.
- Checked in those renders on 2026-10-14 against the references: the hall (crane lettering, the logo and slogans in
  the bays between the far wall's pilasters, the glowing pool with its racks), both yards (A1/A2, the domes' faces,
  TURBINE BUILDING, the containers), the control rooms, the north lane, the court and the aerial. Not yet played: no
  match, bots, navmesh or modes have run on it.
- The AAA pass (2026-10-16 and 17, the user: "get riverdale AAA with a workflow"). A first round's agents wrote
  `riverdale_facades.py` (the yard buildings' faces), `riverdale_yard.py` (ground detail and clutter, drawn only) and
  `Sources/Riverdale/lighting/` (its README has the bake). An overnight pass whose session isn't on record then published
  it all and added:
  - the baked light, revision `daylight-v1`: three indirect volumes (yard, hall, pool) and twelve static reflection
    cubes, kept in `Sources/Riverdale/lighting/*.json` for regeneration (`.gitignore` lets their `.vtex_c` in);
  - box colliders for the big pipes and the yard props ("Pipe Solids", "Yard Prop Solids": `riverdale_parts.PIPE_SOLIDS`,
    `riverdale_collision_scene.py`, `riverdale_merge_collision.py`);
  - `RiverdaleGratingStabilizer` (`Code/Map/`): an opaque, mip-filtered grating in place of the shimmering alpha-tested
    one (`riverdale_grating_stable.py`);
  - cooling-tower vapor (`riverdale_vapor.py`). Its report says gameplay routes from both spawns reach both sites.
  - The backdrop's trees split into 16 render-only sectors (`riverdale_spatial_verify.py`): the sector models are in
    `models/maps/riverdale_sectors/`, but the saved scene still draws the unsplit tree models.
- Round 2 (2026-10-17), from fresh offscreen captures:
  - The hall's walls were blotched light and dark: the hall volume's probes are ~10 ft apart on 80 ft walls. Rendering
    with the fog, then the indirect light hidden showed it was the light, not the haze. The hall volume's NormalBias
    70, ViewBias 100 and RuntimeIntensity 2.1 (were 20, 30 and 1.8) smooth it with no re-bake, and keep the floors
    neutral (at 90/120 a red lamp tinted the walkway pink). Set in the saved scene and `indirect.json`.
  - The turbine buildings' three steam lines left the wall 28 in out, so each elbow met the next and every line read as
    a closed loop. They now leave at one height as a bank 46 in out, on a channel bracketed off the wall with clamp
    bands (`yard_side`), and their colliders moved with them. The jacketing (`jacketing`) is duller: roughness 0.54
    (was 0.38), softer oxidation and grime. It read as chrome.
  - The court's transformer (`transformer`): a lid flange, skids and stiffeners, two banks of 14 panel radiators a side
    on headers, three shedded HV and four LV porcelain bushings (`rv_porcelain`), an oil bund with gravel. Plinth and
    tank collision unchanged.
  - The control rooms' back walls on the upper walkway (`riverdale_hall.control_back`): a supply duct, a cable tray, a
    distribution board, a notice board, an extinguisher, the door's frame and plate, a camera.
  - The blurry console buttons in captures are the capture's 1024 texture cap, not the atlas.
- How to change it now:
  - `riverdale_map.py` builds on Railhead's prop and container code (`railhead_props`, `lowtide_container`, ...), which
    other sessions change. So a fresh build differs from the published yards in places nobody meant to touch (on
    2026-10-17, ~13k triangles of `rw_steel_dark`). Don't publish a whole rebuild over them. `Tools/riverdale_splice.py`
    takes the change as the difference between two builds (without and with it, `--baseline` / `--current`) and
    applies just that to the published OBJs, refusing if any face it removes isn't there.
    `Tools/riverdale_build_models.py` builds the models with the backdrop stubbed out (~5 min), from a source
    dir ahead of Tools for the baseline. It imports that dir's modules first: `riverdale_materials` puts Tools back at
    the front of `sys.path`.
  - `Tools/riverdale_merge_pipe_solids.py` carries a staged scene's "Pipe Solids" into the saved scene and checks that
    nothing else changes. The saved scene round-trips through `json.dumps( indent=2 )` byte for byte (CRLF kept).
  - `Sources/Riverdale/editor/editor_call.py` is a short native connection (`--direct-call --script <cs.txt>`).
    `capture.cs.txt` takes `"set": [{ "object", "property", "value" }]` to try a component's value on its copy.
- To play it: `dev_mode team_deathmatch riverdale`.

