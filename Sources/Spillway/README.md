# Spillway

A multiplayer hydroelectric map built from the supplied Riverdale dam reference. The saved scene is `Assets/scenes/maps/spillway/spillway.scene`; select **Spillway** in the multiplayer map menu. This is a separate map from Riverdale's existing nuclear power station.

The canonical checkout is `C:\sbox-projects\hc1\forked-shooter-main`. The former D: checkout is a compatibility junction to these same files.

## Realism revision — 2026-10-18

The current pass replaces the flat ambient look with a photographed cloud sky, warmer directional light, cooler shade, wet concrete and native indirect lighting. The accepted volume uses `lighting/spillway/lighting-v4`, a 20×25×6 grid with 2,647 active probes and two completed lighting passes. Five static cubes use `reflection_0_v3.vtex` through `reflection_4_v3.vtex`; the water also has camera-correct planar reflections.

The backdrop has eroded valley terrain, photographic rock textures, slope-aware snow and a forest treeline. Cases, pipes, tanks, roof fans and railings have more geometric detail. The B2 equipment cover has a draped canvas mesh with smooth normals and continuous UVs. The map has 354,200 visual triangles across its 11 chunks after the waterfall revision below. These remain purpose-built game assets, not a claim of parity with a commercial AAA production.

Waterfall motion uses decreasing world Z rather than imported UV orientation. Its periodic phases and stable noise hash retain fractional precision during long sessions; this removes the rectangular bands seen in the first close-up. The river has smaller ripples, finer foam breakup and downstream advection. `output/spillway/flow-finish/motion-validation.json` verifies all 15 consecutive native frame pairs moving downward, with median displacement +74 pixels and correlations 0.68–0.91. The frame interval varies with rendering, so this is a direction check rather than a frame-rate benchmark.

The wet concrete shader now uses an integer lattice hash instead of a large sine hash. This removes the sharp rectangular wet/dry boundaries reported on the floor. The source and generated v2 shader retain the same continuous interpolation and wetness response. Four matched native views, the original shader backup and camera restoration reports are in `output/spillway/floor-seams/`; the shader compiled successfully and the running Spillway session was preserved.

### Waterfalls — 2026-10-18

`waterfalls/waterfalls-target-v1.png` is the ImageGen paintover used for the water direction; `waterfalls/generation.json` records both prompts. The generated turbulence map is retained unchanged in Sources and `Assets/materials/spillway/waterfall-turbulence-v1.png`. The v5 shader combines two downward-moving texture fields with broad turbulence, increasing aeration, irregular edges, sky scattering, downstream foam and rising mist. Offset texture blending hides nonmatching image borders while retaining mip derivatives.

`Tools/spillway_waterfalls.py` builds the four wider, corrugated sheets against the actual faceted dam profile, clearing the concrete that previously cut a triangular hole through the water. It stages a narrow visual terrain carve and extends the back river to meet the dam toes; the old terrain covered the impact water. Three overlapping spray cards per fall create soft mist above the impact. The waterfall model grows from 288 to 5,536 triangles. The scene, seven collision hulls, three existing ModelDocs, terrain UVs and material assignments remain unchanged.

Run `rtk python Tools/spillway_waterfalls.py` to stage the local geometry revision. Copy `waterfalls/import-materials.cs.txt` and `waterfalls/import-geometry.cs.txt` into the native session exchange directory, then run them through `run_csharp`. The regular map, landscape and realism generators also retain this version. Source/asset hashes, matched player-camera views and the 16-frame downward-motion check are recorded in `validation/waterfalls-2026-10-18.json`; views are in `output/spillway/waterfall-pass/final/`. Native shaders, all three materials and all three models compiled. FPS has not been benchmarked.

The final geometry pass retained both modified ModelDocs and all seven accepted physics hull OBJ files byte-for-byte. The light and reflection captures use the persistent editor scene and preserve a separately running game. The two cancelled bake revisions were not applied; v3 was the first successful bake and v4 includes the final mesh and shader smoothing. The small final canvas colour change was made after v4. `Sources/Spillway/lighting` holds the accepted volume and probe paths for regeneration.

Final player-profile native views are written to `output/spillway/realism-final/`. The menu image is refreshed from its `reference.png`, using the shared player's native ACES profile and the saved map lighting. The supplied reference remains the visual target; playable proportions and scenery density differ.

The layout has west and east service lanes, a central cargo island, six channel bridges, an upper control room with two stairs, and the raised B2 loading terrace with two further stairs. The dam, four moving spillways, turbine building, A1 stair core, banner tower, power lines, forest and mountain backdrop follow the reference. Enclosed service rooms, cover, spawn shelters and boundary clips support the playable layout.

The scene contains 12 red and 12 blue team spawns, 18 deathmatch spawns, two bomb sites and retake positions, three domination points, five hardpoint zones, cash/extraction points, buy zones, location callouts and a minimap. It uses the project's existing game modes and network components.

## Rebuilding

Run from the project root, using the repository's `rtk` command prefix:

```powershell
rtk proxy python Tools/spillway_fetch.py
rtk proxy python Tools/spillway_map.py
rtk proxy python Tools/spillway_pipeline.py
rtk proxy python Tools/spillway_realism.py
rtk proxy python Tools/spillway_prepare_revision.py
```

