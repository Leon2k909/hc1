## Lowtide (multiplayer map, `Tools/lowtide_map.py`)
- Structural materials installed (2026-10-18): `Sources/Lowtide/structure/material-status.json`.
  Both warehouse models use continuous generated timber with grain along each beam and
  weathered painted cast iron. The original generated 1254px albedo is retained unchanged;
  shallow numerical normals and dry roughness provide surface response. The uniformly
  rusted iron trial was rejected after daylight review. Eighteen matched review captures,
  six production views and six fresh-load views cover both banks, close beams/columns and
  exterior ironwork. The four existing-slot remaps preserve geometry, collision and the
  23 material slots per architecture model. `Tools/lowtide_structure.py` reproduces all
  twelve resources; the canonical map writer applies it only to east/west architecture.
  Column shaft normal checks pass on both banks. Warehouse indirect light was rebaked
  as v5; only six saved texture references changed, and the saved scene reloads correctly.
  Prior v4 provenance/textures are retained. Temporary review sources and raw bake outputs
  are archived outside Assets. The Orion edit tab and Lowtide runtime map were restored.
  Evidence is in `native-2026-10-18/structure-timber-v2`. Gameplay cost, temporal behavior,
  broader cargo/foliage quality and overall AAA acceptance remain open.
- Water reflection filter installed after static review (2026-10-18): read
  `Sources/Lowtide/water/filter-status.json`. Nine native screenshots cover the
  original one-mip capture and the current/filtered materials with the seven-mip
  linear HDR pyramid. The selected filter scale is 0.08, keeping the waves and
  shallow transparency while softening reflected architecture. Capture code
  hotloaded with zero errors, and the unused review model/material loaded without
  error. `lowtide_water.py` now preserves the selected shader/parameter; its writer
  and capture transformation reproduce the installed files. Geometry, collision,
  scene and original wave shader are unchanged. Ares stalled during loading after
  the first review, then recovered. Native production readback confirms the selected
  shader, and three fresh production captures were reviewed. Six editor checks pass:
  visible, outside bounds, below plane, return, disable and reenable. The camera/tab
  was restored and Ares play restarted. Six unused review files are archived outside
  Assets. A fixed-view performance sample failed its camera-angle guard; do not use
  its aggregate timings as Lowtide results. Gameplay cost, moving-camera temporal
  behavior and multiple-view checks remain pending. Evidence and scripts are in
  `native-2026-10-18/water-reflection`.
- Warehouse floors installed (2026-10-18): read `Sources/Lowtide/floor/floor-status.json`
  and `Sources/Lowtide/concrete/wear-status.json`. Both architecture models now select
  the worn pine and concrete-use materials through four existing-slot remaps. Native
  review covers 24 comparison images, six production views and six after the refreshed
  lighting bake. The opaque timber shader uses ordinary RGB mips because the unchanged
  1254px source atlas is incompatible with the engine's alpha-weighted mip filter.
  `Tools/lowtide_floor_surfaces.py` preserves all 18 installed resources byte for byte;
  map generation configures only the existing floorboards and concrete slots. Fresh
  `lowtide_material_stage.py --current --output output/lowtide/quality-pass/<new-folder>`
  reproduces all twenty installed files and verifies 286 collision footprints and twelve
  mezzanine triangles. No render geometry, material-slot count or collision changes.
  Both dressing models had corrupt compiled bounds; native full rebuilds restored finite
  bounds and visible east cargo without changing their OBJ/VMDL sources. Warehouse DDGI
  was then rebaked and saved as v4 (see lighting below). Evidence is under
  `native-2026-10-18/warehouse-floor-current`; use `promotion.json` for installed hashes,
  not the historical staging manifest. Orion play and the prior tab were restored.
  Gameplay cost, temporal filtering, dark structural materials and broader cargo quality
  remain open; these checks do not establish overall AAA quality.
- Structural material diagnostic (2026-10-18): `Sources/Lowtide/structure/response-status.json`.
  Nine lit comparisons tested a current standard shader with existing beam/iron textures,
  first preserving their values, then increasing timber tint and roughness. This recovers
  wood detail but exposes repeated plank seams on solid beams; columns still lose definition.
  Neither trial is installed. Six unbound source/meta files were retired from Assets; staged
  copies and evidence remain in `native-2026-10-18/structure-response`, with compiled caches
  left alone. The first `review/` images used stale DDGI and are invalid material evidence;
  use `review-lit/`. Individual long-grain beam faces and a close cast-iron audit are next.
  When swapping DDGI texture paths, reactivate the existing volumes before viewport review:
  valid loaded textures did not refresh the already-active editor volumes immediately.
  Fresh loading of the saved Lowtide scene then confirmed the v4 bake on both banks without
  reactivation; three loaded-scene views are in the floor pass's `lighting-persistence` folder.
  Play-state status can report a runtime map different from the underlying edit tab. Record
  both before stopping: this review restored the Orion tab and Riverdale runtime map separately.
