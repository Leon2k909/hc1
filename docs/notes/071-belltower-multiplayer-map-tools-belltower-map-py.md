## Belltower (multiplayer map, `Tools/belltower_map.py`)
- Northern plaza lamp placement (2026-10-27): the two lamps at plan `(±420,330)` now stand beside the arcade's
  solid outer piers at `(±420,520)`, clearing the square-to-arcade walkway. Only their render positions and four
  base/shaft collision hulls move; the map generator retains the new placement. Both town models compile, and
  native traces confirm the old sites are clear and new sites solid. `belltower_move_square_lamps.py`,
  `belltower_check_lamp_placement.py` and `Sources/Belltower/props/lamp-placement-v1.json` record the scoped migration.
- Current checkout checkpoint (2026-10-18): work in `C:\sbox-projects\hc1\forked-shooter-main`.
  The live town models include the `firewood-v2` integration, not just garden v3; its six model files and twelve
  material/texture files match the staged sources. Native firewood views are in `firewood-production-v1-saved/`.
  The installed landscape is `parcel-v4`, with 1,600 near trees and 88 compiled woodland sectors. Its 264 model
  source files, 18 published files/backups, scene groups and regeneration caches have been checked in this checkout.
  `Tools/belltower_finalize_parcel.py --check-only` checks these inputs without writing; its normal mode refreshes
  metadata only after validation. It preserves the newer `map_daylight.apply_profile` sky/fog settings and rejects
  other scene drift. `parcel-v4-production/verification.json` records the exact scene hash and validation scope.
  The old v8 visual verification and old landscape hashes no longer describe parcel v4. Current fixed-exposure native
  baselines are in `forest-coverage-v1-native-fixed-baseline/`; they expose noisy distant woodland. Gameplay performance and the
  overall visual target remain unverified. Earlier milestones below are historical; do not restore
  their models or landscape over these newer files. `oct18-current/current-installed-assets.json` records this check.
- Offline ground-edge trial (2026-10-18): `Tools/belltower_ground_edges.py` stages a separate, unreferenced
  `ground-edge-v1` model/material set. The original built-in ImageGen `ground-edge-v2.png` and edit prompt are in
  `Sources/Belltower/generated/`; the broad first atlas, meshes and studio views remain in
  `ground-edge-v1-first-atlas/`. The thinner atlas puts its dense back edge toward the wall. UV selection omits
  isolated specks between atlas cells without editing source pixels or alpha. There are 58 pockets per half,
  232 triangles total and one shared material, with no collision. Placement derives from the existing house
  fronts and requires a whole quad on one flat paving rectangle, clear of plinths and 12-inch-expanded shop/door gaps.
  `belltower_check_ground_edges.py` independently checks exported OBJ data, UV proportions, exact mirroring and
  deliberately invalid doorway/wall fixtures. Its report is `ground-edge-v1/geometry-checks.json`.
  Matched wide and close Blender views are in `ground-edge-v1-studio/`; they are construction renders, not engine
  captures. The preview opt-in reads original RGBA alpha directly, and the studio paving accounts for the native
  stone shader's UV scale. `Sources/Belltower/ground-edges/trial-v1.json` records the review and remaining work.
  Nine versioned files have now passed the guarded native import; the shader, material and both models compiled.
  They remain unreferenced by the saved scene. The clear native close comparison is in
  `ground-edge-v1-native-visible-{baseline,candidate}/ground-edge-close.png`. Its thin shaded deposit follows the
  plinth with broken alpha edges, and both temporary renderers were removed with original object identities restored.
  The first wider shots were obstructed by a market stand and a wall; they remain invalid. The corrected contextual
  pair is now in `ground-edge-v1-native-fixed-wide-{baseline,candidate}/`. Two further sunlit comparisons are in
  `ground-edge-v1-native-fixed-sunlit-{baseline,candidate}/`. These temporarily fixed exposure at 2 and restored tone
  and object identities. Reject the current ground mesh for saved-map use: the sunlit view exposes a flat tan gravel
  strip bridging the cobble relief. Redesign contact before checking the 900-1600-unit fade and gameplay timing.
  A map-generator source change triggered the placement guard. `belltower_revalidate_ground_edges.py` regenerated
  all nine files separately and verified byte-identical assets and identical placements before refreshing provenance;
  the original manifest/check/import records remain archived. Native revalidation wrote no assets. The play preview's
  camera had moved, then the editor switched to Ares; no fair timing
  comparison was completed. `runtime-cleanup-audit.json` confirms the old runtime scene is no longer active and
  no temporary comparison objects remain in the Belltower editor scene. Ares was preserved.
- Native ground-decal replacement (2026-10-18): `Tools/belltower_ground_decals.py` stages four private `.decal`
  definitions under `ground-edge-v2/`, using the existing atlas and the validated 116 footprints. The engine's image
  source selects the four original atlas rectangles; source pixels and alpha are unchanged. The decals use Multiply
  albedo at a component mix of 0.5, with no normal, RMO, emission, height or parallax override. They inherit the
  receiving stone's surface detail instead of adding a flat gravel mesh. Four definitions compiled natively and
  remain unreferenced by the saved scene. `capture-ground-decals.cs.txt` uses the existing hidden Belltower document
  and fixed ACES exposure 2; `belltower_capture_ground_decals.py` preserves shared play, selection, camera and tone.
  Eight matched sunlit/shaded close/contextual views across both halves, plus zero-mix controls, are in
  `ground-edge-v2-native-{dedup-baseline,all-control,all-half}/` and `ground-edge-v2-native-east-*`.
  Every trial capture removed all 116 temporary decals.
  Initial `native-*` and `native-warm-*` captures lost background texture detail and are invalid for visual review.
  The corrected prewarm filters the established Belltower model set, keeps distinct material references across the
  wait and requests all normal-map variants. It agrees with the established helper's sharp surface detail.
  `check-ground-decal-bounds.cs.txt` checks native computed volume and actual world rotation against every validated
  footprint; maximum planar error is 0.000123 inches, and all projectors contain the paving plane. The public
  `Decal.WorldBounds` getter omits rotation in this engine, so its box cannot validate a downward projector; the
  read-only API record includes that getter's IL. `belltower_review_ground_decals.py` verifies native compilation,
  loaded crop dimensions/PBR inheritance, controls, source hashes and restoration. `ground-edge-v2/native-review.json`
  and `Sources/Belltower/ground-edges/trial-v2.json` record scope. The restrained dirt stain preserves cobble relief in
  these stills. Remaining-frontage walkthrough, gameplay motion, distance/culling and cost remain before promotion.
- Offline forest-detail trial (2026-10-18): `Tools/belltower_forest_detail_trial.py` stages only a private shader
  and material under `forest-detail-v1/`. The existing atlas, all landscape inputs and all 88 forest meshes remain
  unchanged. The accepted response hard-clips 25-41% of visible base-level source texels in the three variants
  actually used by the current 640,000-triangle forest. The trial uses a smooth mean-matched response and restrained
  source colour, so branches can retain colour rather than receiving only the terrain green. Source colour is
  normalized before fading uncertain-alpha fringes back to the terrain tint. The rejected fallback and tonal-only
  studies are preserved in `colour-before-edge-fix/` and `tonal-only/` inside that trial folder.
  `belltower_check_forest_detail.py` inspected the installed OBJ UV indices and verifies the numerical calibration,
  the fringe regression, unchanged opacity/normal/lighting/fog code and unchanged texture-sample calls. The current
  linear box-mip proxy stays below 2% channel-mean drift through levels 0-5 for used variants; levels 6-7 have larger
  drift, up to about 5.5%. This is not the native BC7 result. Detail returns toward the accepted response with the
  existing card fade, and blend zero returns the accepted response. Six matched unlit Blender albedo studies use
  the original atlas and a canopy colour sampled near a real forest card. They isolate the transfer function and
  do not show native lighting or prove forest realism. `Sources/Belltower/landscape/forest-detail-trial-v1.json`
  records their review and scope. The two private assets are now imported and natively compiled, with loaded
  calibration vectors checked. Four matched current parcel-v4 views and two blend-zero controls restored all 88
  original material slots. The native colour improvement is subtle; distant woodland remains noisy. A separate
  10000-22000-unit fade experiment reduced the far noise but exposed a conspicuous boundary on the near ridge,
  so that setting is rejected. The trial remains unreferenced and the accepted shader is unchanged. Further coverage
  work and consistent gameplay timing remain required; see `native-detail-review-oct18.json` for the exact scope.
