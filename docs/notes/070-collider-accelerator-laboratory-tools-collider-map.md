## Collider (accelerator laboratory, `Tools/collider_map.py`)
- Column base accepted (2026-10-30): the base beside B1 LABS, left of the stairs up to CONTROL, at plan
  `(-960,-500,0)`. The user approved applying it after the room-context view. Exactly 12 original base triangles
  were replaced with the reviewed 35,002-triangle mesh: chipped grout, bevelled steel, eight threaded anchors,
  open washers/hex nuts, six welded stiffeners, physical weld beads and localized coating loss/fastener oxidation.
  Eight private material bindings and exact approved positions/UVs/normals are retained. Structure is now 284,871
  triangles. The complete original column, unrelated original face lines/attributes, saved scene, all physics,
  other three bases and prior accepted props are preserved. `Tools/collider_column_base.py` and selected
  `collider_map.column_base` branch preserve the new mesh and original collision during regeneration.
  Old standalone before resources removed; rollback is outside Assets. Matching primary staged structure files
  were synchronized. `Sources/Collider/column-base-trial-v1/installed.json` and
  `output/collider-column-base-accepted-20261030/` record integration. These structure hashes supersede historical
  acceptance guards. Existing offline evidence: `output/asset-improvement-20261030/column-base/`; the unfinished
  full-column comparison render was stopped on approval to free resources. No editor/GPU used; native
  import/appearance/LOD/performance pending.
- Cooling unit accepted (2026-10-30): refined proposal at plan origin `(-1470,1702,20)` replaces exactly 170 old
  render triangles with 45,890 approved triangles. Machine mesh is now 182,141 triangles. Fourteen private material
  bindings and exact approved positions/UVs/normals are retained. All unrelated original face lines/attribute
  tables, material bindings, saved scene, other packed sources and prior approved private sources are preserved.
  Authored collision remains absent; other cooling units are unchanged. Regeneration: `Tools/collider_cooling_unit.py`
  and selected `collider_map.cooling_unit` branch. Old standalone before resources removed, rollback outside Assets.
  Newer/different primary staged machine files preserved. `Sources/Collider/cooling-unit-trial-v1/installed.json`
  and `output/collider-cooling-unit-accepted-20261030/` record/prove integration. These machine hashes supersede
  historical acceptance guards while preserving prior upgrades. No editor used; native import/appearance/LOD/performance pending.
- Cooling-unit proposal (2026-10-30): private review of the original machine-hall unit at local origin plan
  `(-1470,1702,20)`. `Sources/Collider/cooling-unit-trial-v1/` copies all 170 saved triangles/UVs/normals from
  `collider_machine.obj`. The isolated 45,890-triangle candidate adds six recessed fans with closed curved blades
  and wire guards, finned side exchangers, service hardware, physical dials and grounded levelling feet. Original
  display size/atlas quadrant retained; neither variant authors collision. Comparison ground is actual plan z=0;
  the old housing begins twenty inches above it. Original/map sources remain unchanged until user approval.
  Checks protect 165 source files, including the newly accepted console. Evidence:
  `output/asset-improvement-20261030/cooling-unit/`. One idle-priority two-thread CPU render, no editor/GPU;
  native import/appearance/LOD/performance pending.
- Control console accepted (2026-10-30): the reviewed second proposal at east station `(side=1,north=-55,floor=256)`
  replaces exactly 688 old triangles with 27,334 approved triangles; structure is now 249,881 triangles. Fourteen
  private material bindings and exact positions/UVs/normals are retained. All unrelated original face lines,
  attribute tables, material bindings, full ModelDoc physics and saved scene remain. Earlier approved chair/monitor
  geometry is preserved; detail/machine/glass and other approved private assets are byte identical. Regeneration:
  `Tools/collider_console.py`, selected `collider_map.control_desk`, original two station clips retained. Other
  stations are unchanged. Old standalone before resources are removed, rollback outside Assets; matching primary
  staged sources synchronized. `Sources/Collider/console-trial-v1/installed.json` and
  `output/collider-console-accepted-20261030/` record/prove integration. These structure hashes supersede historical
  chair/monitor/valve receipts while proving retention. No editor used; native compilation/appearance/LOD/performance pending.
