## Map daylight profiles (2026-10-17)
- The user wants different times of day across maps, with enough light for clear play. `Tools/map_daylight.py`
  defines the saved environment profiles below. Each generator applies its profile after restoring its quality
  state; Lowtide applies it at the end of `lowtide_finish.apply_scene`. Reapplication is idempotent.

  | Map | Lighting mood |
  | --- | --- |
  | Belltower | Warm afternoon |
  | Boxyard | Clear midday |
  | Cerro Blanco | Clear late morning |
  | Lowtide | Soft coastal daylight |
  | Railhead | Early autumn afternoon |
  | Riverdale | Golden morning |
  | Orion | Bright golden hour |
  | Veridant | Soft golden evening |
  | Ares | Warm Martian light |

- These are authored sky, fog and ambient-light settings. Baked maps retain the sun direction, direct light,
  GI volumes and reflection resources that their bakes expect. Their existing interior exposure settings remain
  in place. The profiles add no runtime component or per-frame work; the existing weather system uses them.
- Boxyard has its own clear HDR sky, `materials/boxyard/sky/boxyard_midday.vmat`, with sun pitch 62/yaw -15.
  `Tools/boxyard_sky.py` generates the matching 4096x2048 EXR and material into a staging directory; import the
  reviewed files through the native editor. Regenerate this sky when its profile's sun direction or colour changes.
- Orion's low sun and wet reflection cubes remain aligned. Ambient fill is slightly brighter, and map AO uses
  intensity 0.65/radius 96 to retain tunnel and stair detail. Ares keeps its warm exterior and orange practical lights.
- Native captures in `output/map-daylight-20261017/captures/` cover all nine profiles, with 14 views using the shared
  player camera's ACES post-processing and settled exposure. `verification.json` compares the saved scenes to the
  original C-drive documents and checks the generator hooks. Lowtide's independently added 56 downpipe colliders
  are recorded separately and preserved; all earlier object identities and the lighting changes are retained.
- `weather-restoration.json` verifies storm and fair-weather Apply/Restore against Lowtide's authored sky, sun,
  fog and 11 reflection probes. Native compile status reports zero errors; all 11 changed Python sources compile.
  These are scene and rendering checks, not a full multiplayer or GPU performance benchmark.

