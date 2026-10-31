## Ares (multiplayer map, `Tools/ares_map.py`)
- Pipe end closures (2026-10-27): all 16 wall-service runs now have smooth dished heads, closing the 32 missing
  end faces. `ares_pipework.pipe_run` includes them in future generation. The installed repair appends only
  17,472 head triangles to the active base OBJ, retaining every prior byte and the complete ModelDoc/physics.
  See `Sources/Ares/pipe-end-fix/README.md` and `installed.json` for native captures and verification.
- Formed pressure doors (2026-10-26): `Tools/ares_airlock.py` now exports `ares_pressure_formed.pressure_door`,
  following `Sources/Ares/pressure-doors-v3/concept-v1.png`. All three hatches have true recessed pressings and
  service pulls, rolled/chipped edges, cast spindle clamps, a seated gasket, recessed wheel and new private PBR maps.
  The hall uses the unchanged v2 base import plus the three v3 door imports; its complete physics suffix is preserved.
  See `Sources/Ares/pressure-doors-v3/README.md` and `installed.json` for scope, validation and guarded import details.
- Pressure-door rebuild (2026-10-20): `Tools/ares_airlock.py` replaces the six-box wing/cargo hatches with chamfered
  pressure frames, rubber seals, two recessed coated-metal leaves, six locking dogs, hex pivots, kick plates, a
  three-spoke release wheel, inspection port and pressure/control display. Warning stripes are confined to the
  threshold. The wheel is at z 58 and controls at z 39..80, providing human scale within the large cargo-size doors.
  - `wing()` and `concourse()` call `pressure_door()`; all three assemblies remain inside their original collision
    envelopes. Existing `ar_ext_*`, `ar_rubber`, `ar_rover_white` and screen materials are reused without changing
    any material source. Painted light hardware keeps the wheel and clamps readable in the dim rooms.
  - `Tools/ares_airlock_refresh.py` removes only the 216 old hatch triangles and appends 3,954 new triangles to the
    installed hall OBJ, preserving all previous stair/console edits. It adds eight existing-material aliases to the
    hall's MTL/ModelDoc remaps and leaves the complete physics definition unchanged. The hall is now 27,654 triangles.
    Reproduce the migration from `--source-root output/ares/airlocks-20261020/before`, not the installed new hatches.
  - `Sources/Ares/airlocks/import.cs.txt` publishes only the hall OBJ/MTL/VMDL through the editor, followed by native
    VMDL compilation. `output/ares/airlocks-20261020/` contains backups, scope hashes, staged sources and native
    captures of both wings, the cargo door and an angled view. This is a visual rebuild of the existing sealed doors;
    the scene, collision, lights and active editor/play state are preserved by the workflow.
- Stair surface fix (2026-10-20): all four 28-step flights had yellow nosing fronts coplanar with the steel tread
  fronts, and yellow ends on the stringers. These different materials fought for the same pixels as the camera
  moved. `stair()` now omits the hidden steel front and yellow end/bottom faces. The grating stops two inches
  behind the front edge, where the nosing ends; the nosing meets the riser at top-1.5 and finishes at top+0.125.
  - `Tools/ares_stair_refresh.py` stages those edits in the installed hall OBJ, preserving earlier console UVs,
    all unrelated geometry and every collision source. It is a migration of the original stair geometry; reproduce
    from `--source-root output/ares/stairs-20261020/before`, not from the already repaired installed mesh.
  - Import via `Sources/Ares/stairs/import.cs.txt` in the CLI exchange directory, then compile `ares_hall.vmdl`.
    This only refreshes a model asset and does not switch scenes or change play state. After this pass the hall was 23,916
    triangles (896 hidden/conflicting triangles removed). Materials, stair ramps, scene and gameplay are unchanged.
  - `output/ares/stairs-20261020/` holds backups, source hashes, geometry counts and native moving-camera captures
    for the hall and wing stairs. An independent planar-face audit found 672 overlapping quad pairs between
    hazard and steel/grating within the flights before the repair, and zero afterward.
  - The rear closures z-fought the same stairs' walls at their corners until 2026-10-30, when their coincident end caps
    were removed: `Sources/Ares/stair-rear-wall/README.md`. `Sources/Ares/audit_overlaps.py` lists faces that nearly coincide.