- Paving contact installed (2026-10-18): `Sources/Lowtide/paving/use-status.json`.
  Native comparison covered close pipe outlets, a sunlit shed, both banks at player
  height and a street-distance view. Ten matched images plus two fresh production
  views are reviewed. Narrow settled grit and local moisture use the current 186
  paving triangles, 1,616 wall-foot segments and 16 outlets; 216 interior samples
  confirm that all 24 grate apertures remain clear in the data mask. Original stone
  colour/PBR pixels and relief remain intact. All three production material slots
  bind the new shader and 2048-square texture without overrides. No geometry,
  collision, scene files, material slots or model remaps change; one texture lookup
  is added. `lowtide_paving.py` preserves the extension on material regeneration.
  After geometry changes, stage a fresh mask with `lowtide_paving_use.py --current
  --output output/lowtide/quality-pass/<new-folder>`, then review/import through the
  editor. Current-layout reproduction matches all five installed files. Temporary
  review material is archived outside Assets. Belltower's edit tab was restored.
  Gameplay cost and temporal stability remain unmeasured. Historical offline notes
  below are superseded where this entry and the construction entry record installation.
- Current construction composition (2026-10-18): read
  `Sources/Lowtide/construction/recomposed-status.json`. The three window/door meshes
  and the connected drainpipe/gutter mesh are recomposed against the installed grates
  in `output/lowtide/quality-pass/native-2026-10-18/construction-recomposed`.
  Each scoped component first reconstructs its pinned historical result, then matches
  current corner positions, UVs and normals. All 12,336 grate triangles and both banks'
  92 paving triangles remain exact. Current material libraries include the grate slots.
  This composition is now installed: 20 matched native comparison images and five fresh
  production views were reviewed. All four compiled meshes match the reviewed geometry,
  indices and materials, and all 24 grates pass a fresh native readback. Canonical map/finish
  generation calls `Tools/lowtide_construction.py`; component reproduction preserves
  glass, thresholds and collision. The pass adds 287,048 source triangles and no material
  slots. Temporary review assets are archived outside Assets. Scene/VMDL/collision files
  are unchanged; Spillway's edit tab and the user's stopped play state were restored.
  Controlled gameplay performance and temporal stability remain pending: mixed-scene
  profiler samples are invalid. This does not establish overall AAA quality.
- Street grates (2026-10-18): native checks have resumed at the user's request. Read
  `Sources/Lowtide/drainage/grate-status.json`. All 24 flat-backed grates were replaced
  with beveled cast frames, open bars, lower supports and ten-inch recessed wells.
  Only eight original paving triangles were cut around the apertures; collision remains
  intact. `Tools/lowtide_grates.py` supplies geometry, generated cast-iron PBR materials
  and canonical paving cuts, called by `lowtide_finish.py` and `lowtide_map.py`.
  The 15 imported files add 8,756 source triangles and two finish material slots.
  Native model readback verifies all 24 slots, bars and cleared paving openings.
  A full native compile was necessary for the west model: its incremental compile reported
  success while retaining the old paving. The full compile finished after the CLI timeout;
  inspect actual output/readback before retrying. Four native views now verify both sizes,
  both banks, sun/shade and player height; all 24 native floor traces retain support at z=0.
  Native code compilation has zero errors. Lowtide's camera was restored and Spillway play
  started as requested; the Veridant tab was left open without edits by this pass. Gameplay cost is unmeasured.
  See `native-2026-10-18/grates/review` for the reviewed captures. The existing
  `native-2026-10-18/grate-before.png` shows Spillway and is not grate evidence.
  Historical finish and east/west OBJ stages now predate these grates/holes: recompose
  their scoped faces against current models; do not overwrite these changes with snapshots.
- Current checkout/offline rebase (2026-10-18): use `C:\sbox-projects\hc1\forked-shooter-main`.
  The former D: checkout is now a compatibility junction. Read
  `Sources/Lowtide/construction/checkout-status.json` before using the historical candidates below.
  Four candidate sets were rebuilt under `output/lowtide/quality-pass/rebase-2026-10-18`: the close
  sacks, sack distance alternatives, paving contact and `water-filter-gentle`. All 264 sack shapes/placements match the reviewed
  components, with 742,742 unrelated triangles retained in the current base models. Paving preserves
  the current rotated wetness function; its mask, material and metadata reproduce the earlier layout.
  Water preserves the newer wave/shoreline shader and allocation-saving capture changes. Its filter
  scale is 0.08 at the current 0.22 base roughness; 0.35 blurred the synthetic fixture excessively.
  The isolated capture build passes with no warnings/errors; all four water files reproduce exactly.
  Six current CPU views per material pass were reviewed. 566 protected live files are unchanged.
  The six distance meshes reuse the exact reviewed components with current material libraries. All
  528 reduced bodies pass geometry checks, preserving 742,742 unrelated triangles per detail level.
  The complete prop batches total 1,157,222 / 958,694 / 818,774 triangles across the three levels;
  that is a 17.2% / 29.2% aggregate reduction, not a frame-time result. The original component previews
  remain applicable to those identical shapes/pixels; native switching and grouping are not configured.
  Sacks remain uninstalled. Water has since been installed after native static review,
  with runtime verification pending as recorded above. Paving contact has been rebuilt and
  accepted natively against the installed construction (see above). Native checks resumed
  at the user's request; recheck current hashes before integrating stages. The other historical bundles
  still need current-source integration checks; native appearance, temporal behavior,
  gameplay cost and persistence remain unverified. The old master-check result is historical evidence.
