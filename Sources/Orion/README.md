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

`v2/compare.py [name] [--scene ...] [--disable Type ...]` renders that view through the editor and prints matched
patches of the picture and the capture (shaded faces, the wet yard, the sky by the sun and overhead, the hills).

## Building it

Run in this order; `--stage` writes under `output/orion/v2/` so a running editor isn't made to recompile:

1. `python Tools/orion_textures.py [names] --out output/orion/v2/Assets/materials/orion`: the `oa_` materials
   (concrete on `v2/concrete-grain.png`, an image_gen picture of real concrete with its prompt beside it; the wet yard
   slabs; painted steels; the lettering, plates and screens atlases; flat paints). `letters`, `painted` and a surface
   name each redraw only that.
2. `python Tools/orion_sky.py --out output/orion/v2/Assets/materials/orion/sky [--preview <dir>]`: the panorama on
   Belltower's sky code with a glow round the low sun, and the picture's thin clouds painted in as a 2D layer
   (`paint_streaks`; the ray-marched heaps read as cartoon puffs and are off). `--preview` also writes
   `reference_level.png`, the sky as the reference view frames it.
3. `python Tools/orion_map.py --stage`: the models (`Tools/orion_parts.py`, `Tools/orion_backdrop.py`), the scene and
   the radar picture. Every run checks every spawn, objective and cash spot (room, floor, a walk from the spawns, no
   Retakes pair in sight). `--preview <dir> --views aerial ...` writes flat views.
4. Copy the staged files into `Assets` (the oa_ materials, the sky, the ten `orion_*` models, and the scene and
   minimap), then compile with `v2/editor/compile.cs.txt` through the native MCP's `run_csharp`, repeated until
   `Stale` is 0. After a new sky has compiled, run `orion_map.py --stage --no-models` again and copy the scene again:
   it copies the compiled sky cube to `lighting/orion/reflection_sky_<hash>.vtex_c` (named by its content, so a running
   editor loads the new cube rather than one cached under the old name) and points the probes at it.
5. Don't move or delete assets a running match is using: when v1's textures were moved out from under a match, the
   renderer reloaded them every second until the editor ran out of video memory (2026-10-15).

`v2/editor/capture.cs.txt` renders views offscreen in an isolated editor scene (config in
`output/orion/v2/captures/config.json`: views with eye, target, fov, size, optional exposure and `disable`), and
`v2/editor/navmesh-check.cs.txt` generates the navmesh in an isolated scene and paths from both team spawns to every
spot. Neither touches the open scene or play state.

## Light and look

- The sun 8.3 degrees up, 25 degrees west of north (the sky's sun is the same), half behind Launch Control.
- No baked indirect light. A small flat ambient (`SkyColor` 0.12), the sky's own indirect light, point lights, and a
  lower exposure (auto 1.0 to 1.6) under a sky tinted 2.2, so shaded faces sit dark under a bright sky as in the picture.
- Reflections: the sky's compiled cube as a static `CustomTexture` probe over the play area (tint 1.8), and much
  stronger copies over the wet floors open to the sky (`WET_FLOORS`: the yard 18, the roofs 7), each only a few inches
  deep so crates and walls don't pick them up. Screen-space reflections stay on. The runtime probe baker faults
  `envmap_filtering_cs` on this workstation's driver, so nothing is baked at load.
- ColorGrading 4900 K at 0.5 and ColorAdjustments saturation 1.1. Keep its contrast at 1.0: it works in linear HDR
  space, and 1.1 crushed every shadow to black.
- Steam is unlit (its sprites glow against the low sun instead of going dark).

## State

Checked on 2026-10-15: all 93 spots pass the offline checks; every model, material, the sky and the scene compiled with
no errors; captures of the reference view compared with the picture patch by patch; the user played a match on it in
the editor (all ten models loaded, no error models). Not yet checked: the navmesh check in the editor, a second
client, and the frame time.