- Animated processing core (2026-10-20): `ar_plasma.vmat` uses `shaders/hc1_ares_plasma.shader`. The existing
  turbulence texture moves upward and around the column through a gently curling field, with broad dark amber
  pockets and brighter moving detail. The two noise layers and curl wrap at the mesh's U=0/2 cylindrical seam.
  - `ares_materials.plasma_vmat()` preserves the settings: brightness 1.8, rise 0.018, swirl 0.008, flow height 180,
    warp 0.055, dark areas 0.85 and pulse 0.03. The pulse combines two slow periods and stays within +/-3 percent.
    It runs in the GPU material using engine time, in both editor and play; no game component or network update.
  - `Sources/Ares/plasma/` holds the staged shader, guarded two-asset import and isolated native capture scripts.
    Import compiles the shader before replacing the material, then compile `ar_plasma.vmat` with the native tool.
    The plasma textures, core geometry, glass, collision, scene and actual lights are unchanged. The generator
    still writes the original turbulence textures, so material regeneration retains the animated shader.
  - Captures and source preservation hashes are in `output/ares/plasma-20261020/`. Motion previews can constrain
    exposure on their isolated scene copy; that comparison setting is never written to the map. The user's active
    editor scene is never switched by the capture helper; its isolated scene is destroyed in `finally`.
- Control displays (2026-10-20): eight built-in ImageGen panels replace the placeholder bars/noise. The original
  atlas, full prompt and provenance are in `Sources/Ares/screens/`. `ares_materials.py ar_screens` resamples that
  source into the existing 2048x1024, four-column/two-row atlas; it must not redraw the old placeholders. Screens
  use roughness 0.65, no specular and self-illumination 0.75 to keep the schematics readable.
  - Corrected the eight sloped consoles' mirrored UVs. Four pump readers now use the coolant tile on their fronts
    and steel on the edges. Both Red Planet signs are centred at z 163: the picture spans 135..191, above the
    monitors' top at 130; its backing stops at 191.5 below the gallery underside at 192.
  - `Tools/ares_screen_refresh.py` stages only those OBJ vertex/UV/material edits. It is a one-time migration;
    reproduce from `--source-root output/ares/screens-20261020/before`, not the already migrated installed meshes.
    Import with `Sources/Ares/screens/import.cs.txt` in the CLI exchange directory, then compile the screen material
    and three models. Backups, geometry counts, preservation hashes and native captures are in
    `output/ares/screens-20261020/`. Both control rooms were checked in the engine. Scene and collision are unchanged.
- Exterior colony rebuild (2026-10-19): `Tools/ares_outpost.py`, called by `ares_map.backdrop()`, replaces the
  luminous dome atlases, window-grid spires and plain blocks outside the play area. Habitats now have matte
  insulated shells, geometric ribs, dark observation windows, human-sized airlocks and supported pressure links.
  The atmosphere processors are shorter pressure-vessel skids with access decks, ladders, manifolds and instrument
  masts; service buildings have folded shoulders, rooftop exchangers and piping. Radiator banks and small shielded
  route markers complete the exterior. Signs use an upright, independently mapped atlas.
  - `python Tools/ares_materials.py outpost` generates eight private `ar_ext_*` materials. It does not redraw the
    facility's shared paints. Rebuild the mesh with `ares_map.py --backdrop-only [staging-dir]`.
  - `Sources/Ares/editor/outpost-import.cs.txt` imports the staged sources through the editor. Backups, hashes,
    staged assets and captures are in `output/ares/outpost-20261019/`. The completed backdrop is 203,000 triangles,
    drawn only; the terrain's 107,576 and the boulders' 11,760 triangles retain identical positions, UVs and normals.
    Source hashes also check the scene, facility models and previous materials. No frame-time benchmark.
    Habitat, processor and observation-window views were checked in the engine with no new compile errors. An
    isolated capture with settled exposure refreshed `ui/maps/ares.png`; the user's scene, play state and camera
    were restored/preserved.