- Offline water reflection filtering (2026-10-15): `Sources/Lowtide/water/filter-status.json`
  records a separate candidate for the one-mip, level-zero planar reflection path. A bounded
  seven-mip linear HDR Box pyramid supplies roughness/UV-footprint filtering. The reviewed scale
  is 0.35; the first full-strength trial blurred away too much reflected architecture. Existing
  capture lifecycle, camera guards, waves and optics are preserved. Four staged files reproduce
  byte for byte and 560 protected live files are unchanged. Isolated C# API compilation passes
  with no warnings/errors; it is not a sandbox/native shader compile or an engine hotload.
  Six synthetic CPU fixture views are reviewed, not screenshots or map-quality acceptance.
  The 960x540 colour target gains 1,380,960 bytes and up to six downsample passes; actual GPU cost
  is unmeasured. Native appearance, temporal stability, lifecycle, shader compilation and canonical
  integration were pending in this historical stage; the current installed entry supersedes it. Stage keys include Assets/ and Code/; apply the
  scoped capture diff after fresh before-hash checks, never overwrite later code from its snapshot.
- Offline paving contact (2026-10-15): `Sources/Lowtide/paving/use-status.json` records
  a separate material candidate with narrow settled grit at saved wall feet and local moisture
  near 16 drain outlets. Original stone colour/PBR pixels and nine-millimetre relief are unchanged.
  One numerical 2048-square RGB mask adds one texture lookup; no geometry, collision, model remaps
  or material slots change. All five staged files reproduce byte for byte, 557 protected live files
  are unchanged, and 12,000 atlas samples, 228 excluded-surface cases and 4,692 moisture texels pass.
  Six matched CPU context views have been inspected. Native shader compilation, appearance,
  filtering, cost, canonical integration and persistence were pending in this historical stage; see the current installed entry.
  Use `output/lowtide/quality-pass/paving-use/stage` for later scoped review; its moisture positions
  reference the composed drainage junction candidate. This does not establish overall AAA quality.
  A separate 98-material / 41-PNG repeated-border audit found no further confirmed padding defect:
  the bridge decking and distant shipyard have bounded UVs; the known drain fix is now installed.
- Offline drainage junction repair (2026-10-15): `Sources/Lowtide/drainage/junction-status.json`
  supersedes the isolated drain geometry stage below. Context views exposed warehouse hoppers
  embedded in the cornice and shed gutters crossing hopper mouths. The composed candidate has
  20 warehouse pipe offsets/scuppers, 16 lowered shed receivers, eight pierced gutters moved
  beyond the coping, and folded roof aprons with supporting wall brackets. The shared material
  mapping correction is unchanged. Only `lowtide_finish.obj` changes: +111,936 triangles against
  live production, including +16,432 beyond the earlier drain candidate; no new material slots.
  Geometry reconstruction/reproduction, checked closed shells, 488 exterior rain-path rays and
  20,272 clearance samples against the saved east/west architecture pass. The sampled minimum
  upper pipe/hopper clearance is 0.671 inches; the grid is not an exhaustive intersection proof.
  Eight clipped CPU context views use neutral architecture and matching corrected metal on both
  versions. All 556 protected live files remain unchanged. Native appearance, shader compilation,
  geometry/shadow cost, canonical integration and persistence were pending at staging; see the current construction entry for installed checks.
  Use `output/lowtide/quality-pass/drain-junctions/stage` for later native review; copying the older
  drain-only OBJ over it restores the junction defects. No overall AAA acceptance is claimed.
- Offline drainage construction and material mapping (2026-10-15): read
  `Sources/Lowtide/drainage/construction-status.json`. The candidate replaces 36 capped/blocky
  drains with curved hollow outlets, tapered open hoppers, socket profiles and wall fixings.
  It adds 95,504 triangles to `lowtide_finish`; the other 71,642 triangles remain unchanged.
  Close CPU previews exposed a separate material defect: the two drain materials sampled the
  padded borders of the 2048-square steel atlas. The staged shader limits repeats to the original
  1254-square source at its authored 24-inch scale, preserving all colour/normal pixels. It also
  corrects those shared slots on gutters, grates and anchors, independently of the geometry.
  Six comparison sheets separate the mapping fix from the shape change. Manifold, aperture,
  source-pixel, reconstruction and reproduction checks pass; 556 protected live files are unchanged.
  Native shader compilation, map roof/gutter connections, distance appearance and geometry/shadow
  cost remain unverified. No canonical hook, live promotion or overall quality acceptance is applied.
  Keep the user's offline restriction; use `Tools/lowtide_drain_construction.py` and
  `Tools/lowtide_drain_review.py` for this separate candidate.
- Offline sack detail candidates (2026-10-15): `Sources/Lowtide/sacks/lod-status.json` records
  818- and 288-triangle alternatives to the unchanged 1,570-triangle close sack. They retain the
  close body's positions, UVs and normals, with extra samples around its pinched corners. The
  medium mesh retains simplified closed seam shells to preserve their visible lines.
  All 528 exported reduced bodies are closed; nine CPU comparison sheets cover 320/160/80-pixel
  features and approximate mip filtering. Six staged model alternatives include their unchanged
  material libraries. These are geometry candidates, not configured native LODs or FPS results:
  the dressing/fleet models aggregate many props, so grouping, transitions and budgets still need
  native review. `Tools/lowtide_sack_lods.py` changes no live assets or canonical generator.
