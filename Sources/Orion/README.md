# Orion

A multiplayer map: the Orion Aerospace launch facility at golden hour after rain, built as close as possible to the
user's reference picture (`v2/reference.png`, 2026-10-15). The scene is `Assets/scenes/maps/Orion/orion.scene`.
Orion Aerospace, its planet-and-orbit mark, ORN and every marking are the map's own.

This is the second build (v2). The first (v1, an editor-finished scene with a DDGI bake and its own materials) was
retired on 2026-10-15: its tools and editor scripts are in `Backups/orion_v1/`, and its assets were moved out of
`Assets` to `output/orion/v1_assets/` on the machine that built v2 (not in source control).

## The picture's view

The picture looks north over the wet cargo yard from the overlook's roof. Its vertical lines are all parallel: it's a
shifted lens, not a camera pitched down. So the reference view is a level camera at `Tools/orion_map.py` `REF_EYE`
(plan 0,-560,400; plan is e east, n north, z up, inches) looking due north, 75 degrees across, rendered 1536 x 1356
and cropped to the picture's 1536 x 1024 with its horizon 346 down. Everything the picture shows was placed from its
bearing and height in that view: Launch Control's corner (its east side stops on the line of sight, so the sun shows
beside it), the ORION AEROSPACE block, the service tunnel and its red room, B3's oblique face with FUEL PROCESSING and
the big fuel lines along it, the OPS box and its flag, the rocket between its gantries, the masts, the radome, the
skyline of the hills (`Tools/orion_backdrop.py` `SKYLINE`, measured from the picture) and the clouds
(`Tools/orion_sky.py` `STREAKS`).

`v2/compare.py [name] [--scene ...] [--disable Type ...] [--exposure <fixed>] [--settle <frames>]` renders that view
through the editor and prints matched patches of the picture and the capture (shaded faces, the wet yard, the sky by
the sun and overhead, the hills). It renders 160 frames first by default, so the automatic exposure has settled as it
does in a match: captures of a few frames stop short of it and come out darker.

## Building it

Run in this order; `--stage` writes under `output/orion/v2/` so a running editor isn't made to recompile:

1. `python Tools/orion_textures.py [names] --out output/orion/v2/Assets/materials/orion`: the `oa_` materials
   (concrete on `v2/concrete-grain.png`, an image_gen picture of real concrete with its prompt beside it; the wet yard
   slabs; painted steels; the lettering, plates and screens atlases; flat paints). `letters`, `painted` and a surface
   name each redraw only that.
2. `python Tools/orion_sky.py --out output/orion/v2/Assets/materials/orion/sky [--preview <dir>]`: the panorama on
   Belltower's sky code with a glow round the low sun, and the picture's thin clouds painted in as a 2D layer
   (`paint_streaks`; the ray-marched heaps read as cartoon puffs and are off). `--preview` also writes
   `reference_level.png`, the sky as the reference view frames it. `--wet` writes the wet floors' cube from it
   (`oa_sky_wet`: the sky with the low sun's glitter laid in as a band, `WET_BAND`).
3. `python Tools/orion_map.py --stage`: the models (`Tools/orion_parts.py`, `Tools/orion_backdrop.py`), the scene and
   the radar picture. Every run checks every spawn, objective and cash spot (room, floor, a walk from the spawns, no
   Retakes pair in sight). `--preview <dir> --views aerial ...` writes flat views.
4. Copy the staged files into `Assets` (the oa_ materials, the sky, the ten `orion_*` models, and the scene and
   minimap), then compile with `v2/editor/compile.cs.txt` through the native MCP's `run_csharp`, repeated until
   `Stale` is 0. After a new sky (or wet cube) has compiled, run `orion_map.py --stage --no-models` again and copy the
   scene again: it copies the compiled cubes to `lighting/orion/reflection_sky_<hash>.vtex_c` and
   `reflection_wet_<hash>.vtex_c` (named by their content, so a running editor loads a new cube rather than one cached
   under the old name) and points the probes at them. Both are compiled files that `.gitignore` lets in.
5. Don't move or delete assets a running match is using: when v1's textures were moved out from under a match, the
   renderer reloaded them every second until the editor ran out of video memory (2026-10-15).

`v2/editor/capture.cs.txt` renders views offscreen in an isolated editor scene (config in
`output/orion/v2/captures/config.json`: views with eye, target, fov, size, optional exposure and `disable`), and
`v2/editor/navmesh-check.cs.txt` generates the navmesh in an isolated scene and paths from both team spawns to every
spot. Neither touches the open scene or play state.

## Light and look

- The sun 8.3 degrees up, 25 degrees west of north (the sky's sun is the same), half behind Launch Control.
- No baked indirect light. A small flat ambient (`SkyColor` 0.15: its alpha is 1, so it is the whole indirect diffuse
  light; the sky's tint and the probes only change specular), point lights, and a lower exposure (auto 1.0 to 1.2)
  under a sky tinted 2.6, so shaded faces sit dark under a bright sky as in the picture. The exposure settles at its
  cap. The cap was 1.6, but the captures it was tuned with had stopped at about 1.2 before settling, so a match would
  have been a third brighter than the tuned look; it's 1.2 now, and the captures settle (`compare.py --settle`).
- The flat ambient has no occlusion, so recesses and walls under overhangs came out as bright as open faces. Screen-
  space AO is strong (intensity 1, radius 220) and the shaded lower walls use the darker concrete (`oa_wall_dark`,
  base 104): that brought Launch Control's wall under the balcony from 52 to 36 (the picture's 36).
- The shaded faces get soft fills standing for the south sky: `LC face fill` and `ORION face fill`, high, broad and
  lavender (they read neutral after the grade), and a warm `B3 face wash`. Launch Control's two wall battens are dim
  (`tube_light( ..., colour=... )`) and shadowed, so the balcony slab stops their light.
- Reflections: the sky's compiled cube as a static `CustomTexture` probe over the play area (tint 1.8), and probes
  over the wet floors open to the sky (`WET_FLOORS`), each only a few inches deep so crates and walls don't pick them
  up. The wet floors' probes use their own cube (`oa_sky_wet`, above), so the floors show warm streaks towards the
  sun's side. Their strengths step down northwards where the yard's mirror image meets buildings instead of sky: the
  near yard 4.5, the band from the slab joint at n 244 3.8, the far yard 2.5, the tunnel mouth 1.3; the strip along B3
  5.5, the terrace 6, the yard tarp's top 3.5, the deck and the roofs 3. The yard's slabs are satin with a thin wet
  film (`slabs( film= )`) and glassy puddles over about a fifth of them, and the deck's puddles are few: glassy puddles
  everywhere mirrored the bright cube as white blotches.
  Screen-space reflections are off: the engine's SSR traces a lobe wider than the material's and keeps hits on the
  floor itself, which swapped much of the near yard's sky for the slabs' own dark colour, and its `RoughnessCutoff`
  can't be set. The runtime probe baker faults `envmap_filtering_cs` on this workstation's driver, so nothing is
  baked at load.
- The fog is a darker grey (0.47,0.45,0.47 at 0.82) and the far ridges a forested dark (`oa_mountain` 56,62,62): the
  ridges were painted blue to fake the haze that the fog then added again. Past 12000 out, the gentle slopes and
  everything past 22000 wear `oa_hill_far` (dark woods, dry grass and earth at a 9000 tile) instead of rock, and the far
  ridges are a little higher (`orion_backdrop.height`).
- The gantries are dark steel (`oa_gantry`, with a faint warm self-illumination, `orion_textures.GLOW`) round a slim
  dark core, with seven lamps a floor and ledges (`orion_parts.service_tower`), so they read as a lit lattice. The
  deck front's fascia and parapet are the shaded concrete (`oa_wall_dark`), with rows of cases along the deck wall and
  a lamp over the mezzanine door.
- The sky's low keys are row means over the whole panorama (they had been taken from the picture's sun half, which
  brightened that side twice), with a tighter glow and `SUN_HALO` 0.4.
- ColorGrading 5300 K at 0.5 and ColorAdjustments saturation 1.1. Keep its contrast at 1.0: it works in linear HDR
  space, and 1.1 crushed every shadow to black.
- Steam is unlit (its sprites glow against the low sun instead of going dark).
- The capture renders with the scene's own ACES tonemapper. Since 2026-10-17 the player camera picks AgX (see the
  shared camera look in CLAUDE.md), so in a match the picture is tone-mapped differently. That hasn't been compared.

