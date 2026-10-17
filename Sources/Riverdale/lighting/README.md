# Riverdale's baked lighting

Baked indirect light (three DDGI volumes) and twelve static reflection cubes for Riverdale, planned offline and made in
the editor with the methods Collider, Cerro Blanco and Belltower were accepted with. Nothing here has run in the
editor yet. The look that goes with it (sun, ambient, fog, haze, post-processing, every light) is in
`output/riverdale/aaa/lighting/proposal.json`, each value with its old value and why.

## Files

- `config.json`: the plan, written by `riverdale_lighting.py config` from the map's own layout (`riverdale_map.PLAY`,
  `riverdale_hall`'s hall and pool). World coordinates, as the editor scripts read them: world = ( n, -e, z ).
  - `volumes`: yard (35 x 38 x 6 = 7,980 probes), hall (19 x 17 x 9 = 2,907), pool (10 x 10 x 6 = 600), baked in that
    order, about 105-127 in apart. `expected_counts` is the engine's own count (ceil( size x density / 1024 ) + 1 a
    side, 4 to 40), which the scripts check before baking.
  - `reflections`: the twelve probes, each with its capture point, world box, priority, capture exposure, the sky
    cube's tint until it's captured (`fallback_tint`) and after (`tint`). `calibration`: the west yard, whose upward
    face is 98.8% open sky over the middle the converter uses.
- `riverdale_lighting.py`: `config`, `check [--preview]` (probe grids; capture points against every drawn triangle;
  flat views of each probe's six faces and a plan, to `output/riverdale/aaa/lighting/preview/`), `preserve` and
  `status`. Its `indirect_light_object()`, `reflection_probes_object()` and `sky_fallback_texture()` are what
  `Tools/riverdale_map.py` calls to write the kept lighting back (proposal.json, `generator_integration`).
- `riverdale_reflections.py`: the captured faces to linear panoramas (EXR + sky.shader vmat), calibrated on the sky.
  `--selftest` makes faces from the sky itself and checks they come back (passes: scale 1.0002, median error 0.5%).
- `look_proposal.py`: the look and light proposal as data: `--write` (proposal.json), `--stage-scenes DIR` (the current
  scene and the proposal applied to a copy, for `render_look.py`).
- `render_look.py`: Cycles renders of a staged scene through `Tools/railhead_render.py` (Blender, headless).
- `check-scripts.py`: compiles the editor scripts against the installed engine as run_csharp wraps them, and checks
  every internal member they reach by reflection in `Sandbox.Engine.dll`'s metadata. Nothing runs.
- `../editor/prepare-lighting.cs.txt`, `bake-lighting.cs.txt`, `capture-reflections.cs.txt`,
  `import-reflections.cs.txt`, `apply-reflections.cs.txt`: the editor steps, for the native MCP's run_csharp.

## Rules these follow (engine 26.10.13, this workstation)

- Bake in the persistent editor document, never an isolated scene, and only with play stopped. Each script refuses
  during play; the bake cancels and adopts nothing if play starts, the document changes or a source asset changes.
- Probe relocation runs serially on the main thread with the engine's own trace and relocation functions. Never call
  `IndirectLightVolume.ComputeProbeRelocation`: its parallel traces race `ResourceSystem.RegisterWeak` and break
  rendering in the whole process.
- `Scene.Push()` changes the process-wide `Game.ActiveScene`: no scope is held across an `await`.
- The native cubemapper (`DDGIProbeUpdaterCubemapper`) does both passes. It replaces `GeneratedIrradianceTexture` for
  the second, so the scripts fetch it again after `RunAsync` before saving.
- Textures are written whole beside their target and moved into place; a revision's files are never overwritten (a
  running editor keeps a texture it has loaded under its old name). Start a new revision instead.
- No reflection probe is ever baked in the engine: realtime probes, `EnvmapProbe.Bake`, `RenderCubemap` and the GPU
  Quality GGX filter all run `envmap_filtering_cs`, which faulted (VK_ERROR_DEVICE_LOST) on this workstation. Probes are
  captured as ordinary camera faces and compiled by the sky asset compiler.
- `MarkUsed` asks for 1024 at most across the map (4096 ran the shared editor out of video memory once).

## Doing it

The editor is shared with other sessions and the user's own matches: ask before taking it. Riverdale must be the active
document, saved, with play stopped. Each `.cs.txt` is run with `sbox-cli` run_csharp (`{"path": ...}`, copied into the
session's exchange directory as AGENTS.md describes).

1. Put the proposal into the generator (`Tools/riverdale_map.py` and the files proposal.json names), at least every
   change marked `before_bake`, and its `generator_integration` hook. Publish and compile the map
   (`Sources/Riverdale/editor/register.cs.txt` or `compile-stale.cs.txt`), the sky included: the probes' stand-in is the
   sky's compiled cube.
2. `python Sources/Riverdale/lighting/riverdale_lighting.py config`, then `check --preview`: 0 problems, and look at
   `output/riverdale/aaa/lighting/preview/`.
3. `prepare-lighting.cs.txt`: adds the three volumes (unbaked) and makes every probe static on the sky's cube at its
   capture point. Saves the scene.
4. `bake-lighting.cs.txt`, three times (yard, hall, pool), until it returns `AllBaked: true`. Each call saves the scene.
   The yard took the longest to plan for: ~8,000 probes (Cerro Blanco's 5,500 took 2 minutes to relocate and 2.5 to
   bake); its timeout is 30 minutes. If the CLI gives up waiting, don't start it again: watch
   `output/riverdale/lighting/<revision>/<volume>-<utc>/bake-status.txt` until it says `Complete` or `Failed`.
5. `capture-reflections.cs.txt`: six 512 faces for each probe (a probe with a `faces.json` is skipped; delete its
   folder to capture it again).
6. `python Sources/Riverdale/lighting/riverdale_reflections.py`: calibrates and stages the panoramas; look at each
   probe's `panorama.png` beside its faces. Convert straight after capturing: the calibration reads the sky's EXR as it
   is now.
7. `import-reflections.cs.txt` (imports and compiles the twelve sky materials), then `apply-reflections.cs.txt` (copies
   each cube to `lighting/riverdale/<revision>/reflection_<key>.vtex`, assigns it, saves the scene).
8. `python Sources/Riverdale/lighting/riverdale_lighting.py preserve`: keeps the saved scene's "Indirect Light" and
   "Reflection Probes" groups in `indirect.json` and `reflections.json`, with `manifest.json` (the bakes, a digest of
   every light, the source hashes). Do this before the scene is regenerated: a regeneration without the kept groups
   drops the volumes.
9. Commit `Sources/Riverdale/lighting/*.json` and `Assets/lighting/riverdale/<revision>/*.vtex_c`. Compiled files are
   git-ignored: add `!Assets/lighting/riverdale/<revision>/*.vtex_c` to `.gitignore` as Belltower's and Cerro Blanco's
   are (LFS already covers `.vtex_c`).
10. Review in the editor and in a match. `RuntimeIntensity` (in `config.json`, then `prepare-lighting.cs.txt` again),
    the reflection tints and everything not marked `before_bake` are shading-time: tune them without baking again.
    `Sources/Riverdale/editor/capture.cs.txt` sets every probe to Realtime and calls `RenderCubemap` in its isolated
    scene; change that before using it on the static probes (it would run envmap filtering).

After any change to geometry, materials, the sky or a light, `riverdale_lighting.py status` says the kept bake is stale:
bake a new revision (`REVISION` in `riverdale_lighting.py`, `config`, then steps 3-9).