- Control-console proposal (2026-10-30): private review at east station `side=1, north=-55, floor=256`.
  `Sources/Collider/console-trial-v1/` extracts all 688 actual saved desk triangles, UVs and normals; the candidate
  adds closed rounded panels, recessed vents, proper keyboard/controls, service hardware, contact wear and routed
  cables. The original 100x48 display, atlas quadrant and desk clip remain. No packed map source or scene is edited;
  original assets stay until user approval. Evidence: `output/asset-improvement-20261030/console/`. Source checks
  protect prior accepted models/materials. Rendering uses one idle-priority CPU process confined to two logical
  CPUs, with no editor or GPU rendering, per the user's request while playing another game. Native checks pending.
- Weathered valve accepted (2026-10-29): the user selected surface revision 2 and requested old assets removed.
  Both existing instances at plan `(-1280,280,770)` / `(1280,280,770)` are replaced. Exactly 1,356 old render triangles
  are removed and 40,328 approved triangles inserted; the detail mesh now has 227,608 triangles. The twelve approved
  material bindings, transforms, UVs and normals are retained. All unrelated original face lines/attribute tables,
  prior material remaps, full physics suffix, saved scene and structure/machine/glass sources are preserved.
  Case/cabinet geometry remains exact; monitor/chair structure sources are byte identical. The unused old standalone
  `before` game resources are deleted, with rollback outside Assets. `Tools/collider_valve.py`, `collider_services.valve`
  and `collider_map.configure` retain the new design on regeneration. The old implementation remains solely as an
  offline reference. `Sources/Collider/valve-trial-v1/installed.json` and `output/collider-valve-accepted-20261029/`
  retain acceptance, exact scope/attribute/geometry checks and guarded primary-stage synchronization. This receipt
  supersedes older case/cabinet detail hashes; its verification covers their retention. No editor was opened;
  engine compilation, appearance, LOD and performance validation remain pending.
- Historical model proposal (2026-10-29), subsequently accepted above: valve at plan `(-1280,280,770)`.
  The user found the first proposal too smooth. Surface revision 2 preserves that version and render under
  `output/asset-improvement-20261029/valve/revisions/smooth-v1/`, then adds small casting waviness/parting detail,
  unique casting/bonnet/flange/stem UVs, casting pits, paint/primer loss, metalness variation, bolt-centered grime,
  oxidation streaks, packing grease and scratched/tarnished hardware. The updated material renderer reads the
  exported metalness maps. Previous/revised proposal views share the same camera, lights, exposure and scale.
  `Sources/Collider/valve-trial-v1/` copies all 678 actual baseline triangles/UVs/normals from `collider_detail.obj`.
  The private 20,164-triangle proposal adds a smooth cast body/bonnet, separate packing collar/gaskets, flange fasteners,
  real helical stem thread, rounded handwheel/curved spokes, grip wear and an ID plate. Neither variant adds physics.
  Original preview hashes are historical; the acceptance receipt above covers the installed revision. Actual-mesh matched offline renders, framing, audit and checks are
  under `output/asset-improvement-20261029/valve/`. Native compilation, appearance, LOD and performance remain pending.
- Operator chair accepted (2026-10-29): the user selected the review at plan `(1723,-55,256)`.
  Exactly 100 old render triangles were replaced by the reviewed 8,672; the structure now has 223,235 triangles.
  Four private material remaps are added. All unrelated original faces/attributes, existing material bindings,
  full ModelDoc physics suffix, saved scene and accepted case/cabinet detail sources are preserved. The accepted
  monitor is retained. `Tools/collider_chair.py` and the selected `collider_map.control_desk` branch reproduce the
  exact chair mesh, UVs and normals; `_legacy_control_desk` retains the desk and original chair clip. Other station
  placements remain unchanged. Unused old standalone resources are retired outside Assets; matching primary staged
  sources are synchronized. `Sources/Collider/chair-trial-v1/installed.json` and `output/collider-chair-accepted-20261029/`
  retain scope/geometry/material/collision evidence. Work remained offline at the user's request; engine compilation,
  appearance, slimmer-chair collision fit and performance validation are pending.