- Offline sewn cargo sacks (2026-10-15): read `Sources/Lowtide/sacks/construction-status.json`.
  The separate candidate in `Tools/lowtide_sack_construction.py` replaces 264 rounded-block sacks
  with pinched sewn ends, a side hem, local gathers and finer continuous cloth UVs. Existing jute
  pixels, cover bounds, collision, materials, placements and unrelated prop faces remain intact.
  All exported bodies/thread shells are closed with valid normals/UVs; three components reproduce
  byte for byte. Six matched CPU views are in `output/lowtide/quality-pass/sack-construction/final-preview`.
  The preview's local shadow adapter fixes a half-pixel depth mismatch; sloped-plane checks verify it.
  These three dressing/fleet OBJ copies do not overlap the other construction/material candidates.
  They add 382,800 triangles: native appearance, textile filtering and measured gameplay cost remain
  open, including whether distance reduction or instancing is required. No live import or canonical
  generator change is applied. Native acceptance is still required before installation.
- Offline warehouse concrete use (2026-10-15): read `Sources/Lowtide/concrete/wear-status.json`.
  `Tools/lowtide_concrete_wear.py` stages collision-aware dust, short rubber deposits and traffic
  polishing for both ground floors. Twelve layout routes avoid the saved cargo/column footprints;
  colour images, geometry, collision and live resources remain unchanged. The v2 mask replaces
  the first review's continuous tire lines. Checks cover 3,474 route samples, 8,192 atlas samples,
  36 excluded-surface cases and 32 untouched floor cases. Eight files reproduce byte for byte,
  with 561 protected live files unchanged. The six CPU material views and two layout diagrams
  have been reviewed; this modest candidate still needs native shader, lighting, filtering and
  performance checks. `Tools/lowtide_material_stage.py` combines it with the timber floor in
  `output/lowtide/quality-pass/material-integration/manifest.json`: 20 files, four existing-slot
  remaps across two models. Independent VMDL copies overwrite each other; apply only the four
  remaps after native acceptance, preserving later model/LOD edits. Canonical generation and
  a refreshed warehouse DDGI bake were pending at staging. The 2026-10-18 installed entry supersedes these limitations; gameplay cost and temporal checks remain open.
- Offline warehouse floor (2026-10-15): read `Sources/Lowtide/floor/floor-status.json`.
  `Tools/lowtide_warehouse_floor.py` stages a separate worn pine material for both mezzanines.
  Eight generated board scans remain unchanged; 25.4 cm boards run across the joists, with
  staggered ends and small nails on their 110-inch grid. Shallow grain normals, dry roughness,
  filtered joints and a muted tint replace the domestic-looking floor finish. The candidate
  remaps only the existing floorboards slot: no added triangles, collision or scene changes.
  Six matched CPU views, 100,000 layout samples, UV-derivative/mirror checks and 14 byte-identical
  regenerated files pass; 560 protected live files are unchanged. This is an offline candidate,
  not a native compilation or performance result. The staged VMDLs are review snapshots; after
  native acceptance apply only their material remap, preserving any later LOD/material changes.
  The canonical interior generator and warehouse DDGI bake still need integration after acceptance.
  The 2026-10-18 installed entry supersedes this historical staging state. The overall visual goal remains open.
- Offline construction detail levels (2026-10-15): Tools/lowtide_construction_lods.py prepares
  two geometry alternatives for the combined window/door candidate without altering the close
  version or live resources. The three affected models total 500,413 triangles at close detail,
  411,421 at level 1 and 381,861 at level 2 (17.8% and 23.7% less geometry). All unrelated triangle
  attributes are retained. Six component reproductions, 7,155 coverage/joint/clearance rays and
  556 protected live-file hashes pass. Eighteen matched CPU views cover 300/160/80-pixel features.
  Read Sources/Lowtide/construction/lod-status.json: these are profiling candidates, not configured
  native LODs. ModelDoc switches, temporal appearance and gameplay cost remain unverified. The
  warehouse halves are large aggregate models, so per-feature review sizes cannot be translated
  blindly into one distance threshold. Profile full detail before choosing switching/grouping.
- Offline combined construction set (2026-10-15): read Sources/Lowtide/construction/offline-status.json.
  Tools/lowtide_door_construction.py stages bevelled boards, tapered straps, fixed hinge brackets,
  pull handles and an open hasp staple for twelve closed door pairs on the four nearby sheds.
  Generated green/red colour pixels are unchanged; explicit UVs fit complete boards to the geometry.
  The doors add 39,988 triangles and no material slots. Exported coverage/clearance rays (18,568),
  two byte-identical regenerations and 556 protected live-file hashes pass. Exact face replacement
  preserves all other attributes, upper doors, open passages, thresholds, collision and scene data.
  CPU before/after views are offline construction previews; native compilation/visual/performance
  checks have not run. Sources/Lowtide/doors/construction-status.json records the evidence.
  The door and window candidates both change the east/west OBJ files. Do not copy both independent
  stages over each other: Tools/lowtide_construction_stage.py composes them into one verified set
  under output/lowtide/quality-pass/construction-integration (175,112 extra triangles overall).
  No canonical writer hook or live promotion is applied. Keep the user's offline restriction;
  native review and the separate foliage persistence work remain pending.
- Rejected offline brick relief (2026-10-15): Sources/Lowtide/brick/relief-status.json records the
  fitted-mortar-v4 experiment. Even with denser tracing, grazing views stretch bright mortar edges
  and rare first intersections are missed by up to 7.65 mm. Do not import it. Production brick,
  colour images and weathering remain intact; the research and comparisons are retained in output.
