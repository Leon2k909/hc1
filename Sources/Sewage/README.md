# Sewage

Sewage is a co-op Zombies map built around the reference's industrial pump tower,
twin discharge waterfalls, flooded basin, Gate A, rusty yellow catwalks, green
maintenance tunnel, red service tunnel, crane hooks, and Waterworks stencils.

The playable scene is `Assets/scenes/maps/sewage/sewage.scene`. It uses the existing
Zombies mode and game setup prefabs. `MapInformation.ZombiesOnly` admits it to
the Zombies picker without adding it to the multiplayer map allowlist.

## Sources and editor workflow

- `Tools/sewage_map.py` stages mesh, material, texture and initial scene sources
  in `output/sewage`. It never overwrites a saved editor scene.
- `Tools/sewage_reflections.py` converts six native camera captures into a linear
  EXR panorama. The normal sky texture compiler converts that to a static cube.
- `editor/import-assets.cs.txt` imports the staged assets through s&box. Copy
  editor scripts to the current native session's exchange directory and invoke
  them with `run_csharp` while play is stopped.
- Use `editor/import-scene.cs.txt` only for initial assembly. It intentionally
  refuses to replace an open Sewage document; later work preserves native edits.
- `refine-atmosphere.cs.txt`, `add-skylight-beams.cs.txt`, and
  `apply-reflections.cs.txt` apply the final mist, three overhead shafts, and
  static reflection volumes to that initial document. The saved scene contains
  these finishing edits.
- The reference camera is editor-only. `finish-preview-camera.cs.txt` upgrades
  older assemblies so the survivor's camera controls the running match.
- After script changes to the document, run `mark-scene-changed.cs.txt` and the
  native `save_scene` tool. A successful save call without a dirty document does
  not serialize arbitrary script changes.

Do not call `EnvmapProbe.Bake`, `BakeAll`, or enable realtime probes on this
workstation. Engine 26.10.13 faults in `envmap_filtering_cs.shader_cs` with its
current Vulkan driver. The saved scene uses ready-to-load static textures under
`Assets/lighting/sewage`; these compiled assets are deliberately tracked.
The supporting EXR panoramas and sky materials are under
`Assets/materials/sewage/reflections`.

## Validation

`validate-map.cs.txt` checks all eight mesh groups, their materials, four survivor
spawns, eleven navigation destinations, and the Zombies menu entry. The routes
cover both tunnel approaches, the gate, both rear platforms, both high balconies,
the rear crossing, the tower crown, and the basin escape stairs.

For a live check, use `prepare-live-round.cs.txt`, native `play_start`, then allow
the introductory sequence and first round to begin. `check-live-round.cs.txt`
records player health, round progress, zombie movement, and buy station/workbench
counts. Capture with `capture-live-round.cs.txt`, stop play, and run
`restore-test-settings.cs.txt` to restore the user's damage and launch settings.

`capture-map.cs.txt` reads `output/sewage/capture.json` and captures the actual
editor scene. `import-preview.cs.txt` accepts only a recently reviewed capture
for `Assets/ui/maps/sewage.png`.

The final native check passed all eleven routes and four spawn clearances, with
no missing models or materials. A live first round spawned eight zombies; seven
moved during the 2.5-second sample while one was already at the survivor. All
seven buy stations, including the workbench, were present. The survivor camera
was selected correctly. No new runtime errors were logged. The test ended with
play stopped and the original launch/damage settings restored. Detailed results
and captures are in `output/sewage`.
