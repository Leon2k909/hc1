## Collider (accelerator laboratory, `Tools/collider_map.py`)
- East-wing screen removal (2026-10-27): the remaining concrete screen at e 1500..1524, n -160..160, z 0..164
  is also removed. Both screens and their box colliders are gone; the generator and minimap retain this layout.
  All 68 positions remain supported, clear and reachable. Two Retakes A attacker/defender sightlines become
  exposed, confirmed with native standing-eye rays; see `Sources/Collider/wall-removal-east/README.md` and
  `installed.json`. The scoped asset import preserves the current unsaved document and concurrent door props.
- West-wing concrete screen removal (2026-10-27): the freestanding wall at plan e -1524..-1500, n -160..160,
  z 0..164 is removed, including its single box collider. `collider_map.wings` now only places the east screen.
  The scoped migration removes 12 render triangles, preserves all other geometry/physics bytes and updates the
  radar from published collision. All 68 layout positions and Retakes sight checks pass; native rays through
  the removed wall are clear. See `Sources/Collider/wall-removal/README.md` and `installed.json`.
- Built from the user's blue particle-accelerator reference on 2026-10-15. The playable research hall has an open
  two-level atrium, two main stairs, control/laboratory wings with their own stairs, and a ground-level service lane.
  A large observation window separates the combat space from the accelerator chamber. The upper laboratory display
  and accelerator machinery are scenery; the navmesh's custom bounds stop below that inaccessible upper display.
- `Tools/collider_materials.py` and `Tools/collider_map.py` stage assets under `output/collider/stage/`. The scene is
  `Assets/scenes/maps/Collider/collider.scene`; its title is in the map catalog in `Code/GameLoop/GameUtils.cs`.
  The material source uses the existing Ares surface generators without changing Ares materials. Layout uses plan
  coordinates east/north/up, mapped to world `(north,-east,up)`. Upper walkways are z256.
- Offline revision 2 adds a four-panel telemetry atlas, control desks/chairs, a rounded observation surround,
  wider steel/concrete columns, segmented ring housings, coolant risers and detailed flight cases. Ground spawn
  doglegs remain; the upper doglegs were removed because they obscured the glazed control rooms. Machine panel
  axes are right-handed so their outward faces render correctly. These assets are now imported and compiled natively.
- Detail pass 2 (`Tools/collider_detail_geometry.py`) adds bevelled handrails, bolted mounting plates, open stairs
  with thin collision decks, equipment-case lids/latches/handles, galvanized treads and worn floor stencils.
  All four models/materials are imported; the structure has 70,700 visual triangles, the detail model 97,256,
  the machine 165,594 and the glass 60. All four stair paths and their under-stair clearance passed native checks
  in `output/collider/stair-validation.json`; all 68 gameplay positions were also rechecked after import.
- Services pass 1 (`Tools/collider_services.py`) is imported and compiled. Two glazed openings beneath the
  observation gallery reveal service-room instruments; the original solid player collision is retained exactly.
  Open cable ladders, suspended cables, pipe offsets/flanges/valves and bolted gallery beams add reference detail.
  Structure/detail/machine/glass now have 71,396 / 132,960 / 165,594 / 84 triangles. The collision arrays, compiled
  model physics definitions, convex-hull source and minimap match the previous pass; all 68 offline layout checks pass.
  `Sources/Collider/verify-services.py` also checks finite nondegenerate geometry and clear render rays through all
  four window panes. Staged files and evidence are in `output/collider/services-v1/`; the primary stage now matches the saved build.
  `import-services.cs.txt` checks source hashes and backs up replaced files. Eight native views in
  `services-v1/native-review/` record the earlier geometry review. The accepted v4 bake includes the new openings;
  eleven practical lights now have wider coverage, and GI runtime intensity is 1.6 with unchanged exposure.
  Use a fresh revision for future bakes. The bake script fingerprints inputs, refuses play, cancels and drains
  its updater if the game/editor state changes, and rejects changed inputs before adopting textures.
- The east atrium stair's bottom steps have the east server cabinet standing on them (found 2026-10-19). The cabinets are
  placed mirror-image at plan (+-430, 80), but the stairs aren't mirrored (west n -210..-50, east n 40..200), so the
  east cabinet covers about half the east stair's width at its foot (world x 40 to ~115, from y -406). The other half
  (x ~120-200) is open, and the west stair is clear. Not fixed.
- Authored setup: six team spawns per side, 20 Deathmatch/Gun Game spawns, two Defuse sites, 22 Retakes spawns,
  three Domination flags, three Hot Zones, three Cash Grab/extraction pairs, buy zones, callouts and a minimap.
  Team spawns are disabled during Deathmatch, Gun Game and Retakes. Retakes spawns use the matching site/role tags.
  The minimap uses Collider's bounds and excludes the service ceiling from the upper-floor overlay.