- Offline window construction candidate (2026-10-15): Tools/lowtide_window_construction.py stages
  bevelled cast frames for 380 lower windows and missing curved heads for 586 upper windows.
  Three OBJ candidates add 135,124 visual triangles with no new material slots. Panes, room UVs,
  masonry, model definitions, collision and scene remain unchanged; 556 protected files, 9,440
  coverage/clearance rays and three byte-identical regenerations pass. CPU before/after views are
  construction previews, not native engine captures. Blender stalled before the scripts ran; the
  owned attempts were stopped. No production import or canonical map-writer hook is applied yet.
  Read Sources/Lowtide/windows/construction-status.json before resuming. The user requested offline
  work; native visual/performance review and foliage persistence are deferred, not completed.
- Container surface (2026-10-14): the six production materials now use `hc1_lowtide_container.shader`
  for enamel roughness, base dirt, seam runoff and sparse oxide. Existing generated paint textures,
  UVs, geometry, collision, scene and lighting are unchanged. The canonical container generator
  emits the shader/materials; all 22 generated shader/material/texture files match production byte
  for byte. Six material compilations, eight loaded slots and four reviewed production views pass;
  536 protected files match. Camera and prior tab are restored, with no new native errors.
  Evidence: `output/lowtide/quality-pass/container-surface/verification.json` and
  `Sources/Lowtide/containers/surface-status.json`. The candidate import completed after the stall;
  do not rerun it. This is a modest finish improvement, not completion of the overall AAA target.
- Container construction (2026-10-14): `Tools/lowtide_container_detail.py` is called by the canonical
  container builder. Four containers now have rounded sheet folds, bevelled frame/locking brackets
  and 32 hollow corner castings. Roof/underplate corners stop around all 96 lifting apertures.
  Exact face replacement preserves 322,708 unrelated triangles per dressing half. The two meshes
  add 41,024 visual triangles overall; current material sources, all collision/model definitions,
  scene and 526 protected files are unchanged. Native compilation/loading and four viewport views
  pass. Exported-geometry rays confirm all 96 apertures; canonical collision regeneration matches.
  Evidence: `output/lowtide/quality-pass/container-detail/verification.json`. The before/after manifests
  supersede older whole-dressing-file hashes intentionally. Broad paint response and gameplay
  performance are still open; the scene is not at the full AAA target.
  For tab-sensitive QA, `capture-container-final.cs` activates the existing Lowtide session, captures
  with play/state guards, and restores the camera and prior tab within one native call. This avoids
  a scene-tab change between separate calls. It creates no temporary scene or offscreen renderer.
- Paving relief (2026-10-14): `Tools/lowtide_paving_relief.py` produces numerical height,
  normals and joint AO at nine-millimetre depth, retaining the existing generated granite colour,
  roughness and atlas mapping. The candidate shader limits parallax by distance and pixel footprint.
  It is installed in the production `lt_setts.vmat`. Native compile and four loaded 2048px bindings
  pass; four actual-material viewport views are accepted. The 54 protected sources are unchanged.
  Evidence is `paving-relief-production-verification.json` in the quality-pass folder. Read
  `output/lowtide/quality-pass/paving-relief-pending.json` before proceeding. The built-in generated
  `Sources/Lowtide/visual-target/quay-target.png` and its prompt are art references only.
- Footbridge UV repair (2026-10-14): `Tools/lowtide_bridge.py` now compensates for the OBJ import's
  V flip when selecting scanned board rows. The installed Fleet OBJ changes only 320 existing UV
  records across 80 boards; 198 previous coordinates sampled edge padding and stretched the wood.
  Vertices, normals, faces, other UVs, collision and generated texture images are retained. Native
  model/material loading and compile passed during play without stopping it. Final walk and wide
  viewport views are accepted, with 47 protected files unchanged. Evidence:
  `output/lowtide/quality-pass/bridge-uv-*`; inspect the pending record before reapplying anything.
  `SceneViewWidget.Session` redirects to GameSession during play, so ordinary editor-camera tools
  can target the runtime camera. Keep existing-viewport capture guarded against play mode.
- Shed weathering (2026-10-14): `Tools/lowtide_shed_weathering.py` reads the actual shed facade
  openings and bakes a separate 2048px contact/runoff/lime mask: 16 mirrored elevations and 32 sills.
  `hc1_brick.shader` applies it only at the four sheds' exterior wall bounds/normals; four brick/stone
  materials bind it. Brick, masonry and facade generators preserve these inputs. All eight staged
  files survived the interrupted reload; 46 protected geometry/scene/roof/source files are unchanged.
  After restart, four native material recompiles, loaded texture/strength checks and three normal
  viewport views passed with no fresh errors. Scene and camera are preserved. Evidence:
  `output/lowtide/quality-pass/shed-weathering-*`. The change is deliberately modest; broader finish
  and controlled gameplay performance remain open. Do not move a loaded shader's compiled cache:
  the earlier cache move caused missing-resource reload errors even though shader compilation passed.
- Slate response (2026-10-14): roofs now use `hc1_slate.shader`, a charcoal tint [.40,.44,.48],
  broad runoff variation aligned to the roof pitch, stronger split-stone normals and shallow joint AO.
  `Tools/lowtide_roofs.py` reproduces the material/maps. The existing generated colour image and
  roughness map are unchanged; no model, collision, scene or lighting-bake change. Six installed files
  and 45 protected source files pass the scoped checker. Native shader/material compilation, all
  three 2048px bindings and five existing-viewport views pass; scene and camera state are preserved.
  Evidence: `output/lowtide/quality-pass/roof-response-*`, `check-roof-response.py`.
  New shaders require `EditorUtility.CompileShader` before material compilation; asset Compile alone
  does not create the shader combo. Gameplay performance, facade repetition and overall finish remain open.
