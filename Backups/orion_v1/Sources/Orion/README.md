# Orion

Playable launch-facility map built from the supplied visual reference. The saved
scene is `Assets/scenes/maps/Orion/orion.scene`.

The launch control and fuel-processing wings connect a wet cargo yard, an upper
launch deck, and a three-entry service underpass. Four stair routes connect the
two floors. The rocket and gantry, radome, lighting masts, pipes, yellow guardrails,
control-room displays, cargo cases, containers, forklift and steam vents carry
the reference's main architectural features.

## Editing and regeneration

The editor-saved scene is authoritative. Edit and save it with native s&box tools.
`Tools/orion_map.py` stages geometry and the initial scene specification; do not
replace the finished scene with that initial specification. It does not contain
the editor's final lighting, reflection probes, woodland or particle effects.

`Tools/orion_materials.py` produces the map's PBR materials and original sign atlas.
`Tools/orion_sky.py` stages its sky. `Tools/orion_finish_stage.py` rebuilds the
final geometry and stages light/woodland placement without rewriting the scene.
`Tools/orion_image_assets.py` converts the selected v2 sky PNG into the engine's
linear-light EXR format and selects the v2 concrete albedo. Their original PNGs
are retained alongside the materials; the exact built-in imagegen prompts and
provenance are in `concrete-v2-prompt.txt` and `sky-v2-prompt.txt`.
The editor scripts in `editor/` are method bodies for native `run_csharp`; copy
them to the current sbox-cli session exchange directory before running them.

- `import-assets.cs.txt`: registers staged assets through the editor.
- `finish-lighting.cs.txt`: applies authored work lights and native vista trees.
- `add-atmosphere.cs.txt`: adds four bounded, looping steam emitters and distance haze.
- `bake-lighting.cs.txt`: serial DDGI relocation and two native lighting passes.
- `capture-reflections.cs.txt`, `Tools/orion_reflections.py`, and
  `apply-reflections.cs.txt`: produce and install three static cubemap reflections.
- `capture.cs.txt`: renders the actual scene for visual QA and map artwork.
- `validate-map.cs.txt`: tests standing space, support and complete navigation
  paths at all 70 authored spawn/objective locations.
- `prepare-live-round.cs.txt`, `check-live-round.cs.txt`, and
  `restore-test-settings.cs.txt`: run and clean up a local TDM integration test.
- `prepare-network-test.cs.txt`, `network-snapshot.cs.txt`, and
  `restore-network-settings.cs.txt`: prepare a private two-process match, record
  player ownership and asset loading in each process, and restore all temporary
  settings. Time and score limits are disabled only for the test. The snapshot
  script writes into its own process's CLI exchange directory.
- `Tools/orion_verify_network.py`: compares before/after snapshots from both
  processes to verify distinct owned pawns and observed replicated movement.
- `Tools/orion_client_snapshot.py`: connects to an existing client PID, reads
  its native snapshot and closes its own CLI connection without closing the game.
- `check-position-replication.cs.txt`: exercises the existing player teleport
  owner RPC to a clear, supported nearby position between those snapshots.
- `fix-static-networking.cs.txt`: saves the authored woodland, steam and
  reflection objects with `NetworkMode.Snapshot`, using an editor undo scope.

The final DDGI textures live under `Assets/lighting/orion/lighting-v3/`.
Reflection textures are `reflection_*_v2.vtex_c` in the parent directory.
Keep these files in source control: engine lighting bakes have no ordinary
uncompiled texture source. Static probes deliberately use `CustomTexture`;
the runtime GGX probe baker is unreliable on this workstation's graphics driver.
Authored static visuals must use `NetworkMode.Snapshot` (serialized value 2).
`Never` excludes them from network-created client scenes. Keep the woodland
parent and its 320 children, all four steam emitters and all three reflection
probe objects in the scene snapshot. Temporary review cameras use `Never`.

## Gameplay

The map contains team spawns, free-for-all spawns, two bomb sites with retake
positions, three domination points, three hardpoint locations, cash collection
and extraction points, buy zones, named areas, a bounded play area, a minimap,
and a complete navigation mesh. Map selection and Quick Play register Orion
through `Code/GameLoop/GameUtils.cs`.

Native validation reports and engine captures are retained under `output/orion/`.
The local TDM integration check verified a live player camera, supported player
spawn and moving bots on both teams. All 70 authored spawn/objective positions
passed standing-space, floor-support and complete navigation-path checks.

The private two-process TDM check passed on 2026-10-15. Both processes reported
the same two owned pawns, six valid map models, no missing map materials, valid
DDGI textures, three custom reflection cubes, 320 vista trees and four steam
emitters. A 64-unit position change through `PlayerPawn.Teleport`'s owner RPC
was observed identically by host and client. The report is
`output/orion/network-validation.json`, with four original snapshots beside it.

That check exposed authored visual objects using `Never`; their saved scene
setting was corrected to `Snapshot`. The existing client received the corrected
visuals through native `NetworkSpawn` and passed the checks above. A fresh join
after this setting correction was not repeated. The final serialized settings
were checked separately, and all temporary test settings and processes were
cleaned up. Native project compilation finished with zero errors.

`Assets/ui/maps/orion.png` and `output/orion/captures/live.png` are native engine
captures, not concept renders. The sky and concrete texture sources were made
with the built-in image generation tool; their exact prompts and source paths
are retained in the two provenance text files linked above.