- `--check` checks all 68 player/objective positions for clearance, support and connectivity, plus standing/crouching
  sight between opposing Retakes spawns. `Tools/collider_validate.py` checks IDs, references, resources, generated
  model/material/texture dependencies and mode wiring.
  Reports are `output/collider/layout-validation.json` and `scene-validation.json`; the latter also resolves the seven
  compiled lighting textures, including native resource references serialized as `{Id, Path}` objects.
- `Sources/Collider/editor/import-build.cs.txt` installs the staged build through the editor, refuses an open Collider
  document, writes changed assets atomically and preserves the selected scene and play state. Copy it into the current
  native MCP exchange directory before invoking `run_csharp`. `import-visual-assets.cs.txt` handles material/model/menu
  changes without replacing an open document. `export-reviewed.cs.txt` exports the saved native scene and lighting cache.
- Native validation (2026-10-15): all 68 authored positions passed engine floor support, player-box clearance and Complete
  navmesh paths, with no missing model/material resources (`native-validation.json`). All four stairs also passed.
  A fresh local TDM run on the saved services/v4 build selected the pawn camera and observed eight of nine bots moving
  over four seconds (`live-round-validation.json`). A separate game process then joined the editor host: both processes
  had the same four model identities, two correctly owned player pawns, valid materials and selected player cameras.
  A host-owned QA teleport of approximately 100 units replicated to the client (`network-validation.json` and `network/`).
  This verifies position replication, not manual keyboard traversal or an Internet latency test. The owned test client
  was closed and temporary launch/game/network settings restored before releasing the editor.
- Lighting: 82 point lights, six shadow casters. High hall/machine fills contribute diffuse/transmission only, preventing
  large specular dots. Painted metal uses a dielectric coating instead of dark bare metal. The saved GI bake is
  `Assets/lighting/collider/lighting-v4/` with 2205 probes and two passes; relocation is serial to avoid the engine's
  `ResourceSystem.RegisterWeak` race. Never call default parallel `ComputeProbeRelocation` on this workstation.
  Four custom reflection cubes (`reflection_*_v3.vtex_c`) come from ordinary camera faces and native sky texture
  compilation (`collider_reflections.py`). Do not use the GPU Quality GGX bake that faults `envmap_filtering_cs`.
  Seven compiled lighting textures are intentionally included in source control and the package. Regeneration retains
  the accepted GI and reflection objects from `Sources/Collider/lighting/`.
- The unaccepted v3 indirect bake had `GamePreserved=false` and predates the services pass; never adopt it.
  V4 completed with unchanged input hashes and game state. The document was then closed by another editor action;
  `adopt-completed-bake.cs.txt` revalidated every input hash and saved those completed textures into Collider.
  `lighting-v4/adoption-result.json` and `lighting-review.json` record this. Future bakes save their own session
  atomically after completion, avoiding dependence on whichever editor tab is selected in a later call.
- `output/collider/captures/` contains eight current native views, including service windows and ceiling details.
  They show the darker case finish, v4 GI and v3 reflections; the saved map-picker image uses the current art view.
  `live-tdm.png` and `live-client.png` show the current local host and separate client. `capture.cs.txt` uses the open document's
  persistent camera and restores it. It creates no isolated scene and performs no reflection bake. Historical
  `offline-preview/` images are approximate software renders and are superseded by these captures. Camera position,
  rotation, FOV, projection and size are reset before each render because SceneViewportWidget may overwrite them.
- `Tools/collider_package_native.py` checks saved/staged scene identity, all seven lighting textures, native evidence,
  menu-image freshness and archive CRC/SHA256. Its current default is `collider-native-v2.zip`; it requires current
  saved-scene hashes in navigation, live-match, capture and lighting-review evidence. Separate-client and performance
  status are recorded independently, so stale evidence cannot imply successful validation of a new scene.
  `output/collider/current-build.json` points to the current native-v2 archive, which matches the saved scene and assets.
  `collider-detail-v2-review.zip`, native-v1 and offline-v2 are historical snapshots; their pending-review notes are superseded.
- Native performance samples are in `performance-validation.json`: the 300-frame host sample averaged 12.85 ms
  (77.8 FPS; P99 19.93 ms); the lower-hall sample averaged 14.05 ms (71.2 FPS). These are short editor-hosted samples
  with bots, not a full-match benchmark. The raw report retains startup/GC hitches and the missed 90 FPS target.
- Network test helpers preserve launch mode, hardcore/ranked flags, no-damage, custom-game rules, lobby privacy and
  local-instance arguments. Test time/score limits are disabled to prevent map rotation during asset downloads.
  `check-network.cs.txt` records each process's player ownership, cameras and assets; `collider_verify_network.py`
  compares before/after snapshots from both processes and requires replicated movement. `network-test-state.json`
  must have `RestoredAt` after cleanup. Host startup may stall for several minutes while scanning shared assets;
  inspect the running operation and logs rather than starting hosting again after an observation timeout.