- Editor water rendering (2026-10-14): `LowtideWaterReflections` now registers editor reflection
  commands on `Scene.Camera`, while retaining the viewport camera for reflection projection and
  water exclusion. Engine `InitializeRendering` copies the main camera's render hooks onto editor
  views; attaching only to the viewport camera hid the water without executing its replacement draw.
  Game cameras retain their original registration route. Multiple perspective editor cameras fall
  back to regular cubemap water to avoid duplicate draws through their shared hook. Native compile
  and eight lifecycle assertions passed; overview, bank and quay captures are `water-*-fixed.png`
  in quality-pass. Scene/play/camera state was preserved, with no new engine errors. This verifies
  editor rendering, not a fresh gameplay or performance run. No water shader/material change.
- Shed gables and ridges (2026-10-14): `Tools/lowtide_shed_details.py`, called by finish, adds eight
  louvred circular vents with individual chamfered radial bricks and four formed metal ridge caps
  with lap joints. It appends 14,784 visual triangles to Harbour Details, retaining all 71,946 prior
  triangles, scene data, collision, other model sources and materials. Native compile, 384 vent
  backing coverage samples and five existing-viewport views passed without console errors.
  Evidence: `output/lowtide/quality-pass/shed-details-*`; finish is now 86,730 triangles.
  A thin slate-course mesh was tried and rejected for ground-level aliasing, then removed from the
  assets and canonical generator. `roof-*-after`, `roof-*-final` and `roof-relief-*` captures are
  rejected experiments, not current verification. The original roof texture/panels are retained.
  The rejected generator is archived only in output; do not reapply it. Older perimeter whole-file
  hash reports predate this intentional additive pass. Broad roof material response, facade
  variation, composition and controlled gameplay performance still need work.
- Perimeter building closures (2026-10-14): `Tools/lowtide_perimeter.py` closes 42 omitted wall
  sections in the mirrored background blocks and northern row. The two exposed quay ends have
  30 sealed windows, masonry sills, cornices and loft vents. Finish calls this module on regeneration.
  The scoped import appends 10,634 visual triangles to Harbour Details; all 61,312 existing finish
  triangles, collision, other model sources and scene data are preserved. Native model compilation,
  material checks, 2,300 facade coverage samples and normal viewport views passed; east/west quay
  and northern roof corners no longer expose the missing building walls. The scene stays clean and
  the user's camera is restored. Evidence: `output/lowtide/quality-pass/perimeter-*`.
  Earlier strict whole-file geometry reports are historical baselines: tidal seam and perimeter
  manifests record the later intentional changes. They do not certify the current hashes or a new
  lighting bake. Architectural variation and controlled gameplay performance remain outstanding.
- Canal surface weathering (2026-10-14): `Sources/Lowtide/visual-target/canal-biofilm-source.png`
  is the unchanged built-in imagegen albedo, with full prompt beside it. Six masonry materials bind
  it through `hc1_brick.shader`; world-space exterior/height masks exclude indoor walls and floors.
  Brick/masonry generators preserve these inputs; finish shares masonry's granite definition.
  The final `g_flTidalClay` adjustment to the old straight tide boundary compiled after restart;
  six materials recompiled and resolve the generated 1254-square texture. Overview, east-close and
  west-close captures (`live-*-biofilm-final`, `live-biofilm-*-final`) verify the exterior blend.
  The first interior regression capture is invalid (black): render-target ResourceSystem.RegisterWeak
  errors began during that capture,
  before the later failed offscreen benchmark and editor exit. Use the normal editor viewport for
  further checks; do not repeat the temporary-scene capture/benchmark loop. The replacement normal
  viewport interior capture passed with no fresh global errors; controlled game performance remains
  pending. A subsequent scoped mesh repair removes the raised tidal strip/cap: twelve vertex moves,
  four UV adjustments and four cap triangles removed, with all other geometry/collision/scene data
  preserved. All three meshes compiled; native east and west viewport views show the bright seam
  gone. The wall generator matches the repaired geometry and UVs. Evidence is tracked separately in
  `output/lowtide/quality-pass/tidal-seam-*`. The user's saved scene and camera were preserved.
  Native compilation success alone is insufficient:
  inspect texture bindings, rendered pixels and fresh global console errors too.
- Static shadow caching (2026-10-14): `Tools/lowtide_static.py` marks nine named fixed world meshes
  and 24 local lamp objects static (native flag 32768). Finish/marine/masonry scene patches preserve it.
  Glass, water, trees, gameplay objects and the weather-controlled sun remain dynamic. Native reload
  confirmed static render-object flags; an isolated moving-caster test confirmed shadows move while
  the same static cache is reused. Only 33 scene Flags fields changed; no measured game-FPS claim yet.