- Martian terrain pass (2026-10-19): the plain uses broad, low swales instead of metre-scale noise sampled below
  the mesh spacing. The cliff has a wider weathered shoulder, and the far range uses smooth bounded noise instead
  of folded noise that produced pointed peaks. Smaller, partly buried rocks replace the oversized boulders.
  - `ar_regolith` and `ar_rock` have muted ochre/taupe colours and gentler normals. `ar_terrain.vmat`, generated by
    `Tools/ares_materials.py ar_terrain`, uses `shaders/hc1_ares_land.shader` to blend them continuously by slope, with
    world-space dust and triplanar bedrock. Terrain triangles all use this material; whole-face rock/dust selection
    exposed the grid as hard zigzag borders. Boulders retain `ar_rock`.
  - `python Tools/ares_map.py --backdrop-only [staging-dir]` rebuilds just `ares_backdrop`, preserving the facility,
    scene and menu images. This terrain pass produced 133,646 triangles (107,576 terrain), before the colony rebuild
    above, drawn only. No frame-time measurement.
  - Native editor import/compile: `Sources/Ares/editor/terrain-import.cs.txt` (copy into the CLI exchange directory).
    Backups, staged assets, hash checks and before/after captures are in `output/ares/terrain-20261019/`.
    In the sampled plain (e -5000..5000, n 2700..7000, 80-unit samples), the 95th-percentile slope fell from 34.9 to
    3.9 degrees. Ground, window and cliff views were checked in the editor; assets compiled with no new errors.
    The Ares scene file and edit/play state were preserved.
- The user asked for a map on Mars "as close to this img as possible" (2026-10-14), from a reference picture of an
  atmosphere-processing plant:
  - the ATMOS PROCESSING column glowing orange through its glass, in a dark steel hall ringed with galleries;
  - a leaning window wall onto the red plain with habitat domes, spired towers and two moons;
  - the facility's posters and banners (ARES FACILITY, HUMANITY FURTHER, HABITAT B, RED PLANET REAL PROGRESS) and
    black hard cases stencilled MARS / BIGGER / CLEANER / BRIGHTER.
  It's indoors and pressurised, so it has the game's normal gravity (the user said so). Nothing in the scene changes
  gravity. ARES FACILITY and its red triangle mark are the picture's made-up company.
- Built by script like Boxyard, from three scripts (each docstring has the details):
  - `Tools/ares_materials.py`: the ar_ materials drawn with numpy into `Assets/materials/ares/`, its atlases (cases,
    signs, lit door signs, screens, plasma, domes) and flat paints. Run it first. `names` redraws only those.
  - `Tools/ares_sky.py`: a Martian evening (near black overhead, a rust haze at the horizon, stars, a sun with the
    blue halo of a Martian sunset). Written with belltower_sky's EXR writer and wrapping.
    - The moons are drawn far bigger than Phobos and Deimos really look (3 and 1.7 degrees across), as in the picture.
    - They sit low in the north-north-west, so from the menu picture's view they hang in the window's top right.
  - `Tools/ares_map.py`: the models (`ares_hall`, `ares_reactor`, `ares_dressing`, `ares_glass` and `ares_backdrop`;
    the last two are drawn only), the scene (`Assets/scenes/maps/Ares/ares.scene`, rewritten whole on every run) and
    the radar picture.
