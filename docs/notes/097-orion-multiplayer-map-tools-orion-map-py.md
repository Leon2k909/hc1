## Orion (multiplayer map, `Tools/orion_map.py`)
- The user asked for a map as close as possible to their picture of a rocket launch facility at golden hour after rain
  (2026-10-15; kept as `Sources/Orion/v2/reference.png`). Orion Aerospace, its planet-and-orbit mark, ORN and every
  marking are the map's own. `Sources/Orion/README.md` has the build steps and the look's settings.
- v2 (2026-10-15) replaced a first build. v1's tools and editor scripts are in `Backups/orion_v1/`; its models,
  materials and DDGI bake were moved out of `Assets` to `output/orion/v1_assets/` on the building machine (never
  committed, and not needed: nothing references them).
- The picture's view is a shifted lens (its verticals are parallel): a level camera at plan `0,-560,400` looking due
  north, 75 degrees across, rendered 1536 x 1356 and cropped to 1536 x 1024 with the horizon 346 down.
  `Sources/Orion/v2/compare.py` renders it and prints matched patches against the picture. A pitched camera doesn't
  frame it the same way.
- Scripts, in order: `Tools/orion_textures.py` (the `oa_` materials; the concrete's grain is
  `Sources/Orion/v2/concrete-grain.png`), `Tools/orion_sky.py` (Belltower's sky code with a glow round the low sun and
  the picture's thin clouds painted in as a 2D layer: the ray-marched heaps read as cartoon puffs, so they're off),
  `Tools/orion_map.py --stage` (with `Tools/orion_parts.py` and `Tools/orion_backdrop.py`). Each runs offline into
  `output/orion/v2/` (ignored), then the files are copied into `Assets` and compiled with
  `Sources/Orion/v2/editor/compile.cs.txt` until Stale is 0.
- Layout: Red Team spawns in the west court behind Launch Control 01, Blue Team in the east court behind Fuel
  Processing. Bomb site A is the launch deck, B the wet cargo yard. Every run checks all 93 spots (room, floor, reach,
  no Retakes pair in sight).
  - Launch Control's upper east side stops on the line of sight from the overlook through its front corner (a wedge
    fills the corner), so nothing of the tower shows past the corner and the sun glows beside it as in the picture.
  - B3 has a wedge on its south-west whose west face runs at 144 degrees (`B3_FACE_BEARING`): the picture sees B3's
    face at an angle, its lettering and joints sloping down to the right. The fuel lines run along that face, then
    south to the overlook's north wall; the low ones are a kerb you step over or mantle.
  - The skyline of the hills is the picture's, measured by bearing (`orion_backdrop.SKYLINE`): past 15000 the land
    climbs to it at the far edge. No cone trees: at that size they read as a picket fence.
- Light: no baked indirect light. Flat ambient (`SkyColor` 0.15), which has no occlusion, so screen-space AO is
  strong (intensity 1, radius 220) and walls in shade use the darker concrete (`oa_wall_dark`). Soft lavender fills
  stand for the south sky on the shaded faces (`LC face fill`, `ORION face fill`, the warm `B3 face wash`).
  Exposure auto 1.0-1.2, sky tint 2.6, ColorGrading 5300 K at 0.5, ColorAdjustments saturation 1.1 (its Contrast works
  in linear HDR space: 1.1 crushed every shadow to black).
  - Auto exposure settles at its cap. The cap was 1.6, but the captures the look was tuned with had stopped at about 1.2
    before settling, so a match was a third brighter than they showed. `compare.py` now renders 160 frames first
    (`--settle`), and the cap is 1.2.
  Reflections: the sky's compiled cube as a static CustomTexture probe (tint 1.8), plus probes only inches deep over
  the wet floors open to the sky (`WET_FLOORS`, stepped down where the floor's mirror image meets buildings). Those use
  their own cube, `oa_sky_wet` (`orion_sky.py --wet`: the sky with the low sun's glitter as a band, `WET_BAND`), so the
  floors show warm streaks towards the sun. SSR is off: the engine's SSR swapped the near yard's sky for the slabs' own
  colour. The cubes are copied to `Assets/lighting/orion/reflection_{sky,wet}_<hash>.vtex_c`, named by their content
  so a running editor loads a new one; `.gitignore` lets both in.
- The gantries are dark steel with a faint warm glow (`orion_textures.GLOW`) and seven lamps a floor. Past 12000 out,
  gentle slopes and everything past 22000 wear `oa_hill_far` (woods, dry grass, earth) instead of rock.
- The captures render with the scene's ACES tonemapper; since 2026-10-17 the player camera picks AgX (see Shared camera
  look), so a match is tone-mapped differently. Not compared yet.
- Steam (copies of the gun smoke prefab) is unlit, so it glows against the low sun instead of going dark.
- Don't move or delete assets a running match uses. When v1's textures were moved out from under the user's Orion
  match (2026-10-15), the renderer reloaded them every second until the editor ran out of video memory and stalled.
- Player clips: `write_scene` sizes each railing clip ( length, thickness, height ) under its rail's heading turned
  90 degrees. The ( size[1], size[0], size[2] ) it first copied from Riverdale laid every clip across its rail: each
  stair's rail walled the stair off at its middle, and only the in-editor navmesh check caught it (the offline reach
  check ignores clips).
- Checked: the offline spot checks, every asset compiling, the user playing a match on v2 in the editor (all ten models
  loaded, no error models), and the in-editor navmesh check (`Sources/Orion/v2/editor/navmesh-check.cs.txt`: complete
  paths from both team spawns to all 95 spots, again after the 2026-10-16 round and the 2026-10-17 one).
- Against the picture (2026-10-17, capture `v4f` at settled exposure, `Sources/Orion/v2/compare.py`; README's State
  has the table): all twelve patch medians (the shaded faces, the yard's three bands, the sky by the sun and overhead,
  the hills, the deck front, Launch Control's lower wall, the terrace) are within 4 levels of the picture's. Still
  unlike it:
  - the floors are satin with a few glassy puddles where the picture's are mirror-wet with long warm streaks (the
    terrace's brightest tenth 105 against 165), and the deck front's puddles are too bright (179 against 118);
  - the hills are dark woods and fields with no town or lights;
  - the gantries are an evenly lit orange lattice, not dark steel picked out by small lamps;
  - Launch Control, the deck front's arcade and B3's pipe bank are simpler builds.
  Not yet checked: a second client and the frame time.