- Native comparison tooling (2026-10-18): matched parcel-v4 baselines, candidates, native exposure and restoration
  records are in the `forest-detail-v1-native-*` and `ground-edge-v1-native-*` folders. Eleven versioned source assets
  are installed for these comparisons; neither trial has been promoted. The current capture helper supports
  `forest_detail_trial` on all 88 woodland material slots, validates loaded calibration vectors and uses a private
  material copy for `forest_detail_blend` zero-to-one comparisons. It restores the original overrides and checks
  renderer serialization. Optional fade overrides act only on that private copy. `ground_edge_trial` temporarily
  inserts the two checked models with `RenderType: Off`
  and no collider components, then verifies that the original scene object identities are restored. These trials
  are compared separately. New wide/close ground views and a narrower ridge detail view are in `capture_views.py`.
  The initial helper and guarded imports passed a separate engine-DLL compile; its exact source hashes are in
  `forest-detail-v1-native/helper-static-compile.json`. Later helper changes also ran in the engine. The initial
  colour-comparison helper is archived as `capture-helper-ca8b36.cs.txt`. Native shader compilation uses the guarded
  `compile-detail-shader.cs.txt` and `EditorUtility.CompileShader`; the generic `asset_compile` tool rejects shader
  sources. Both shader result records report success. `Tools/belltower_review_native_details.py` validates matched
  camera/lighting/source hashes, native compile records and restoration, while recording rejected or incomplete
  visual checks separately. `native-detail-comparisons-v1.json` records the session and remaining requirements.
- Forest coverage experiment (2026-10-18): `Tools/belltower_forest_coverage_trial.py` stages a separate two-asset
  `forest-coverage-v1` shader/material experiment. A read-only native query confirmed the accepted atlas is 1254 by
  1254 with nine mip levels. `Tools/belltower_analyze_forest_projection.py` estimates minification from the actual
  320,000 cached crowns and saved native cameras, without occlusion. Its valley frustum centres have a median
  projected width of about 3.1 pixels; those counts are not visible-tree counts. At the rejected 22,000-unit distance
  boundary, the closer ridge view still resolves many crowns at about 20 pixels or more, explaining why a fixed
  distance cut removes useful detail. The installed engine's `vr_common.fxc` boosts alpha by `1 + .25 * mip` before
  alpha testing. The source box-mip proxy shows substantial coverage expansion at levels six and seven, and atlas
  cells become very coarse at the last mip. This is not native BC7/raster coverage proof. The staged shader cancels
  only the requested share of that boost. Strength one takes the accepted path, and mip zero is unchanged; colour,
  normals, lighting, textures, geometry and existing fade distances are preserved. No extra texture sample is added.
  Source checks pass. The two private assets are installed and natively compiled, but remain unreferenced by the
  saved scene. The guarded import/compiler and hidden Belltower document captures preserved Orion play and the
  selected document; no shared-editor handoff was needed. The old static API binding proof predates removal of
  unnecessary play guards in two helpers; current helpers also executed successfully in the engine.
  Adaptive exposure made the initial strength-one control invalid despite identical settings. The replacement
  `forest-coverage-v1-native-fixed-*` study uses temporary ACES exposure 2, restored after each image. All four native
  strength-one controls pass in valley, ridge, ridge detail and terrace. Zero compensation reduces coarse grey grain
  while retaining the closer crown shapes in these stills; the repeated crown pattern remains conspicuous.
  `belltower_review_forest_coverage.py` checks the matched recorded inputs, compilation, controls and restoration of
  all 88 material slots. `forest-coverage-v1/native-fixed-review.json` records the evidence and invalid adaptive
  comparisons. `Sources/Belltower/landscape/forest-coverage-trial-v1.json` records current helper hashes and remaining
  work. Motion, mip transitions and consistent Belltower gameplay performance remain required before promotion.
  Neither alpha compensation nor a shorter fade alone meets the overall visual target.
- Bounded forest-density study (2026-10-18): `belltower_forest_distribution_trial.py` stages eight west-facing
  sectors, reducing their 52,986 cards to 41,137 with correlated retention. The kept cards retain exact positions,
  heights, sizes, UVs and material. A smooth envelope returns retention to one at the study boundary. Eight private
  control models have byte-identical OBJ geometry to the accepted models; the eight candidates are exact exported
  subsets. `belltower_check_forest_distribution.py` checks actual OBJ data, topology, source hashes and all sixteen
  native model compile records. Forty-eight versioned source files are installed, unreferenced by the saved map.
  `capture-forest-distribution.cs.txt` derives from the verified viewport helper and restores eight model references,
  original overrides and all 88 material slots. All variants hold the private alpha-coverage strength at zero and
  use temporary ACES exposure 2. Two native views are in `forest-distribution-v1-native-{baseline,control,clumped}`.
  The clumped candidate shows pale exposed terrain and is withheld. Its image controls also miss the strict 0.1
  mean RGB8 gate (about 0.18 and 0.20); do not claim a clean isolated geometry acceptance comparison. A later
  unchanged repeat after selecting Lowtide shifts brightness much more, despite matching recorded exposure bounds.
  That repeat cannot calibrate the earlier active-tab batch. Resolve exposure consistency and investigate crown
  shape/canopy-to-terrain continuity before another acceptance test; fewer cards alone have not met the visual goal.
  `belltower_review_forest_distribution.py`, `forest-distribution-v1/native-review.json` and
  `Sources/Belltower/landscape/forest-distribution-trial-v1.json` record the failed image gate and exact scope.
  The other local chat was stopped and the editor idle before the brief foreground comparison. Lowtide was restored,
  out of play and saved; all model/material/tone state restored. The saved Belltower scene and accepted shader remain
  unchanged. Do not revive isolated-world capture loops to bypass document availability.
- Preview-camera investigation (2026-10-19): the current engine is resolved through `FACEPUNCH_ENGINE`, including
  the Windows user environment; the former D: Steam installation is gone. Offline installed-engine IL in
  `camera-consistency-v1/engine-api.json` confirms that `InitializeRendering` copies post-processing from
  `Scene.Camera` onto editor cameras. Main-camera selection excludes editor cameras and can fall back to a
  non-main minimap camera. `inspect-preview-cameras.cs.txt` adds camera parent, orthographic state, priority and
  main-camera flags to a read-only probe. After the Ares chat completed, the native Belltower probe confirmed the
  orthographic Minimap Renderer as its fallback. `capture-preview-consistent.cs.txt` pins the existing viewport only
  during synchronous rendering and restores/checks the pointer, tone, pose, projection, exposure, objects and editor
  state. A synchronous exposure change alone did not update GPU history. Settling the active stopped viewport across
  normal frames produced a strong native 0.35/2.0 exposure response. Two seconds still failed repeat consistency;
  five-second baseline/control captures passed the strict 0.1 mean RGB8 gate in sky, forest, stone and plaster regions.
  No Scene.Push scope or camera pin crosses an await. Hidden-document settling remains unverified.
  `Sources/Belltower/lighting/capture-consistency-v1.json` records the native evidence and current helper hash.
  The surface-finish trial reduced broad plaster peeling and calmed the masonry. Three fresh matched native views
  passed sky/forest controls on 2026-10-20, and the nine reviewed materials were published through the editor.
  `Sources/Belltower/materials/surface-finish-v1.json` records the assets and generator: plaster wear coverage 0.24;
  rubble tint [1.04,1,0.90], contrast 1.04, weather 0.12. Texture pixels and shaders are unchanged. The later saved-scene
  image confirms appearance qualitatively; it drifts about 1 RGB8 from the earlier candidate and does not pass the
  strict cross-session photometric gate. Do not use it for a precise before/after measurement.
  The forest-shapes trial replaces UVs in eight sectors without moving cards: irregular outlines help, but the result
  still reads as repeated cards, so it remains withheld. The October 20 audit matched both trials' original guards
  before publication: gate/clock/planter town mesh edits were outside their guarded inputs. The subsequent public
  material, generator and saved planting changes intentionally invalidate those earlier guards. Preserve the
  historical manifests; a future comparison needs an explicit new revision, not silently refreshed hashes.
  The new `Sources/Belltower/generated/belltower-visual-target-oct19-v1.png` and its JSON are an ImageGen art
  reference for warmer distinct masonry, localized plaster wear, balanced sunlight and varied woodland crowns;
  they are not native screenshots or evidence of implemented graphics.
- Constructed town gates (2026-10-19, user: "fake/plain/flat"): `belltower_gate.py` replaces each flat slab and three
  continuous bars with fourteen bevelled boards, two leaves with rebated backing and an overlapping centre joint,
  six hinge straps with barrels and rivets on each face, ring pulls, a sliding bolt, rear compression braces, a curved
  timber lining and separate stone voussoirs. Timber UVs select seam-free strips of the existing CC0 scan.
  `belltower_stage_gate.py` matched and removed exactly 48 old triangles per half from the installed meshes, then
  appended 13,088 new triangles. All other OBJ lines and all VMDL physics are byte-identical, preserving firewood-v2
  and lorry removal. One gate-only forged-iron material was added. The generator retains the old collision box.
  `import-gate-v2.cs.txt` published the correction to the first pass through the native editor, using backups and
  hash guards. The asset watcher compiled both halves; never force-compile these large town models.
  `belltower_check_gate.py`, `Sources/Belltower/gates/town-gate-v2.json` and `gate-v2/verification.json` record checks.
  Native west front/oblique and sunlit east views are in `output/belltower/quality/gate-v2-after/`; every capture
  restored editor state. The first pass's centre daylight leak and overly high hinge positions were corrected.
  The Belltower scene file was unchanged by the gate edit. The user moved into Belltower and requested that edit
  during the earlier comparison slot. Match performance was not measured.