All generators stage into `output/spillway`; they do not edit live engine assets. The fetch step caches the photographic textures and skies. Apply the realism step after the base pipeline. The revision preparation merges art roots into the saved native gameplay serialization and retains existing curated scripts and capture/bake configuration. `--scene-only` and `--materials-only` are supported by the map generator. For a visual-only rebuild, `spillway_realism.py --works` copies the accepted native hulls back into staging and verifies their hashes; a full geometry regeneration needs fresh navigation and collision validation.

Use native s&box `instance_status` and `editor_status` to verify the checkout and obtain the session exchange directory. Copy the `.cs.txt` method bodies from `Sources/Spillway/editor` there, then invoke each with native `run_csharp`, passing its absolute `path`:

1. `import-realism.cs.txt` registers and imports only Spillway assets, backs up changed files and compiles its shaders.
2. `import-scene.cs.txt` saves the staged scene through the editor's scene resource API. Close Spillway's scene tab first; the importer refuses to overwrite an open or running Spillway scene.
3. `compile-assets.cs.txt` compiles stale materials and models.
4. When rebuilding reflections, complete the reflection steps below before previewing or playing the new scene.
5. `validate-isolated.cs.txt` generates a real engine navmesh and checks the spawn/objective/bridge positions and stairs without switching the active scene.
6. `capture-player-look.cs.txt` uses the shared player's native camera effects in the persistent editor document. Its configuration is `output/spillway/realism-capture.json`. Temporary cameras, authored scene objects, play state and the original camera enabled states are checked and restored. `preserve_running_session` explicitly permits captures against the separate editor scene while a game runs. The older `capture.cs.txt` is retained for basic isolated diagnostics.

For a new reflection revision, capture ordinary faces with `capture-reflections-v2.cs.txt`, then run `rtk proxy python Tools/spillway_reflections.py --v3`. Set the same numeric revision in `output/spillway/reflection-config.json`; `import-reflections-v2.cs.txt` and `install-reflections-v2.cs.txt` read it. The importer refuses to replace a differing existing revision. This uses ordinary camera faces and the sky asset compiler, avoiding the GGX filtering path that has faulted on this workstation. Retain the compiled cubes under `Assets/lighting/spillway` along with their EXR sources. Regenerate a new version when changing the environment; do not overwrite an accepted cube silently.

The final native reference capture is also the map-menu thumbnail. `import-thumbnail.cs.txt` copies that capture into the map's UI asset path and registers it.

Only run a live test in an agreed shared-editor window: activate Spillway, run `prepare-live-round.cs.txt`, start play, wait for the pawn and bots, then run `check-live-round.cs.txt`. Stop play and run `restore-test-settings.cs.txt` afterwards. Restore the previous editor scene. These scripts save and restore the previous mode, hardcore/ranked settings, damage toggle and editor lobby preference. The short check runs locally with bots; a separate-client networking check is a different test.

## Verification and implementation notes

- `Sources/Spillway/validation/realism-2026-10-18.json`: the final saved scene passed all 86 native floor/clearance/nav/path checks and the four direct stair routes. All 11 models and their materials are valid; Spillway is listed and match-ready. The thumbnail matches the final native capture. All native code compilers succeeded with zero errors. Seven final player-profile captures preserved the authored objects, original camera states and running game, with no temporary capture camera left behind. The later running session was on another map and was preserved; a fresh local bot round and separate-client test were not performed for this art pass.
- `output/spillway/native-validation.json`: all 86 positions passed floor, standing clearance, navmesh snapping and complete-path checks; both control-room stairs and both B2 stairs have direct complete routes.
- The native editor reported zero compile errors, and `GameUtils.IsMatchReadyMap` and `GetMatchMaps` both include Spillway.
- The final local TDM check on 2026-10-15 spawned a player with 100 health and the correct player camera; all nine bots moved during the four-second sample. Navigation was enabled and finished generating, and all five static reflection textures were valid. Results are saved in `output/spillway/live-round-validation.json`. This was a local bot round; separate-client networking was not tested.
- The original 2026-10-15 integration audit found the map listed and match-ready, its thumbnail and minimap present, and all 11 models and their materials valid. That test stopped play and networking, restored its previous test settings and returned to the prior editor scene. The 2026-10-18 art pass preserved the later running session instead.
- Geometry: 348,952 visual triangles across 11 chunks, 27 point lights and 51 railing clips. Mountains, trees and the dam are visual scenery; play collisions stay within the multiplayer area.
- Five reflection probes use `Mode = CustomTexture` and static captured cubes. The saved scene and previews use the same textures; neither needs runtime GGX probe updates.
- `P.clip` already rotates the long local X axis. Spillway corrects the inherited scene serializer's swapped collider dimensions locally, leaving other maps unchanged.
- The upper control-room sill has two full-height openings aligned to the stairs. Keep these clear when changing facade geometry.
- Offscreen captures retain the original editor scene and running game.

## Art sources

`material-sources.json` records the CC0 Poly Haven textures, original authors and download URLs: Concrete Wall 009, Concrete Layers 02, Seaside Rock, Kloofendal 38d Partly Cloudy Pure Sky, and Kloppenheim 01/03 Pure Sky. The current sky uses Kloppenheim 03. `generated-assets.json` records the spruce billboard prompt and technical conversion; its original image is preserved in `source-assets/spruce-original.png`.

The geometry, facade signage, weathering, water and waterfall shaders were authored for this map. Shared structural helpers and some existing material assets come from the project's Riverdale and Lowtide pipelines. The map is an interpretation of the reference, with its own playable proportions and simplified scenery.