- Wall monitor accepted (2026-10-29): the user selected the reviewed display at plan `(1880,-190,381)`.
  Exactly 26 old triangles were replaced by 6,088 approved triangles; the structure now has 214,663 triangles.
  Every unrelated original face line/attribute table, existing material binding, ModelDoc physics suffix and saved
  scene is retained. Seven private material remaps were added. Detail sources containing the accepted case/cabinet
  are byte identical. `Tools/collider_monitor.py` and the selected `collider_map.monitor` branch reproduce its exact
  mesh, UVs, normals and bindings without collision. `Sources/Collider/monitor-trial-v1/installed.json` and
  `output/collider-monitor-accepted-20261029/` record the source installation and guards. Unused old standalone
  resources were retired outside Assets; matching primary staged sources were synchronized. Work remained offline
  at the user's request; native compilation, appearance and performance validation are pending.
- Historical chair proposal (2026-10-29), subsequently accepted above: plan `(1723,-55,256)`, reviewed under
  `Sources/Collider/chair-trial-v1/`. All 100 baseline triangles/UVs/normals match the saved structure mesh. The
  private proposal isolates the unfinished operator-chair draft: shaped upholstery, separate shell/spine, adjustment
  controls, a gas lift, five-spoke base and twin casters, with cloth/plastic/metal PBR surfaces. Before/after have
  100 / 8,672 triangles and the same original player clip. The acceptance receipt above supersedes the preview's
  structure hashes; native collision fit and appearance remain pending. Evidence: `output/asset-improvement-20261029/chair/`.
- West cabinet accepted (2026-10-29): the user selected the reviewed equipment cabinet at plan `(-430,80,0)`.
  Exactly 276 old render triangles were replaced with 17,044 approved triangles; the detail mesh now has 188,636.
  The original collision box, ModelDoc/MTL, saved scene, all unrelated original face lines and accepted case are
  preserved. `Tools/collider_west_cabinet.py` and the west `collider_map.detail` branch retain it on regeneration.
  The old standalone `before` resources were retired outside Assets. `Sources/Collider/west-cabinet-trial-v1/`
  and `output/collider-cabinet-accepted-20261029/` record acceptance, installation and exact scope/geometry checks.
  Work remained offline at the user's request; engine compilation and native appearance remain pending.
- Historical wall-monitor review (2026-10-29), subsequently accepted above: plan `(1880,-190,381)`.
  `Sources/Collider/monitor-trial-v1/` copies all 26 baseline triangles/UVs/normals from the saved structure mesh.
  The proposal retains its display atlas and active image size while adding a chamfered casing, recessed screen,
  physical operator controls, open rear vents, tilt mount, fixings and power cable. Standalone resources are under
  `models/props/collider/monitor-trial-v1/`; matched actual-mesh Cycles renders and offline checks are under
  `output/asset-improvement-20261029/monitor/`. Its original preview hashes are historical; the installation receipt
  above supersedes the structure hashes. Engine validation remains pending.
- Equipment case accepted (2026-10-29): the user selected the new flight-case design at plan `(-1150,-350,0)`.
  Removed exactly 2,420 old render triangles and inserted the reviewed 15,568; all other original face lines/attribute
  tables, saved scene and ModelDoc physics bytes are preserved. `collider_equipment_case.py` and the corresponding
  placement branch in `collider_map.hardcase` reproduce the accepted mesh exactly. Other case placements are unchanged.
  The unused old standalone `before` game resource was deleted, with rollback data outside Assets. `Sources/Collider/
  equipment-case-trial-v1/installed.json` and `output/collider-case-accepted-20261029/` record installation, exact
  generator/geometry/collision checks and guarded primary-stage synchronization. The user asked to work without the
  editor: no launch or connection was used for installation; engine compilation and native appearance remain pending.
  The west cabinet was subsequently accepted; its installation receipt supersedes this pass's detail OBJ hash.