- Warehouse lighting update (rebaked 2026-10-18): `lowtide_finish.apply_scene` calls `Tools/lowtide_lighting.py` to
  preserve the native bake in `Sources/Lowtide/lighting/warehouse-lighting.json`. Eighteen warehouse points
  remain disabled; downward shadowed spots use 55/30 degree cones and 85% original colour. Two DDGI volumes
  cover floor, walls and ceiling, with 1200 probes each, intensity4, contrast.85 and blend24. Keep their six
  native `.vtex_c` files in `lowtide_scene_data/ddgi/warehouse-{east,west}-v5`; `.gitignore` narrowly exempts
  these from the compiled-file rule and existing LFS rules cover them. The native public
  `IndirectLightVolume.BakeProbes` method refreshed both volumes after the accepted floor/structure
  materials and dressing cache repair; six fresh-load viewport views and stored-texture copies pass.
  This v5 save changed only six texture references. The previous v4 save's collider/default and
  resource/prefab serialization is retained. Generator lighting application
  is idempotent against the saved scene. `bake-provenance.json` records the inputs and evidence;
  v3/v4 provenance and textures remain available. Re-bake after static geometry, material, fixture or
  daylight changes. Sun/sky/exposure/outdoor lights are unchanged. Controlled gameplay performance
  and the overall visual-quality goal remain open.
- The user asked for a new map and left the theme to Claude (2026-10-05). Lowtide is the warehouse quarter of a made-up
  North German port at low tide, after Hamburg's Speicherstadt. Six-storey red-brick warehouses stand straight up out of
  a tidal canal (a Fleet), with stepped gables, winch oriels under copper hoods, and loading doors up their fronts. The
  tide is out, so the Fleet's bed is mud with a channel of water down its middle.
- One script, built like Railhead's with `map_kit`, writes:
  - the models, to `Assets/models/maps/lowtide/`:
    - the Fleet: its bed, the bridges and the barge;
    - the east half, and its mirror the west half, repainted by `WEST_PAINTS` (sooty brick, cream frames, red doors);
    - the dressing, built in place for each side so number plates read the right way round;
    - the glass, the water, and the backdrop: the Fleet running on north under a building, the harbour, its far shore
      and a tug;
  - the scene, `Assets/scenes/maps/Lowtide/lowtide.scene`, rewritten whole on every run (change the layout in the
    script, not in the editor);
  - the `lt_` materials, `Assets/materials/lowtide/*.vmat`. They're text only:
    - tinted copies of the project's own materials (`LT_MATERIALS`: sooty, glazed and slimed brick, wet mud, the
      water, painted doors, jute, tarred timber, steel grating);
    - flat paints (`LT_PAINTED`).
    So the map needs no new pictures;
  - the radar picture, `ui/minimaps/minimap_lowtide.png` (the folder is `ui/Minimaps` on disk);
  - with `--art`, a stand-in menu picture, `ui/maps/lowtide.png`.
- Levels:
  - The streets and quays are at z 0.
  - The Fleet's mud is 128 below them at its walls, under the 156 drop that hurts, with level flats at -130 along both
    walls.
  - Its channel's bottom is at -146, with water at -137 (`BED_PROFILE`), and the bed falls away into the harbour at its
    mouth.