- Circular tower clocks (2026-10-19, user: "the white around the clock is weird"): `belltower_clock.py` replaces the
  four opaque square dial images and their square stone backing patches with circular enamel meshes and a profiled
  bronze bezel mounted directly against the tower. The existing clock artwork, hour/minute marks and hand orientation
  are unchanged; explicit UVs retain the original 80-inch artwork scale. No raster pixels or materials were edited.
  `belltower_stage_clock.py` removed exactly 48 old triangles and appended 8,056 to the installed centre OBJ; all other
  mesh lines, the VMDL, material mappings and collision remain byte-identical. `import-round-clocks-v1.cs.txt` published
  that single OBJ through the editor, with a guarded backup. The watcher compiled it successfully without a forced build.
  Native front and oblique comparisons in `output/belltower/quality/clock-v1-after/` show the square corners gone and
  the bezel's edge/shadow against the masonry. `belltower_check_clock.py` checked all four exported circular edges,
  source hashes, unchanged data and capture restoration; static stone controls passed the 0.1 mean RGB8 limit.
  `Sources/Belltower/clocks/round-clock-v1.json` records acceptance. The saved scene and both gate meshes are untouched.
- Worn stone planters (2026-10-20, user: flat/plain, edges too perfect): `belltower_planters.py` replaces the six
  visible boxes with individual chipped, bevelled stones, mitred projecting coping, recessed nonflat soil, clods,
  pebbles and one thin curved root. Existing CC0 stone/soil pixels are unchanged; private stone UVs avoid painted
  mortar seams. Two planter-only materials and a private stone shader retain restrained normals and dry roughness.
  `belltower_stage_planters.py` preserves every non-planter OBJ byte, including gates/firewood/lorry removal, and all
  existing VMDL physics. Each half removes 36 triangles and adds 6,682. The old 40x40x28 collision box remains;
  there are no new scene objects or colliders. Never force-compile the large town models.
  A temporary lowering trial showed the old shrubs floating above the soil. Native undoable scene tools lowered
  exactly six existing shrubs by eight inches and saved the scene. `belltower_map.py` keeps that placement on
  regeneration (planter blob centre z36). All other authored scene properties are preserved. Native Save Scene also
  refreshed same-path resource IDs, float text, renderer defaults and five generated prefab binding entries;
  `belltower_check_planter_scene.py` audits each category and unchanged prefab overrides, rather than concealing
  that serialization diff. Original scene/mesh manifests remain historical.
  `belltower_check_planters.py`, `planter-v2/scene-revision.json` and `Sources/Belltower/planters/worn-planters-v2.json`
  record preservation, actual exported geometry, native asset compilation and final placement. Four restored native
  views in `output/belltower/quality/planter-v2-saved/` cover close, context, low angle and the shaded mirrored planter.
  Match performance and moving-camera aliasing were not measured; this changes physical shape, not AA settings.
- Garden bush grounding (2026-10-20, user: "floating bushes"): the beech asset's low outer leaves reach local z
  -19.216661, while the central stem starts at z0.845722. The old crown/bounds placement left tall hedge stems
  20.76 inches above the lawn, low borders 5.85 above it, parterre plants 5.21 above soil, and bed plants 3.77 above
  their raised soil. Native vertex inspection is in `output/belltower/bush-grounding/`.
  `belltower_detail.shrub(..., ground_z=...)` now embeds the central stem half an inch into its soil and adjusts only
  vertical scale to retain the old canopy top. `belltower_map.py` supplies the lawn/soil height for 12 tall hedge
  shrubs, 100 low hedge shrubs, 24 parterre plants and 108 raised-bed plants. Widths, x/y positions and yaw stay;
  pots, planters, pergola foliage and other props retain their existing placement.
  The shared editor repeatedly exited during startup before MCP became available. With no editor running, the
  guarded closed-editor publisher replaced only 488 Position/Scale string values in the saved scene; every other
  scene byte stayed intact. The original f92a810e... scene is archived; the resulting scene is a7c75cfe... .
  `belltower_check_bush_grounding.py --offline` verifies the exact saved delta, root contact, canopy tops and unchanged
  town models. The latest shared garden generator also produces identical geometry/collision with old versus new
  shrub placement. Newer shop/stall/scarecrow/gazebo work that appeared while waiting was preserved with an explicit
  input revision, not overwritten. Earlier planter/gate/clock evidence remains historical; the grounding diff proves
  their assets and scene placements were untouched by this correction.
  `Sources/Belltower/gardens/bush-grounding-v1.json` records the saved correction. Native visual verification is
  still pending because of the startup exits. Do not rerun `native-apply.json`: the transforms are already saved.
  When the editor is available, open the current scene, run `check-garden-grounding-after.cs.txt`, then capture the
  four planned views with `capture-preview-consistent.cs.txt` and the current scene hash.
- Woodland volume prototype (2026-10-20): `belltower_forest_volume_trial.py` stages one private shader and strength
  0/0.42 materials against the eight private forest-shapes sectors. Atlas-derived crown coordinates and a derivative
  frame perturb diffuse normals without adding triangles or texture samples. The shader compiled and materials
  loaded natively. Four fixed native captures restored all model/material/camera/scene state, but the forest
  candidate/control difference (0.01733 mean RGB8) was smaller than control/repeat variation (0.01797).
  `Sources/Belltower/landscape/forest-volume-v1.json` records the unresolved ineffective result. These assets remain
  private and unreferenced by the saved map; do not promote them or claim rounded canopy lighting.