- Layout (plan e, n; mirrored across e 0; floors at z 0 and galleries at G 208):
  - The Atmos Hall, e -1100..1100 and n -720..720, 720 high. The column stands in its middle on a 16 high plinth.
    - A ring catwalk runs round the column at G, with a bridge from it to each side gallery.
    - Galleries run round all four sides. The north one, the observation deck, runs along the window and is bomb
      site A at its east end.
    - A stair in the void beside each side gallery, and a glass-fronted control room under each side gallery.
  - The window wall leans out 14 degrees (`LEAN`): mullions every 200, a glass collision slab, cheeks against the
    side walls. Outside, the land falls away from a cliff under the window.
  - The wings: SECTOR 03 in the west (Red Team spawns there) and HABITAT B in the east (Blue Team).
    - Each is double height, with an L of mezzanine along its north and inner walls and a stair up its outer wall.
    - Three doors lead into the hall: the floor's middle door, the side gallery's SECTOR 03 / HABITAT B door, and
      the north door onto the observation deck.
    - A blast screen inside each middle door stops a sightline from site A through the door into the spawn.
  - The cargo concourse runs along the whole south side (n -1400..-752, 320 high). Its middle is clear; the rover and
    its collision were removed on 2026-10-15. Bomb site B is the cargo bay at its east end.
- Lanes: north is the observation deck and the wings' north mezzanines; middle is the hall floor past the column, with
  the ring and bridges over it; south is the concourse.
- Modes: the scene lists TDM and Defuse. It has 32+4 deathmatch spawns and Retakes spawns per site. Domination is A in
  the west wing, B by the column and C in the east wing. Hot Zone and Cash Grab spots are `ObjectiveSpot`s.
  `GameUtils` lists it (menus, Quick Play, vote, Ranked).
- Every run checks all 93 spots, as Boxyard's checks do. All pass: room and floor, reach, and no Retakes pair in sight.
- Checked offscreen in the editor on 2026-10-14, in an isolated scene (the editor's own was left alone):
  - A navmesh generated with the scene's agent and bounds: 186 of 186 paths complete from both spawns to every spot.
    The only islands are roofs, case tops and points inside the column.
  - Traces: the column is solid at radius 170 at every height. The window, wing windows and control-room glass
    block. A railing's top rail blocks players, and you can shoot between its rails.
  - Renders: `Sources/Ares/editor/capture.cs.txt`, with views in `capture-config.json`, writes to `output/ares/`. Its
    `art` view writes the menu picture, `ui/maps/ares.png`, from `ares_map.ART_VIEW` on the south-east gallery,
    framed like the reference picture.
  - Offline, `railhead_render.py` renders it in Cycles with `SCENE` pointed at ares.scene (a scratch wrapper).
- Learned making it:
  - The editor's file watcher missed the new folders: assets reported "no source file". Register them with
    `Editor.AssetSystem.RegisterFile` in a run_csharp script, then compile vmats, then vmdls, then the scene.
  - OBJs rewritten while the editor was stalled compiled into a fresh `_c` identical to the old one (same hash), so
    renders showed the old mesh. Register the .obj and .mtl again with `RegisterFile`, then `Compile( true )` the vmdl,
    and compare the `_c`'s hash before and after.
  - A 768 px normal map failed to compile ("GenerateMips HemiOctIsoRoughness_RG_B"), and every model using its
    material failed with it. Keep normal maps a power of two.
  - The engine ignores a mesh with a point 90000 out ("ignoring mesh"), so the land stops 60000 out (`WORLD_EDGE`)
    and rises there so its rim never shows.
  - `map_kit.Model.oriented_box` needs right-handed axes. Left-handed ones draw the box inside out, and its collision
    fails map_kit's angle assert.
  - The original plasma at self-illumination 12 blew the whole view out under bloom. It was reduced to 2.4 before
    the animated shader above replaced it. The scene currently uses bloom 0.135 over 2.5 and auto exposure 1.7-3.35.
  - Point lights in the engine are far dimmer than Cycles shows them: the lights here are 2.5-3.2 times white.
- Not yet checked: a match played on it (bots, every mode's objects, spawns), its frame time with 102 point lights (10
  with shadows), and any sound (it has no ambience).
- Cases at a distance (2026-10-31): they drew their plain far LOD from 11.6 m and their alpha-tested stencil broke into blotches from about 11 m. LOD thresholds are now 30/80 (LOD 2 from about 38.6 m) and the stencil is blended. See `Sources/Ares/crate-v2/README.md`.