- Ceiling fabrication `ceiling-v1` (2026-10-27) replaces 36 hanging solid blocks with bracketed industrial LED fixtures,
  connected power conduits and cooling fins. Nine plain beam envelopes now have separate flanges/webs, edge bevels and
  stiffeners. Three ceiling undersides use a private matte concrete material and recessed construction joints.
  The structure now has 208,601 triangles; original physics/hulls and the saved scene are unchanged. Native model/material
  compilation and all 68 support/clearance/nav checks pass. `Tools/collider_ceiling.py` plus generator hooks preserve it;
  `Sources/Collider/ceiling-v1/installed.json` records the accepted stage-v3 and matched native views. Existing GI/reflections
  are retained; no new bake or match-performance result is claimed. Prior craft/finish structure hashes below are historical.
- Wall seam correction (2026-10-27): the accelerator side walls overlapped the playable shell at e +/-1900,
  n674..980, z0..900, competing `co_concrete` against `cf_wall`. `Tools/collider_wall_seams.py` trims those faces
  and the smaller accelerator rear-corner overlaps; `collider_map.build` retains the correction. Only the machine
  OBJ changes: 20 old triangles replaced by 31 retained fragments, 136,421 total. Original attributes/unaffected
  face lines, all materials/textures, physics/hulls and saved scene are unchanged. Independent concrete overlap
  audit: eight groups before, zero afterward; native compilation, four corridor views and all 68 clearance/nav
  checks pass. `Sources/Collider/wall-seams-v1/installed.json` supersedes craft-v1's machine OBJ hash. Evidence and
  backups: `output/collider-wall-overlap-20261027/`. Collider remained selected/stopped/clean; no new lighting or
  match performance result is claimed.
- Fabrication/detail pass `craft-v1` (2026-10-27) supersedes the finish-v1 geometry below. Twenty rail runs, including
  eight stair runs, now use round closed steel tubes, dedicated contact-wear/roughness/metalness maps, smaller anchor
  hardware, weld collars and folded toe plates. Background accelerator guards use simpler hardware. Two recessed
  drains, two split access covers with flush ring pulls, three shallow concrete spalls and thirteen actual cut
  control joints add floor construction depth. The structure/machine have 169,073 / 136,410 triangles; the four base
  static models total 438,527, up 7.4% from finish-v1. Published collision/convex-hull sources and the scene are unchanged.
  Nineteen assets compiled/imported; all 68 native floor/clearance/navmesh checks pass with no missing resources.
  `Tools/collider_craft.py` and generator hooks retain the work; scoped migration is `collider_stage_craft.py`.
  `Sources/Collider/craft-v1/README.md` and `installed.json` identify the accepted stage-v6 and final native images.
  The older pale angular spall trial was rejected. GI v6/reflections v4 are retained; they were not rebaked for this pass.
  Bitmap screenshots at 1600x900 visibly undersampled thin rails/stairs relative to the viewport. The canonical
  `Sources/Collider/editor/capture.cs.txt` now defaults to 2x native resolution and filtered downsampling, warms material
  textures and restores the persistent camera. Hidden-session rendering also blurred the sign atlas despite a sharp
  native mip-zero readback; temporarily matching `SceneEditorSession` with `MakeActive(false)` during the synchronous
  render fixes it. The previous session is restored in `finally`, without bringing Collider's tab forward. A disposable
  texture-streaming scope follows the engine's asset-preview implementation. Captures record nineteen source hashes;
  no game quality preference changes. Final views are native 3728x1832, resolved to 1864x916, in
  `output/collider-detail-v3-20261027/captures-final/`; the menu image uses their art view. The selected Veridant document
  and its dirty/play state were preserved while finishing Collider in its background document. No live-match or new
  performance benchmark was run. The existing primary staged scene was not replaced; older package/finish receipts
  describe historical geometry.