- Layout: mirrored across e 0, the Fleet's middle. Red Team spawns on the west square, Blue Team on the east one. The
  play is e -2200..2200, n -1650..1450.
  - North: the street in front of the north row, over the Fleet on a riveted plate-girder bridge with cast-iron lattice
    railings and a lamp on each end post.
  - Middle: the two warehouses (east e 240..1000, n -400..1150).
    - Each is open on its ground floor, a whitewashed hall of cast-iron columns, and on a mezzanine over its north half
      (z 176), reached by a timber stair up the east wall.
    - The columns and beams (2026-10-12, the user: "this beam needs improvement", of a column built from a box, a
      12-sided shaft, a band and a square cap):
      - Each column is a Speicherstadt cast-iron one (`iron_column`, `lathe`): a chamfered base plate, a moulded base
        (torus, cove and astragal), a shaft tapering 6 to 5 in radius, a neck ring, a bell capital and a cap plate
        bolted to the timber above. Those on the mezzanine are slighter (5.2 to 4.4).
      - They stand in two rows at e 500 and 740, n -120, 130, 396, 630 and 880 (the middle row was at 380, under the
        mezzanine's edge).
      - Each row carries a 16-inch square timber girder (`girder`, `GIRDER_W`) on a bolster with rounded ends
        (`bolster`, a Sattelholz): under the ceiling's joists (z 324-340) the whole length, and under the mezzanine's
        (z 132-148) from its edge north.
      - About 1,600 triangles a column. Its collision is two boxes and three hulls; the bolts have none.
      - Checked in offscreen renders in the editor (the base, the capital, the mezzanine), not in a match.
    - Two ground-floor loading bays onto the Fleet have steel landings with stairs down into it. Two mezzanine bays look
      over it, with a 37-high bar across each, which you can vault.
    - Bomb site A is the east warehouse's ground floor under the mezzanine.
    - Between the warehouses is the Fleet's bed, with a steel lighter (a Schute) lying on the mud. Its sides are 70-82
      over the mud and 70 over its hold's floor, so you can mantle in and out.
    - The hold (2026-10-12, the user: "textures glitching on lowtide"):
      - Its floor was at -137, level with the channel's water plane, which runs on under the hull, so the two
        flickered through each other. It's now 3 higher (`WATER_Z + 3`), and the cargo with it.
      - Its plate was `rw_wagon_rust`, a freight wagon's side, whose overpainted panels showed as dark blocks. It's
        `lt_hold_rust` now, Boxyard's `bx_rust` darkened and tiling at its real size (`lt_tile`: 48).
      - The green patch was an opaque `lt_water` puddle, which came out.
      - Only `lowtide_fleet` was regenerated. Not yet seen in the engine.
  - South: the yards, each with a brick shed, and the harbour quay, crossed over the Fleet's mouth on a pony-truss
    footbridge. Two level-luffing cranes stand on each quay, with a 200-high portal you can walk under. Bomb site B is on
    the east quay, among the cargo under a crane.
  - A cross street each side runs from the north street to the quay, past the spawn square.
  - The alley beside each quay shed (e ±1950..2200, n -1050..-600) is closed off from the quay by a yard wall
    (`alley_wall`, `ALLEY_WALL`, 2026-10-12; the user: "you shouldnt be able to go this way"). It's 132 high, too high to
    mantle, with a shut pair of gates, a granite coping and a player clip over it. The way from the spawn square to the
    quay is the cross street. Not yet seen in-game.
  - A shut door at a wall's foot has a stone threshold in its recess (`leaves_shut`). The recess had no floor, so a pale
    strip of sky showed in front of the doors (the user's screenshots, 2026-10-12). Not yet seen in-game.
  - The granite plinth, the glazed brick bands at each floor and the cornice turn round a building's outside corners
    (2026-10-12; the user's screenshot of the plinth stopping short of one: "this looks weird").
    - A building's side walls (±e) run between its end walls (±n). Their mouldings stopped at the end walls' backs, 20
      short of the corner, so bare brick and the plinth's cut end showed there.
    - Now a side wall's plinth, bands and cornice band carry on past its run by the wall's thickness plus their own
      depth, filling the corner square (`corner_reach`).
    - The coping meets the end wall's, where it overlapped it on one side and left a notch on the other.
    - `block` works out a building's corners from the fronts it draws (`corners`), and `speicher` passes the
      warehouses' own.
    - Only `lowtide_east` and `lowtide_west` were rebuilt (876 vertices moved in each; collision unchanged). Not yet
      seen in-game.
  - Six stairs go down into the Fleet: one from each warehouse ground bay, and a public one from each quay. Iron
    ladders on its walls are dressing only.
  - Those stairs are open steel stairs (`steel_stair`, 2026-10-13; the user's screenshot from the Fleet's bed: "issue
    behind stairs on lowtide").
    - They were boxes with no back or bottom faces, so from behind or below only the treads' tops showed, floating.
      Their hull was solid down to the mud, an invisible wall behind and under them.
    - Now each has two channel stringers from the landing to the mud, and grating treads with steel nosings. Every
      face is drawn, and the handrail runs on the outer stringer.
    - The collision is only the ramp under the nosings, so you can walk under a stair.
    - Only `lowtide_east` and `lowtide_west` were rebuilt: only the stairs' grating, steel and rails changed. The spot,
      reach and Retakes sight checks passed. Checked in offline renders of the OBJ from behind, below and the side,
      not yet seen in-game.
  - Mooring rings (2026-10-13, the user: "what is this trash on lowtide", of a black T on the Fleet's wall). Each was
    two black boxes, every 230 along both walls. Now it's a ring as on Hamburg's Fleet walls (`mooring_ring`,
    `MOORING_RINGS`):
    - a granite ring stone set into the brick, 20 wide and 17 high, proud by 1.2 with bevelled edges. Its UVs map one
      joint-free block of ashlar_grey's picture (`RING_STONE_PX`), so it reads as one stone;
    - an eye bolt leaded into it, and a rusted wrought-iron ring (`lt_hold_rust`, 11 across) hanging from the eye,
      its foot resting against the stone.
    - Eight to a wall, clear of the ladders, the footbridge, the quay stairs and the bays' landings. Drawn only, with no
      collision, about 570 triangles each.
    - Only `lowtide_fleet` was rebuilt. Checked in an offline render of the generated mesh, not yet in the engine.
- Modes:
  - The scene lists TDM and Defuse, and the map is in `GameUtils`' three lists.
  - It has deathmatch spawns and Retakes spawns for each site.
  - Domination's flags: A in the west warehouse, B in the Fleet's channel, C in the east warehouse.
  - The Hot Zones and the Cash Grab points are `ObjectiveSpot`s.
- Every run checks all 91 spots with railhead_map's `check_spots`, `check_reach` and `check_retakes_sight`. The last two
  now take another map's bounds and Retakes table. On 2026-10-05 all three passed.
- The navmesh's bounds stop at `NAV_TOP` (300): over the mezzanines and under the warehouses' ceilings (352), above
  which they're closed. The window panes' model is tagged `navskip`.
- `map_kit` gained two things:
  - `asset_file` finds an asset's file whatever its case. On Linux the scene's `scenes/maps/defusemap_01/game_setup.prefab`
    is `DefuseMap_01/Game_setup.prefab`.
  - A wall's arch skips a side painted None.
- Made offline on 2026-10-05 and checked in software renders of the models with their textures, the reach grid and the
  radar picture. It hasn't been opened in the editor: nothing has compiled, and the lighting, the navmesh, bots and the
  modes' objects are all unchecked.
- The radar and menu pictures are PNGs, kept in Git LFS, which this session couldn't push. Run
  `python Tools/lowtide_map.py --art` once to write them.
- To play it: `dev_mode team_deathmatch lowtide`.