- The user asked for a new multiplayer map. Belltower is a walled hill town's market square, built by script the way
  Ridgeback's buildings are (`Tools/map_kit.py`, with `Tools/building_textures.py`'s materials). The script's docstring
  has the layout, the conventions and the plan axes. It writes:
  - four models to `Assets/models/maps/belltower/`: `belltower_centre`, `_west`, `_east` (the west half's mirror) and
    `_vista`;
  - the scene, `Assets/scenes/maps/Belltower/belltower.scene`;
  - the radar picture, `ui/minimaps/minimap_belltower.png`, drawn from the collision in Innocent Hotel's style.
  Keep layout changes in the generator. When the editor is open, stage changes with the quality scripts and
  publish them through native s&box tools; do not overwrite the open editor's scene or assets from Python.
  `Sources/Belltower/editor/` holds the native import and capture method bodies as `.cs.txt` files: copy these to
  the current MCP session exchange directory and run them with `run_csharp`. Scene import checks the current source
  hash, preserves gameplay objects and scene properties, and refuses an open Belltower editor document. It saves
  the source for the next load without replacing a running match.
- Native visual pass (2026-10-14): `belltower_quality_sources.py` records original CC0 Poly Haven photographs and
  checksums in `Sources/Belltower/scans/manifest.json`; `belltower_quality_materials.py` owns the scan-based materials.
  The stone, neutral painted plaster, interior plaster and clay roof maps retain their original pixels. Exterior
  and interior plaster UVs use different scales to preserve the photographed physical size.
  - `belltower_relief.shader` uses the matching height maps for cobbles and rubble walls. The two-metre tiles use
    UV multipliers 3.2512 and 2.032 respectively; apparent depth is 0.6 and 1.5 inches. Dry cobble mortar has a 0.7
    roughness floor. The shader traces 10-28 height samples, retains base UV derivatives and fades the effect from
    700 to 1800 units. It changes surface appearance without altering silhouettes or collision. Ashlar remains on
    its existing shader: the supplied medieval_blocks_03 height map is flat and cannot supply useful relief.
  - Stage the rubble height source with `belltower_quality_sources.py --only medieval_blocks_05 --out
    output/belltower/quality/relief-v1-sources`; `import-relief.cs.txt` verifies its original MD5, imports it and
    compiles the shader natively. Stage only the changed materials with `belltower_quality_materials.py --only
    street_cobbles rubble`, then use `import-materials.cs.txt` and native material compilation. Material imports
    replace source files atomically because the compiler can retain memory mappings on the previous file.
    Native street, wall, mirrored-side and grazing-angle checks are in `saved-relief-v1/`; the accompanying timing
    files measure RenderToBitmap including readback, not in-game FPS. Backups are in `before-relief-v1/`.
    `compare_relief: true` alternates relief off/on/on/off using copies assigned only to the isolated capture scene.
    In `relief-cost-check/`, pooled 32-sample medians added 0.18-0.36 ms in the street views and 0.04 ms in the hall
    control. The larger shift between separate capture runs remains visible with relief disabled, so it is not a
    measurement of the height-tracing cost. Full-game performance still needs a separate check.
  - Wall material v3 (2026-10-18) supersedes the rubble scan/regular-block finish above with ImageGen limestone color
    and height plus photographic climbing ivy. `Sources/Belltower/wall-v3/README.md` records the material workflow;
    `generation.json` contains the exact built-in ImageGen prompts and saved source paths. The separate
    `belltower_masonry_v3.shader` uses shared color/height UV selectors from `Tools/belltower_wall_quilt.py`, shallow
    relief and height-derived normals. `belltower_quality_materials.py` owns both `rubble` and `ivy_climb`; older
    material/front generators already delegate these definitions. Native captures are in `output/belltower/quality/wall-v3`.
    The earlier wall-v2 buried-face cleanup remains in the map generator, with its existing collision and exterior foundations.
  - `belltower_architecture.py` adds roof relief from the photographed height map, closes its perimeter to the roof
    substrate, adds clay ridge caps, and builds shutter rails, tilted louvres and hinges. Cornices sit below the roof
    surface. Council Hall piers have small bevels. `belltower_detail.py` uses smooth parasol gores and scalloped hems.
  - `belltower_furniture.py` builds separate cart and crate boards, wheel felloes/spokes/tyres, raked bench slats,
    cast-iron arms and feet, and rounded sacks with seams. Wood uses original 4K `brown_planks_03` maps at their
    photographed one-metre scale; board UVs avoid scan seams. Lanterns have transparent glass around separate bulbs.
    `belltower_architecture.street_door` adds bevelled raised panels, rails, stiles and brass fittings to 38 closed
    street doors. Neither pass changes playable doorways or collision. Both halves now have 939,001 visual triangles;
    the centre has 246,560 after the hall joinery and deck pass. All 94 placement/reachability checks and native model compiles passed. Native material
    resource checks are in `props-v1-native-resources.json`; reviewed door captures are in `doors-v1-viewport/`.
  - Bench arm placement v2 (2026-10-20): `belltower_furniture.bench_arm` separates the arms from the leg frames.
    The 36 armrests on 18 benches move outward 4.9 inches; their grip centres are 1.1 inches from the ends,
    so the grips meet the slat ends. Seats, backs, legs, braces, bolts and collision remain unchanged.
    `belltower_stage_bench_arms.py` patches only the arm faces in both canonical OBJs and four existing bounded
    imports. Native publication, current compiled-model checks, all 18 exported benches and native thumbnails
    passed. The running game was preserved; no in-map screenshot was captured. See
    `Sources/Belltower/benches/arm-placement-v2.json` and `output/belltower/bench-arms-v2/verification.json`.
  - Bench rear-support clipping v3 (2026-10-21): `belltower_furniture.bench_back_support` replaces the old
    steeper upright with a closed casting raked eight degrees with the slats. Its front has 0.04 inches of
    clearance behind the back boards; its offset foot clears the last seat board and meets the seat carrier.
    All 36 supports on 18 benches retain the old triangle count. `belltower_stage_bench_backrest.py` patches
    only those faces in both canonical OBJs and their two existing bounded iron imports. Seats, back slats,
    arm placement v2, bolts, collision and model descriptions are unchanged. Native publication and both
    incremental model compiles passed. Five first-person captures from a running Belltower match reviewed
    the rear, oblique rear, seat joint, front and mirrored rear. The test was stopped and the saved Belltower
    editor document left open. See `Sources/Belltower/benches/backrest-v3.json` and
    `output/belltower/bench-backrest-v3/in-game/`; these supersede v2's missing in-map bench check.
  - Crate joinery v2 (2026-10-20, user: boxes look flat): `belltower_crates.py`, called by the furniture crate
    helper, adds shallow physical cupping, worn chamfers, varied board depths, rebated corners, a recessed lid
    under raised cleats, round nail heads and existing photographed end grain. The 66 shipping crates keep
    their centres, orientation, stack height and original cover collision. No texture pixels or materials changed;
    each half adds one mapping to the existing `bench_oak_endgrain.vmat`. `belltower_stage_crates.py` matched
    60,456 old crate triangles per half and replaced them with 84,840; every non-crate OBJ byte and all VMDL
    physics remain intact. Source assets were installed locally only after the editor had closed. The initial
    prototype compiled and rendered as a native model thumbnail; final refined model compilation and map review
    remain pending. Standalone resourcecompiler could not mount the required asset configuration; its zero-job
    or configuration-error results do not validate these models. `Sources/Belltower/crates/joinery-v2.json` and
    `output/belltower/crates-v2/verification.json` record this scope. The scene and all foliage were untouched.
    This legitimate crate edit postdates the model hashes in the separate bush-grounding plan: retain it when
    revalidating that plan, using the exact non-crate preservation proof. Do not regenerate the whole town.
  - Facade profiles v1 (2026-10-15) replaces box cornices and window heads with three profiled variants,
    bevels the surrounds, slopes the sills, varies some upper shutter angles, and divides wall coping into
    individual bevelled stones. Ground-floor shutters and original collision bounds are preserved.
    The centre now has 247,036 authored triangles; each half has 969,171. All 94 spot/reachability checks,
    35 detail-geometry cases, and convex-hull/physics comparisons passed. Only the three visible OBJ files changed.
    `Sources/Belltower/facades/manifest.json` records the accepted sources, checksums, compiled resources and six
    same-camera comparisons in `facades-v1-before/` and `facades-v1-saved/`. The scene file, v9 indirect lighting
    and v7 reflections are unchanged. Runtime performance has not been measured for this pass.
    `import-facades.cs.txt` verifies backups and hashes and can resume a checked partial import. A Git status scan
    temporarily denied replacement of an OBJ; it cleared naturally. Inspect the current hashes and locking process
    before retrying. `verify-facades.cs.txt` uses the off-editor `source-geometry.json` count report and validates
    loaded resources: this running engine's GetIndexCountForLod reports the first material's indices, not the total.
    The full source triangle totals are independently counted and tied to the imported OBJ hashes.
  - Garden props v2 (2026-10-15) is imported, natively compiled and reviewed as an incremental quality pass.
    `belltower_gardens.py` closes the shed roof gaps, builds individual boards and braced doors with hardware,
    adds slatted compost bins and stacked split logs, and replaces the wheelbarrow box with an open basin,
    frame, legs and rounded wheel. Cut log faces reuse the existing Gunsmith Range oak end-grain material.
    Each town half now has 996,123 authored triangles, 457 collision boxes and 116 hulls. All 94 placement and
    reachability checks and 11 prop geometry checks passed. Garden collision, shared RNG state and scene props
    are unchanged. Both native model compiles and material-load checks passed; the scene and lighting are unchanged.
    Seven native baseline views are in `garden-v1-before/`; offline construction previews are in
    `garden-v1-studio/`. Seven matching native captures are now in `garden-v1-saved/`. The shed's corner stiles and
    bottom rails shared the cladding plane and showed depth-buffer artifacts. Garden v2 recesses the boards by
    0.25 inches and moves the backing farther inward, preserving collision and silhouette bounds. Its 11 geometry
    checks and three cladding/trim overlap checks pass; the two town meshes are installed from `models/garden-v2/`
    after all 94 gameplay checks and collision comparisons. `garden-v2-trim-regression.json` proves the check rejects
    all three v1 sheds and accepts v2. Two offline construction views are in `garden-v2-studio/`; seven matching
    native views are in `garden-v2-saved/`. `Sources/Belltower/gardens/manifest.json` and
    `garden-v2-saved/verification.json` record the accepted sources, native compiles and unchanged scene/collision.
    The shed edge artifacts are resolved. Firewood still needs less faceted profiles and convincing bark/cut faces.
    The wheelbarrow chassis correction is accepted in v3 below.
    `garden-v1-checkpoint.json` records the rejected overlap. Do not restore the older facade models over these
    changes. `garden-import-request.json` selects
    the checked garden revision. `import-gardens.cs.txt` supports checked partial imports and preserves an unrelated
    known play session; inspect hashes and the locking process before resuming any interrupted publication.
    Garden v3 is accepted after native comparison (2026-10-15): its wheelbarrow chassis stays below the basin,
    with four mounts and lowered braces.
    The old generator is preserved in `garden-v3-before/source/`. The basin regression check catches 138 intruding
    samples in v2 and none in v3. All 11 geometry cases, three shed trim checks and 94 gameplay checks pass;
    collision and shared RNG state are unchanged. Each staged half has 996,387 triangles, 264 more than v2.
    `garden-v3-studio/wheelbarrow.png` is an offline construction render; it has been reviewed but is not an engine
    screenshot. Both checked v3 OBJ files are now installed, natively compiled and loaded. The wheelbarrow and
    terrace views in `garden-v3-saved/` match the v2 camera/lighting metadata; the frame is visibly below the basin.
    `Sources/Belltower/gardens/manifest.json` and `garden-v3-saved/verification.json` record acceptance, unchanged
    collision and scene, and restoration to saved Spillway with play stopped. The v2 backups remain preserved.
    `garden-v3-native/partial-import-state.json` is historical evidence from the earlier interrupted import.
    Git text-diff readers held the west OBJ during that work. `.gitattributes` now disables text diffs only for
    the two generated town OBJ files; scoped numstat completes with binary entries. The import still checks hashes
    and publishes atomically; inspect a timed-out or locked operation before retrying it.
    A separate offline firewood trial is in `Tools/belltower_firewood_trial.py`; it does not replace that pinned
    garden generator. The original built-in ImageGen bark, cut-face atlas and split-fibre albedos are preserved as
    `Sources/Belltower/generated/firewood-{bark,cuts,split}-v1.png`, with prompts and provenance in matching JSON.
    The trial has 34 irregular logs, 27 split, with rounded bark, growth rings and lengthwise fibres. It uses 8,024
    triangles per pile versus 1,768 before. `firewood-v1-studio/geometry-checks.json` verifies closed outward surfaces,
    bounds at both studio and garden placements, safe atlas UVs and unchanged shared RNG. The accepted assets,
    production generator and collision are unchanged. `Sources/Belltower/gardens/firewood-trial-v1.json` records
    the reviewed same-camera Blender comparison at exposure -1.2. These are construction renders, not engine
    captures. Surface normal maps, whole-map integration and native visual/performance validation remain pending.
  - `belltower_interiors.py` replaces the hall's box furniture with pegged trestles, separate eased boards,
    breadboard table ends, drawer fronts, recessed archive doors, and bronze fittings. Its oak floor and ceiling
    use staggered individual boards; the ceiling beams have softened edges. Both stair openings stay clear, and
    the deck vertices remain inside the original slabs. The centre retains its 403 collision boxes and 56 hulls.
    `hall-v2-deck-checks.json` records the bounds checks; `hall-plaster-native-results.json` records native imports
    and successful compiles. `council-hall-target-v1.png` and `.json` preserve the ImageGen design reference.
  - All eight exterior plaster colours now use `belltower_plaster.shader`. It blends the clean two-metre scan
    with original 1.5-metre `rough_plaster_broken` photographs using continuous warped sampling, broad wear patches
    and stronger weathering near the base. Coverage is 0.34; normal and roughness maps follow the same blend.
    The production material generator owns these definitions. The earlier triangular sampling trial was rejected
    for visible seams. `hall-plaster-streaming/` contains native captures with material and DDGI textures resident.
  - `belltower_window.shader` supplies reflected glass with a parallax room behind windows and shopfronts. The shop
    shelf image was generated with the built-in ImageGen tool; original output and prompt are preserved in
    `Sources/Belltower/generated/shop-shelves-v1.png` and `.json`. It is an asset texture, not a gameplay screenshot.
  - Window boxes now use small intersecting geranium clusters and folded hanging ivy; balcony bougainvillea also
    has depth. `window-plants-v1.png` and `.json` preserve the built-in ImageGen atlas and prompt. The plant shader
    samples its original RGBA directly, including the alpha channel. Native shader, material and model compiles
    passed, and `output/belltower/quality/foliage-v1/` contains reviewed cafe and street views. The two halves each
    gained 888 visual triangles; all 94 gameplay checks passed and collision is unchanged.
  - `belltower_quality_models.py` stages the three town models, checks all 94 spots and reachability, and compares
    convex collision geometry and VMDL physics before native import. This pass preserved gameplay collision.
  - `belltower_quality_foliage.py` selects 1,600 cloud oak trees from the landscape painter's crown plan. It respects
    roads, buildings, yards and existing trees, and places each tree on the rendered terrain. These have no colliders,
    use automatic LOD, and cast shadows only near town. The deterministic scene group is in
    `Sources/Belltower/landscape/trees.json`; its dry-oak package is `facepunch.treeoakdrymediuma#289352`.
  - Distant woodland v8 (2026-10-15) adds 320,000 town-facing tree cards in 88 sector meshes, 640,000 triangles.
    These are visual only, with no collision or shadow casting. The original generated RGBA tree atlas is preserved
    in `Sources/Belltower/generated/forest-trees-v1.png` with its prompt/provenance. `belltower_forest.shader` uses
    diffuse lighting and the landscape B/C/D palette and slope normals, averaged over a 128-unit crown footprint.
    Generated leaf detail modulates that colour; distance fade is 30,000-52,000 units. Single cards avoid the bright
    crossed-card seams. The v8 pass was reviewed against same-session baseline captures at the valley, west ridge
    and terrace, then saved natively. It improves the nearby canopy; the far valley still needs refinement.
    `Sources/Belltower/landscape/forest.json` is the accepted native group, and `forest-manifest.json` records its
    source/asset hashes. `belltower_map.py` includes that cache when regenerating; staging trials are excluded.
    `belltower_quality_forest.py` stages placement, models and materials. Import with `import-forest.cs.txt`, compile
    the material and verify with `verify-forest.cs.txt`. `apply-forest.cs.txt` is only for the first reviewed save;
    it refuses an existing group. Future replacements must update the existing group rather than adding another.
    `forest-v8-saved/` contains fresh saved-scene captures and the scene comparison; `audit-forest-sources.py --saved`
    verifies all 267 inputs, all 88 current compiled models, 640,000 triangles and the matching regeneration cache.
    The native save also refreshed per-process resource IDs/two prefab child mappings and wrote the new false
    ZombiesOnly default; town geometry/collision, transforms and other scene values were preserved. The v9 indirect
    light and v7 reflection assets are unchanged. Editor performance was sampled with play stopped; gameplay
    performance remains unverified and the overall AAA quality goal remains open.
  - The landscape pass replaces rectangular field rows with larger, warped Voronoi parcels, reduces crop-colour
    contrast and varies woodland coverage continuously at its edges. Crop choice is sampled at each parcel's fixed
    site, so the same parcel keeps its crop across scanlines and texture zones. All four colour/kind maps are 4096px;
    normal maps are 2048px. The tree plan follows the same revised parcels and retains the 1,600-tree budget.
    `output/belltower/quality/landscape-v2-preview/` contains comparisons before the woodland addition. Distant
    fields and the near retaining walls still need refinement for the overall quality goal.
  - Offline canopy candidates (2026-10-15) have not changed the accepted landscape. `belltower_canopy_trial.py`
    stages procedural variants; `belltower_photographic_canopy.py` uses the original built-in ImageGen RGBA atlas
    `Sources/Belltower/generated/canopy-crowns-v2.png`. Its JSON preserves the edit prompt and provenance; the v1
    original is also retained. The atlas alpha is unchanged, including occasional alpha=1 pixels in the gaps.
    Natural oak/holm/beech/willow crowns use premultiplied linear filtering; planted trees keep the accepted painter.
    The first photo trial had straight overlap cuts from intersecting analytic domes. V2 layers whole crowns by
    summit height with world-coordinate tie breakers. `canopy-photo-v2-checks.json` verifies input-order invariance,
    matching tile edges, unchanged planted trees and all four species; the check rejects the original painter.
    `canopy-photo-v2-review.json` records the reviewed swatch, 2048px zone B and 1024px zone C comparisons. Coverage
    in the matching grove is 79.87% versus the accepted 80.87%. Ellipsoid shadows remain approximate, and distant
    texture detail/repetition still need full-resolution and native review. All candidates stay under quality output;
    the accepted landscape generator, live textures, tree placement and scene are unchanged.
    The complete 4096px candidate is now in `canopy-photo-v2-full/`. All four normal maps match the accepted files
    exactly, and zone A's colour/kind maps are also identical. `offline-review.json` records the full-size review,
    source checks and pixel comparisons; the broad far-field woodland patterns still need improvement.
    `belltower_quality_canopy.py` stages eight colour/kind textures and two material copies under a separate
    `materials/belltower/vista/canopy-photo-v2/` resource path. It preserves every other material setting and all
    accepted inputs. `import-canopy-trial.cs.txt` validates sources, dependencies and the allowlist, imports only
    missing or identical trial files, and supports inspected partial resumption. It has not run natively yet.
    Compile both trial materials, then run `verify-canopy-trial.cs.txt` to check all loaded texture dimensions.
    The capture helper's `--canopy-trial` temporarily overrides the vista and existing woodland materials together,
    prewarms 4096px colour maps for both baseline and candidate, and restores exact renderer snapshots afterward.
    Its import, resource verification and new material-override branch still require native validation. Review
    matching valley, west-ridge and terrace views before changing any accepted landscape input or manifest.
    `check-native-script-types.py` type-checks the six garden/canopy/camera method bodies against the installed
    .NET 10 engine assemblies without executing them. `native-script-types/report.json` records the matching
    script hashes and zero compiler diagnostics. This confirms API compatibility, not native rendering or restoration.
  - Stage landscape textures with `belltower_vista_paint.py --out <output directory>` (four CPU threads), then
    `belltower_quality_landscape.py --source <same directory>`. The latter checks the bundle and writes the native
    import manifest. `import-landscape.cs.txt` verifies all staged and destination hashes before writing; compile
    `materials/belltower/vista/vista_land.vmat` afterward. Backups are in `before-landscape-v2/`. Stage matching trees
    with `belltower_quality_foliage.py --out <output directory>` and review with the capture script's staged_landscape
    and landscape_resource settings before saving. `Sources/Belltower/landscape/textures.json` records the accepted
    source hashes; lighting manifests include these texture inputs as well as the tree group.
  - Lighting uses the photographed Kloppenheim sky, a warm sun at pitch 34/yaw -63, an ACES exposure range of
    1.05-2.2, and native indirect lighting across a 28x39x5 grid (5,460 probes; 4,806 active in v9). Three 256px reflection cubemaps use
    Baked mode. `Sources/Belltower/lighting/` preserves the volumes, probes, source hashes and bake light settings;
    `belltower_quality_lighting.py` imports a reviewed native bake into that cache for future scene regeneration.
    The saved scene uses daylight-v9 indirect light and the three accepted daylight-v7 reflections. These
    `.vtex_c` textures have no uncompiled source; the narrow `.gitignore` exceptions are intentional. One town volume covers world bounds
    (-1480,-2400,2) to (1880,2400,450), density 8, strength 2, normal bias 20 and view bias 30. The revised vertical
    spacing reaches the upper hall; no extra local hall volume is used. Fresh saved-scene views and the menu image
    are in `output/belltower/quality/hall-plaster-final/`. The v9 bake includes the revised hall joinery, timber decks
    and worn plaster, and completed both lighting passes. It retains the v7 reflections. `daylight-v9-save/` verifies
    that only the three indirect-light texture paths changed in the saved scene. The source manifest records local
    geometry, shaders and textures, including the landscape and height maps.
  - Use `Sources/Belltower/editor/capture-viewport.cs.txt` with the persistent Belltower editor document. It captures
    one bitmap per call, dispatches render hooks, and explicitly applies the scene's post-process volume to the
    viewport camera. A hidden tab can have no `Scene.Camera` while another map is playing. It records the requested
    camera exposure settings and preserves the selected document and game state while restoring its camera transform.
    It uses the persistent document's hidden `editor_camera` directly, without selecting its tab. Mark material
    textures used at mip size 2048 and all three indirect-light textures at their full dimension before a short
    streaming wait; then mark the DDGI system dirty and update its volume buffer synchronously. Hidden documents
    do not tick normally: missing prewarm can produce black shadows or blurred textures in offscreen captures.
    Do not disable global texture streaming for this capture. Use saved-scene captures for final
    verification. Do not revive the older isolated-scene capture/benchmark loops. `scene.Push()` changes global
    `Game.ActiveScene`: use only synchronous scopes and never keep one across `await`.
    `look_trial` can temporarily compare the Tonemapping mode and exposure bounds, then restore the serialized
    component and camera settings. Eleven native images in `look-v1-*` were reviewed: AgX visibly improves the pale
    surfaces, but exposure bounds and compensation produced nearly identical pixels despite changed camera metadata.
    `look-v1-review.json` records matched cameras, pixel differences, exact component restoration and the unchanged
    saved scene. Effective rendered exposure remains unverified; do not treat metadata as proof. Local engine IL
    shows editor rendering can copy post-processing from `Scene.Camera` again, and native tone-map parameters cross
    into the renderer; the cause is not confirmed. Inspect both cameras/native settings and use a deliberately
    separated fixed-exposure comparison in the next coordinated window. No look changes have been saved.
    `capture-camera-state.json` confirms separate main and editor cameras with valid native tone-map systems.
    The staged capture helper records `NativeExposureAfterRender`; `--sync-main-postprocess` is an opt-in diagnostic
    that updates both cameras and restores the main camera's prior exposure values. This new branch has not run
    natively yet. `aces-fixed-low` and `aces-fixed-high` use 0.35 and 2.0 bounds to make the next comparison decisive.
    The latest helper also sets horizontal FOV and bitmap dimensions after its streaming wait and restores those
    projection values afterward. The installed SceneViewportWidget resets projection each editor frame, as confirmed
    independently by Cerro Blanco's capture work and the local source. This helper renders synchronously after setup;
    the garden v3 native captures validate its `Projection` metadata and reported native exposure of 1.05-2.2.
    The fixed-exposure/main-camera diagnostic and canopy override still await native validation. The read-only camera
    probe reads `IsSceneEditorCamera` as a field, matching the installed engine IL. Its updated missing-document
    branch compiled and ran natively without changing the active game or document. Belltower was closed; open it
    in the next coordinated slot before capture. `direct-camera-read-unwrapped-final/` preserves that result.
    Fresh CLI connections using direct `tools/call` succeeded where this chat's `call_tool` wrapper calls timed out.
    `editor_check.py --direct-call --cleanup-exchange` selects that route and removes only its own script and empty
    exchange directory. `capture_views.py` uses those options. `direct-route-status/` and `direct-route-console/`
    confirm the correct project, successful C# compile and another chat's active Cerro Blanco game; they do not
    grant an editor slot. Copy fresh helpers from source for the next coordinated window.
    The helper and capture runner also accept `--pid` to pin the verified editor when test clients are running;
    the connection checks that PID, editor kind and project before dispatch. PID 15884 was verified for the v3 slot.
    `network-static-audit/report.json` inspects the saved scene against enum values read from the running engine.
    Its three reflection probes, indirect light and static visual hierarchy use Snapshot mode without excluded
    flags. The lighting/forest regeneration caches agree after normalizing texture references from Id/Path objects
    to paths; no saved fields were changed. This is source-level evidence, not a two-client rendering check.
  - `Sources/Belltower/visual-target/west-street-target-v1.png` is an ImageGen design reference. Actual native captures
    are under `output/belltower/quality/`. The AAA quality goal remains open: distant painted fields, repeated facade
    detail and interior dressing still need work. The Council Hall's black column blotches, cafe plinth speckle
    and terrace parapet artifacts were isolated to baked indirect light. The denser daylight-v5 town volume and
    completed second bounce resolve the large artifacts in fresh saved-scene captures; small residual speckles under
    furniture and awning edges remain. Local hall volume experiments were rejected after checking exterior views.
    Capture errors preserve inner stacks. Native parallel `ComputeProbeRelocation` can race the engine's unlocked
    `ResourceSystem.RegisterWeak` dictionaries, then break rendering throughout the process. Do not retry that path.
    `bake-editor-lighting.cs.txt` calls trace and relocation methods sequentially on the main thread, yielding
    between rows. It uses the persistent editor scene and the updater's own scene world.
    `DDGIProbeUpdaterCubemapper.RunAsync` replaces GeneratedIrradianceTexture for its
    second pass: fetch the current texture after the await before saving, or only the first bounce is preserved.
    The importer requires a completed two-pass `bake-result.json` before it updates the accepted cache. The dense
    town bake currently uses a 600-second cancellation limit and a longer connection timeout. A cancelled bake must
    never be published. In the v8 recovery, Quality GGX reflection filtering faulted the GPU in
    `envmap_filtering_cs.shader_cs`; preserve the accepted v7 reflections and do not repeat that capture path.
    `daylight-v8-gpu-crash/` preserves the diagnostics and unaccepted reflection. Apparent hangs can also be native
    asset compilation or resident-resource reloads; inspect progress before terminating an editor. A later lobby
    startup stall in PID 16792 was `BuildNetworkedFiles` / `LargeNetworkFiles.AddFile` hashing multiplayer assets on
    the main thread. Disk reads kept advancing; it recovered after about seven minutes without a restart. The
    stack, asset inventory and recovery record are in `startup-recovery/editor-stall-16792*`.
- The town is mirror-symmetric. Red Team spawns on the west road inside the town wall, Blue Team on the east. Three
  lanes join them:
  - North: Market Street, with the market cross in the middle. Bomb site A is at its east end.
  - Middle: West and East Street, through the square. The Town Hall and its belltower stand on the square, with the
    council hall upstairs.
  - South: the terrace, above the gardens (48 lower). Bomb site B is in the east gardens.
  - Between the lanes are alleys, the Bakery and Dairy, the Inn and Tavern, and the church. The east half is repainted
    in cool colours (`EAST_PAINTS`), so each side reads as its team's.
- The church's three square-facing windows (2026-10-21) use `Tools/belltower_church_windows.py`: recessed timber
  sashes, curved heads, individual tinted glass panes, eased stone surrounds and sloped projecting sills. The front
  cornice stops either side of the large arch instead of cutting across it. `dress` opts into this only on the church's
  `+n` face; opening dimensions and the original two-inch glass collision slabs are unchanged.
  `belltower_stage_church_windows.py` replaced only 225 original visual triangles with 5,436. The centre VMDL redirects
  three bounded imports to private copies and adds `church-windows-v1/windows.obj`; all original bounded imports,
  including the rebuilt fountain, remain unchanged. The three private glazing materials reuse the existing coated
  glass shader without editing it. Native compilation and exterior/interior captures succeeded. Applied-state and
  verification records are in `Sources/Belltower/windows/church-windows-v1.json` and `output/belltower/church-windows-v1/`.
- Houses nobody enters are one collision box each. The open buildings have doorways and no doors, because bots can't
  open doors. Roofs are 42 degrees, over the navmesh's 40, and every attic is filled with its roof's hull.
- Market Street's two lorries (one each half, plan (-+900, 1290)) came out on 2026-10-19 (the user: "remove this truck
  from belltower it looks awful"). `lorry()` and its call are gone from `belltower_map.py`.
  - The installed halves weren't regenerated (the generator's other inputs have moved on since they were built).
    `output/belltower/lorry-removal/find_lorry.py` built the lorry alone with the generator's own code and found its
    330 triangles a half in the installed OBJs, by their written vertex positions and material. `stage_lorry_removal.py`
    dropped those faces (the vertices stay, unused) and the lorry's 6 `PhysicsShapeBox`es a half (it had no hulls), and
    `Sources/Belltower/editor/import-lorry-removal.cs.txt` published them, refusing any file changed since staging. The
    originals are in that folder's `stage/before/`.
  - No Retakes sightline crossed a lorry and no spot stood on one (`check_lorry_gameplay.py`). Market Street's north
    lane is more open without its cover.
  - Checked in an isolated editor scene: no collision at bed, cab or roof height where either stood, and the street's
    view down to the market cross. Not yet seen in a match.
  - The file watcher compiled both halves. Don't `Compile( true )` them by hand: a forced compile of `belltower_west`
    stalled the editor and it closed (2026-10-19), as the Railhead notes warn.