- Environment finish v1 (2026-10-27) is installed. `Tools/collider_finish.py` adds closed bevelled portal frames,
  coved skirting, screwed thresholds, local circulation/door wear and ceiling mounts for the existing hanging lights.
  The concrete floor uses a matched 2 m photographic albedo/GL-normal/roughness/AO scan; walls and columns use the
  existing cast-concrete albedo with its matching GL normal at the scan's 1.805 m scale. Soffits have a separate matte
  concrete finish. No coplanar floor-joint strips were retained. The structure now has 109,614 visual triangles;
  original retained geometry and all physics definitions/hull sources are preserved. Other model sources are unchanged.
  Native import/compilation, five final screenshots and all 68 support/clearance/Complete-navmesh checks passed.
  Current GI is `lighting-v6` (two passes, 2205 probes); four static reflection cubes are `reflection_*_v4.vtex_c`.
  `Sources/Collider/lighting/` retains these accepted objects, and the map-picker image uses the new native art view.
  `Sources/Collider/finish-v1/README.md` and `installed.json` record hashes, source attribution, guards and rollback.
  `output/depot-finish-20261027/` holds the accepted stage-v8 and final native evidence. The existing primary staged
  scene had a different hash and was preserved; a reviewed scene snapshot is saved with this pass. No new live-match,
  multiplayer or performance benchmark was run. Earlier native-v2 package/live/performance records below are historical.
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
- East stair server repair (2026-10-27): the former 48x60x138-inch cabinet at plan (430,80,0) is replaced with a
  28x44x84-inch rack at (430,-60,0), 78 inches clear of the near stair edge. Its single collision box moves/resizes
  with it; all other detail-mesh lines, physics and material bindings are retained. Recessed equipment, open side
  louvres, frame hardware, rear fans and levelling feet replace the flat repeated panels. The west rack is unchanged.
  `Tools/collider_server_rack.py` and the east branch in `collider_map.detail` preserve regeneration. Native compilation,
  40 stair-width body probes, all four stair routes and all 68 map navigation checks pass. Sources/accepted hashes and
  screenshots: `Sources/Collider/server-rack-v1/`, `output/collider-server-rack-20261027/`. No new match-performance result.
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
  `Assets/lighting/collider/lighting-v6/` with 2205 probes and two passes; relocation is serial to avoid the engine's
  `ResourceSystem.RegisterWeak` race. Never call default parallel `ComputeProbeRelocation` on this workstation.
  Four custom reflection cubes (`reflection_*_v4.vtex_c`) come from ordinary camera faces and native sky texture
  compilation (`collider_reflections.py`). Do not use the GPU Quality GGX bake that faults `envmap_filtering_cs`.
  Seven compiled lighting textures are intentionally included in source control and the package. Regeneration retains
  the accepted GI and reflection objects from `Sources/Collider/lighting/`.
- The unaccepted v3 indirect bake had `GamePreserved=false` and predates the services pass; never adopt it.
  V4 completed with unchanged input hashes and game state. The document was then closed by another editor action;
  `adopt-completed-bake.cs.txt` revalidated every input hash and saved those completed textures into Collider.
  `lighting-v4/adoption-result.json` and `lighting-review.json` record this. Future bakes save their own session
  atomically after completion, avoiding dependence on whichever editor tab is selected in a later call.
- `output/collider/captures/` contains eight historical native views, including service windows and ceiling details.
  They show the earlier case finish, v4 GI and v3 reflections. Current finish-v1 views and the map-picker source are
  in `output/depot-finish-20261027/captures/`. `live-tdm.png` and `live-client.png` show the earlier local host and separate
  client, not a test of finish-v1. `capture.cs.txt` uses the open document's
  persistent camera and restores it. It creates no isolated scene and performs no reflection bake. Historical
  `offline-preview/` images are approximate software renders and are superseded by these captures. Camera position,
  rotation, FOV, projection and size are reset before each render because SceneViewportWidget may overwrite them.
- `Tools/collider_package_native.py` checks saved/staged scene identity, all seven lighting textures, native evidence,
  menu-image freshness and archive CRC/SHA256. Its current default is `collider-native-v2.zip`; it requires current
  saved-scene hashes in navigation, live-match, capture and lighting-review evidence. Separate-client and performance
  status are recorded independently, so stale evidence cannot imply successful validation of a new scene.
  `output/collider/current-build.json` points to the historical native-v2 archive; it does not contain finish-v1.
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