## State

Checked on 2026-10-15: all 93 spots pass the offline checks; every model, material, the sky and the scene compiled with
no errors; the user played a match on it in the editor (all ten models loaded, no error models).

On 2026-10-16/17, after the second round (the rocket's nose and taller, enclosed gantries, the yard's tarp block,
crates and lane lattice to the picture's places, B3's west side receding behind the line of sight, weathered yellow
paint, the tunnel a warm arcade with a red doorway, and the light and reflection changes above), everything compiled
and the navmesh check found complete paths from both team spawns to all 95 spots.

On 2026-10-17, after the third round (the exposure cap, the wet floors' cube, the lit gantries, the far hills, the
deck front's parapet, fascia and cases), everything compiled again and the navmesh check again found complete paths to
all 95 spots. The reference view (capture `v4f`, settled exposure) against the picture, median of each patch
(`v2/compare.py`; capture / picture):

| patch | capture | picture | | patch | capture | picture |
|---|---|---|---|---|---|---|
| Launch Control face | 54 | 52 | | sky by the sun | 241 | 241 |
| ORION face | 42 | 45 | | blue sky | 132 | 129 |
| B3 face | 55 | 53 | | hills | 124 | 122 |
| yard, far | 39 | 40 | | deck front | 39 | 37 |
| yard, near | 66 | 64 | | LC wall under the balcony | 39 | 36 |
| yard, middle band | 48 | 47 | | foreground terrace | 40 | 42 |

Every patch is within 4 levels of the picture's. What the medians don't show, and is still unlike the picture:

- The picture's floors are mirror-wet, with long warm streaks of the sun and the lamps; here they're satin with a
  sheen and a few glassy puddles (the terrace's brightest tenth is 105 against 165). The deck front's brightest tenth
  is 179 against 118: its puddles are too bright where the picture's floor there is dark and even.
- The hills are dark silhouettes with woods and fields. The picture's are a lit hill town, with houses and lights.
- The gantries are an evenly lit orange lattice. The picture's are dark steel picked out by many small lamps, and
  the steam round the rocket's foot is much thicker.
- Launch Control, the deck front's arcade and B3's fuel lines are simpler builds than the picture's: its Launch
  Control is a taller block with its lit control room at the top left, and B3 has a bank of big pipes.

Not yet checked: a second client and the frame time.

The offline reach check missed one thing the navmesh found: player clips. A railing's clip is a box along its rail
(`riverdale_parts.clip`), and the scene must size it ( length, thickness, height ) under the rail's heading turned 90
degrees (`write_scene`). Sized the other way round, as Riverdale's and Riverside's are, every clip lay across its
rail: each stair's rail put a wall across the stair at its middle, and nothing above the terrace was reachable.