- The square's oak in each north corner (plan (-+560, 450), Facepunch's medium oak) came out on 2026-10-25 (the user's
  screenshot: "is it out of place? remove if so"). Its trunk stood 90 from the side house's shopfront and 100 from the
  north house's, and its crown (~336 across) went ~6 ft into both, over their shop doors and windows.
  - Its call is gone from `street_props` (it used its own seeded RNG, so nothing else moves on a rebuild).
  - `output/belltower/square-tree-removal/stage_square_tree.py` took the two "Oak tree" objects out of the scene and
    each trunk's 7-sided hull out of `belltower_{west,east}_hulls_wood.obj`; nothing else in those files changed.
    `Sources/Belltower/editor/import-square-tree-removal.cs.txt` published them (refuses while Belltower is open in
    the editor), and the watcher recompiled both halves. Originals are in that folder's `stage/before/`.
  - The scene's hash changed, so an older stage guarded on Belltower's scene hash refuses until it's staged again.
  - Checked in an isolated editor scene (`check-square-tree-gone.cs.txt`): no collision at either trunk, the shopfronts
    still hit, and a view of the cleared corner (`square-corner-after.png`). Not yet seen in a match.
- Coopered casks (v3, 2026-10-25, the user: the barrels looked "too perfect/round"). The old `Detail.barrel` was a
  48-sided tube curving in like a pill at both ends, its lid flush with the rim, thick black bands, every stave one shade
  and every barrel identical; v2's clock-frontage pair still had twenty equal staves. All 23 casks a side are now
  `Tools/belltower_barrels_v3.py`'s, as a cooper builds one:
  - staves of real widths (2.6-4.4 in) on one gentle arc, each its own shade (four tints of the furniture's oak scan),
    with V joints, standing ~1.6 in proud of a recessed head of 4-6 boards, their end grain and inside bevel showing;
  - 4 or 6 thin flat steel hoops (`sh_hoop`) with a riveted lap, rusted at the bottom or all over on some (a darkened
    `sh_rust`), a bung in one stave;
  - each cask slightly oval, slightly leaning and seeded by where it stands (`seed_for`), so no two match.
  - Its seven materials (`materials/belltower/barrels-v3/`) are existing pictures in their own tints: no new textures.
  - Drawn only: the ten-sided wood hulls stay. ~5.5k triangles a cask against the old 1,870 (127k a side), in three
    bounded imports a side (`models/maps/belltower/barrels-v3/<side>_<n>.obj`); the v2 import node is gone.
  - `Tools/belltower_stage_barrels_v3.py` took the old casks out of every import by matching their faces against each
    generator's template at the hull's centre (24,192 iron, 966 lid and 14,112 stave triangles from the bounded
    imports, 51,450 from the canonical record, a side), keeping every other line byte for byte. Two groups had casks
    standing into each other (centres 20.6 and 23.9 in apart): `V3.NUDGED` moves the third cask of each until they're
    27 apart, hull and all (`belltower_stage_barrels_v3_nudge.py`), both spots checked clear of the map's collision and
    every neighbouring pair ~1 in apart. `belltower_map.barrel` draws the same casks (checked against the published).
  - Published with `Sources/Belltower/editor/import-barrels-v3.cs.txt` and `-nudge.cs.txt` (hash-guarded, no scene or
    play change); the file watcher compiled the halves. Checked in isolated native renders
    (`capture-barrels-v3.cs.txt`, views in `output/belltower/barrels-v3/captures/config.json`): the market trio, the
    clock pair, the yard and tavern groups and the east market. Not yet seen in a match.
- It's in `GameUtils.MainMenuMapOrder` and `IsMatchReadyMap`. So the menus, Quick Play, the map vote and Ranked offer it
  with every mode but battle royale. Ranked plays it as Defuse, because the scene lists `bomb_defusal`.
  - Team spawns: 12 a side on the spawn roads. Deathmatch and Gun Game spawn players at any active spawn point,
    whatever its team, so the team spawns are off in those modes (`GameModeObject` with Inverse).
  - Free-for-all spawns: 33 round the town, on only in Deathmatch and Gun Game.
  - Retakes spawns, tagged like Refinery's (`retakes,<site>,<role>`). Each site has Red planters and defenders and
    Blue attackers. `ActiveBombSiteSelector` turns on the round's site. The mode's `TeamSpawnAssigner` puts one Red
    player on a `planter` spawn, and `SpecialWeaponAllocator` gives that player the C4.
    - No Red spawn can see a Blue one at either site, standing or crouched (checked against the script's collision on
      2026-10-01). The spawn deaths the user had came from every spawn being switched off (see Retakes and Defuse
      rounds).
  - Buy zones on the spawn roads, callouts for every area, the play area, and a player clip over the south parapet, so
    nobody jumps off the drop. A catch floor under the lowest land (`CATCH_FLOOR_Z`) stops anything thrown over the
    walls.
  - `MapSpawnSettings` turns off map spawn points and navmesh spawns: every spawn is placed.
- `ObjectiveSpot` (`Code/Maps/ObjectiveSpot.cs`) is a map's own place for an objective. Domination uses a map's spots
  when it has at least three, named by their labels. Hot Zone uses them whenever there are any. Otherwise both fall back
  to the spawn points, which on Belltower would put flags A and C in the spawns.
  - Belltower's flags: A in West Street, B in the square, C in East Street.
  - Its Hot Zones: Market, Council Hall, Square, Gardens, West Street and East Street.
  - Cash Grab's three points: the Market's cash is taken to the gardens, the Gardens' to the market, and the Square's
    up to the Council Hall.
- The land round the town (2026-10-02, the user's goal of an AAA look, after a reference picture of an Italian hill
  town): `Tools/belltower_vista.py` shapes it, and `belltower_map.py` writes it through `Vista.write_land`:
  `belltower_vista.obj` / `.vmdl`, one mesh with shared vertices (~338k triangles), drawn only, with no collision and
  no shadows. The old flat-shaded vista, with its farm buildings and trees, is gone.
  - Forced perspective (`SCALE`, `scale`, `apparent`, `real_place`): past 1200 out from the walls, a point d out is
    drawn as if it were scale( d ) times as far from the town's middle: 1.07 at 3000, 2.6 at the river and 8 at the
    land's edge, so 2.3 km of land plays a landscape 18 km deep. Patterns (fields, rows, districts) are laid out at the
    apparent place, and things (trees) are drawn round, at their real size over the scale.
  - Its lowest point is -5409. The catch floor is at `CATCH_FLOOR_Z` (-6500), and `belltower_map.py` asserts the land
    stays above it.
  - The current fog is `GradientFog`, alpha 0.6 from 2000 to 70000, falloff 0.75, height 25000, with vertical falloff
    1.2. Native overview captures use a ZFar of 100000 so the distant landscape remains visible.
- `Tools/belltower_vista_paint.py [--size N] [--zones abcd] [--out <dir>] [--sheet <png>]` paints the land's textures
  into `Assets/materials/belltower/vista/` with numba, from the land's own heights and slopes. A full run at 4096 takes
  about 3 minutes, numba's first compile included. `--preview <dir> [--views name ...]` renders the town's views
  (`belltower_vista.PREVIEW_VIEWS`) with the painted textures, per pixel as the shader picks the zones, with the town
  flat-coloured; with no `--zones` it paints nothing. On 2026-10-02 those renders from the terrace and the gardens
  showed wooded hills with clearings, a patchwork of fields in the valley and blue haze towards the far hills. None of
  it had been seen in the engine at that time. The 2026-10-14 quality pass subsequently inspected it in native captures.
  - Four nested zones, A by the walls out to D at the horizon (texels of 1.9, 3.9, 17.8 and 46 units at 4096), each a
    colour JPG, a kind PNG (grass, soil or stone) and a normal JPG, plus three tiling detail textures and
    `vista_land.vmat`.
  - What it paints: districts of irregular fields (warped, stretched Voronoi cells, their crops by the land: plain,
    hill farms, vines, uplands), with hedges, tracks, ditches or trees between; olive terraces; vineyards; woods; scrub
    and rock on the steepest slopes; the river.
  - Every tree is a spheroid crown, shaded per channel by the sun and the sky, with its sun shadow (the sun is to the
    west-south-west, so shadows fall east-north-east). Crowns smaller than a texel are averaged into the ground.
  - `shaders/hc1_vista.shader` picks the zone by how far out from the town a point is (Chebyshev), blends the zones
    over 12% of each, adds the detail textures near the walls (fading from 700 to 2600 out) and sets the roughness by
    kind.
- `Tools/belltower_vista_props.py` builds the vista's buildings and trees, drawn to the vista's forced perspective
  (`World.k_at`): a walled hill town with its gate, a villa with its walled garden and cypress avenue, a village,
  farms, chapels, and cypresses and pines. `belltower_map.py` writes it (`belltower_vista_props.obj` / `.vmdl`, ~53k
  triangles) as the scene's "Vista Props", drawn only, with no collision and no shadows.
  - The painter grounds it (`World.paint_data`): the yards (a town's paving and kitchen gardens, a farm's beaten earth,
    the villa's parterre, gravel), the white roads out of the gate and down the avenue (`winding_road`), and the
    buildings' and trees' shadows. It clears its own painted trees off all of that (`clear_crowns`). `--no-props`
    leaves it all out.
  - After changing the props, run `belltower_vista_paint.py` (the repaint, ~1.5 min), then `belltower_map.py`.
  - First checked in the painter's previews (2026-10-02), then in native engine views during the 2026-10-14 pass.
- `Tools/belltower_sky.py` is the legacy generated sky. The current scene uses the original photographed
  `kloppenheim_05_puresky_hdri_4k.exr` through `materials/belltower/sky/afternoon_scan.vmat`.
- `Tools/belltower_finishes.py` draws the houses' finishes, like the lime render (`plaster_<colour>`, anchored at the
  ground: rising damp, salts, splashed mud, render blown off). `Tools/belltower_fronts.py` draws the shutters, windows,
  doors, shop signs, railings, plants and painted lettering, as decal paints at their real size in the project's own
  fonts.
- Three houses in four have painted window surrounds (cornici, `belltower_map.SURROUNDS`): a pale band round a
  coloured house's windows, grey stone round a pale one's, each with a little hood over its head that throws a line of
  shadow (`dress`). They're drawn only, with no collision. Checked in the script's flat previews (2026-10-02).
- The gutters and downpipes are copper's brown oxide (`copper_brown`, a second colour of building_textures' copper
  sheet): the tower roof's verdigris read as bright teal along every eave. The market stalls' counters are two tiers
  of slatted crates on a pallet (`crate_counter`), drawn over the stall's own collision box, so the cover is the same.
- Market-stall canvas (2026-10-20, user: red/white canopy too straight): `belltower_stall_canvas.py` supplies a shallow
  sag between the existing posts, small corner tension folds and a soft curled valance. Continuous cloth UVs bend
  the existing eight-inch stripes over the shape. `stall` delegates only its roof/flap to this helper; the counters,
  produce, posts, RNG sequence and gameplay collision are identical. `belltower_stage_stall_canvas.py` surgically
  replaced 72 old fabric triangles per half with 16,848; every unrelated OBJ byte and the VMDLs/MTLs are unchanged.
  Both OBJs were imported through the native editor with guarded backups. The editor subsequently closed; final
  resource compilation and after screenshots remain unverified. `Sources/Belltower/props/stall-canvas-v1.json` and
  `output/belltower/canopy-cloth-v1/` record the pending check, native import and preservation evidence. Do not infer
  native visual acceptance from the old, flat before images or force-compile the large town models.
- Some street doors have terracotta pots with clipped bushes beside them (`door_pot`: building_textures' `clay_pot`,
  the beech bush scaled down). Each has a collision box the pot's size.
- Its look (the user: it "doesn't look AAA", the textures and the low-poly plants, 2026-09-29):
  - `Tools/belltower_materials.py` retains the older procedural canvas and produce materials. Material names owned
    by `belltower_quality_materials.py` delegate to those photographed definitions so regeneration preserves them.
    The cobbles and flagstones also use scans. `--out <dir> --sheet <jpg>` stages the older painter's output elsewhere.
    `g_flRoughnessScaleFactor` is an exponent, so values below 1 make the material rougher.
  - `Tools/belltower_detail.py` has the props and the material each paint uses (`MATERIALS`, `TILES`):
    - the café's bistro tables and chairs under gored parasols with scalloped valances;
    - Blue café spacing (2026-10-21): `belltower_cafe_spacing.py` translates three eastern seating groups and
      removes the fourth, leaving 43 inches between the closest canopy edges. The red café is unchanged.
      The main generator and `belltower_quality_models.py` apply this after mirroring the east half. The surgical
      import changed only the blue café's render faces and four table hulls; native physics checks found the
      three new table tops at 29 inches and clear ground at all four former locations. Successful compilation,
      import receipts and matching before/after captures are under `output/belltower/cafe-spacing-v1/` and
      `output/belltower/quality/cafe-spacing-v1-{before,after}/`.
    - the stalls' crates of produce;
    - the foliage: Facepunch's cloud oaks and beech bushes, which the scene's `__references` list.
  - A crate of produce is a low, lumpy mound under a tiling picture of the heaped fruit (`produce_<kind>`: two layers
    packed hexagonally, dark gaps, stalk ends, apples' and onions' streaks running from the stalk). Up to six whole
    fruit lie on top, drawn with `produce_skin`, their kind's skin alone. The pile's picture has each fruit's roundness
    in its normals, which would count twice on a round fruit.
  - Round things (fruit, the furniture's bars) have a normal per point (`map_kit.Model.polygon`'s `normals`), so they
    shade smoothly.
  - Checked only in Cycles renders of a run into scratch (2026-09-29). Assets got the new models and materials on
    2026-10-02.
- Every run checks all 94 spawn, objective and cash spots:
  - `check_spots`: room for a player and a floor under each spot;
  - `check_reach`: a way to walk there from the spawn roads. It uses a 2.5D grid of the collision's level tops, kept 16
    from anything in the way like the navmesh, and stands in for the navmesh while the editor is busy. `--preview <dir>`
    also writes its picture (`reach.png`).
  - On 2026-09-28 both passed. The Council Hall and the Inn's and Tavern's upper floors are joined to the streets.
- The menus' picture (`ui/maps/belltower.png`) is a native 1920x1080 capture of the tower, square and fountain.
  `import-map-art.cs.txt` validates the PNG dimensions and preserves the original before importing it in the editor.
  The generator only writes its old placeholder if no map image exists.
- Fountain carvings (2026-10-21): `belltower_fountain_ornaments.py` supplies four solid limestone lion masks,
  four upper lilies and eight basin lilies, following `output/belltower/fountain-ornament-concept-v1/`.
  The old ellipsoids used a reflected frame without reversing winding, so their exterior faces were culled.
  The replacement checks transformed winding, uses one connected, closed 18,000-triangle lion sculpt and
  rounded leaf sections for the lilies. The bronze outlets meet the existing water spline at local `(0,10,42)`.
  `belltower_fountain.py` delegates its ornament calls to this helper; water, masonry and collision are unchanged.
  The sculpt source is signature-checked in `Sources/Belltower/props/fountain-ornaments-v2/lion-*.npz`.
  After changing the sculpt, run `python Tools/belltower_bake_fountain_lion.py --prepare`, then background
  Blender with `--factory-startup --threads 2 --python Tools/belltower_bake_fountain_lion.py -- --blender`.
  This prepares source geometry; Blender is not a game dependency. The signature includes a bake-version tag.
  `belltower_stage_fountain_ornaments.py` performed the one-time legacy upgrade, removing exactly 17,832
  triangles and adding 121,164, while preserving every unrelated canonical OBJ byte and all existing materials.
  The centre VMDL now uses 42 bounded render imports (at most 65,000 triangles each) under
  `models/maps/belltower/fountain-ornaments-v2/centre/`, retaining its material remaps and physics nodes.
  The guarded native import and successful incremental compile are in
  `output/belltower/fountain-ornaments-v2/revision4/`. Native before/after views of the lion, lily and whole
  fountain are in `output/belltower/quality/fountain-ornaments-v2-{before,after}/`; camera, exposure,
  scene objects and editor state were restored. The first three construction revisions were not published.
- Fountain bell quality (2026-10-21): `Tools/belltower_bell.py`, called by `belltower_fountain.py`, owns the smooth cast
  profile, hollow inner shell, rounded crown loops and dedicated `materials/belltower/bell-v2/` bronze. A guarded native
  import replaced only 2,394 old bell triangles with 30,564, preserving every other centre OBJ byte, the timber yoke,
  collision, scene, water and shared bronze fittings. Materials and centre model compiled successfully; the new materials
  were confirmed loaded and visually checked in live Belltower. `Sources/Belltower/fountain/bell-v2.json` links the receipts.
- Theater doesn't record it: there's no MapInstance for playback to load (`MatchRecorder.CanRecord`).
- To play it: `dev_mode team_deathmatch belltower` (any mode's prefab name or ident).
- The 2026-10-14 pass checked native street, square, landscape and interior captures, successful asset/code compilation,
  and the 94-spot collision/reachability checks. A short live performance sample preceded the 1,600 landscape trees;
  it is not a benchmark for the final map. Full bot, mode and runtime navmesh validation remains separate work.

