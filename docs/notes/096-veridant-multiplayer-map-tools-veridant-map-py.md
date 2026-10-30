## Veridant (multiplayer map, `Tools/veridant_map.py`)
- Spa windows (2026-10-25): `Tools/veridant_spa_windows.py` replaces the nine
  flat opaque/emissive spa panes with recessed masonry openings, bronze frames,
  glass and shallow furnished rooms with folded linen curtains. The two facade
  faces and old window/fixture faces are removed only from the active buildings
  base OBJ; `spa-windows-v2/spa-facades.obj` supplies 43,420 replacement triangles.
  Original OBJ indices, other imports and the complete physics suffix remain.
  `spa()` retains the original two collision boxes and four lamp identities;
  those lamps are now below the sills, with their native scene positions saved.
  Only those four scene Position properties changed from the immediate backup.
  `configure()` preserves `vr_spa_` materials. Final stage-v4, thirteen successful
  native compiles and three reviewed captures are recorded in
  `Sources/Veridant/spa-windows-v2/README.md` and its installed receipt.
- Pergola flowers (2026-10-24): `veridant_parts.bougainvillea()` delegates to
  `Tools/veridant_bougainvillea.py` for branching vines, folded green leaves and
  small shaded pink bracts. The six old atlas cards (24 triangles) are removed
  from a byte-preserved `pergola-flowers-v2/foliage-base.obj`; the foliage VMDL
  also imports `pergola-flowers-v2/flowers.obj`. Original foliage indices, atlas,
  scene and collision are preserved. `configure()` keeps the `vr_bv_` material
  overrides. Final stage-v5, native compile receipts and front/angle captures
  are documented in `Sources/Veridant/pergola-flowers-v2/README.md`.
- Garden table planter shrub (2026-10-24): the single olive at (-470,740,148)
  now uses `Tools/veridant_planter_shrub.py` with the installed beech shrub's
  authored mesh/material, finer branches, embedded roots and textured soil.
  The canonical foliage OBJ and active `pergola-flowers-v2/foliage-base.obj`
  both replace precisely 466 old triangles with 2,972; retained bytes and index
  mappings are preserved. Scene and physics stay unchanged. Native compilation,
  live material checks and matched captures passed. See
  `Sources/Veridant/planter-shrub-v1/README.md` and its installed receipt.
- Lounger upholstery realism (2026-10-24): `Tools/veridant_lounger_soft.py` adds
  crowned and compressed foam, irregular cloth outlines, smooth seam pulls,
  piping/stitches and rounded, subtly varied teak sections. The existing lounger
  generator delegates to it, and all eight dedicated lounger imports plus the
  reusable prop are updated through their existing `lounger-v2` resource paths.
  Model documents, physics, scene, shared map OBJs and other prop imports retain
  their hashes. Final publication: `output/veridant/lounger-v3/stage-v3/manifest.json`.
  Seven materials and three models compiled; garden and rooftop captures were
  reviewed. See `Sources/Veridant/lounger-v3/README.md` and the validation receipt.
- Bistro tables (2026-10-24): `Tools/veridant_table.py` supplies the 128-segment honed stone top with a 3 mm eased
  edge, a 64-segment bevelled pedestal base and a 32-segment stem. All 11 published tables retain their 30-inch
  diameter, 29.5-inch height, 1.5-inch slab thickness, placements and collision. The tabletop's own material uses
  restrained relief and UVs inside one limestone panel; OBJ import flips V, so source V=.75 becomes engine V=.25.
  Scoped imports and native mesh/UV/rim checks are in `output/veridant/table-v2/`; the reviewed final view is
  `output/veridant/quality/table-v2-complete/angled.png`. Resolve current VMDL render imports when patching: the
  dressing now uses `chair-v2/dress-base.obj`. These OBJs contain interleaved vertex tables; append new tables
  after all retained bytes so existing vertex, UV and normal indices keep their original meaning.
- West bar doorway clearance (2026-10-24): `shelves_beside_doors()` keeps shelving
  outside the cafe entrances at N=-80 and N=100 and lounge entrance at N=-390,
  using the wall's shared 60x96 inch doorway definitions plus 4 inch jamb margins.
  The active buildings render import is `lounger-v2/veridant_buildings-base.obj`;
  its shelf correction and the canonical OBJ retain subsequent lounger work.
  `stage-v5-index-repair` restores the original OBJ index allocation while keeping
  face/material records unchanged. Sparse patches must append new tables after
  all original tables, including declarations after faces. Native compile and
  27 doorway collision rays passed; final evidence is in
  `output/veridant/door-obstruction/validation.json` and
  `output/veridant/quality/door-obstruction-after-repaired/cafe-south.png`.
- Bistro chair clearance correction (2026-10-24): `Tools/veridant_chair.py` now
  routes the rear uprights behind the backrest and around the seat. Rear mounting
  spacers replace the collars that pierced the wicker. All 12 instances use the
  two `models/maps/veridant/chair-v3/chairs-*.obj` imports, at 4,480 triangles each.
  The chair-v2 base and current lounger import remain. See
  `Sources/Veridant/chair-v3/README.md` and `output/veridant/chair-v3/after/` for
  front, rear and side close-ups. Scene placement, materials and physics are preserved.
- Bistro chair rebuild (2026-10-24): `Tools/veridant_parts.chair()` delegates to
  `Tools/veridant_chair.py`; all 12 published chairs now have curved wicker panels,
  rounded bound edges and smooth tapered steel legs. `veridant_materials` generates
  the 1024px wicker PBR maps. The dressing model references two six-chair imports
  and `models/maps/veridant/chair-v2/dress-base.obj`; physics and scene placements
  are preserved. See `Sources/Veridant/chair-v2/README.md` and the final stage-v8
  manifest. Existing Veridant OBJs interleave tables and faces: append new table
  declarations after all old data, since inserting before the first `usemtl`
  shifts indices in later declarations. Final editor captures are under
  `output/veridant/chair-v2/final/`.
- Inland hillside image backdrop (2026-10-24): `Tools/veridant_inland_vista.py` removes the remaining box villas and
  polygon trees after the bay-impostor pass. Three distinct photographic sectors from one RGBA atlas (288 triangles total,
  radius 14000) replace the earlier enlarged picture. Each keeps equal world scale per image pixel; uniform vertical
  translations match the ridge heights. `mainland_arc()` derives the bearings from the actual coast at that radius
  (currently -140.945 to 73.831 degrees), preventing scenery from being placed offshore. The horizon shader blends
  adjacent image samples in texture space, preserving full interior coverage; only the two outer ends fade into haze.
  ModelDoc flips the OBJ's V coordinates, so shader atlas samples use top-down PNG row order directly.
  `Tools/veridant_vista_ground.py` builds a closed rolling mainland outside the play rectangle with separate cliff faces,
  smoothly shaded normals, a continuous grass/soil material and 180 photographic scrub clumps (720 triangles). A coarse
  backing extends to radius 60000 so elevated inland views cannot expose the sea behind low photographic valleys.
  Clipped triangles interpolate their original plane, and scrub bases sample those actual triangles. There is no photo
  projected on the ground. The two backdrop meshes total 32,438 triangles, down from 164,312 (80.3% fewer); FPS is unmeasured.
  The near sea wall/riprap and original bay/boat cards remain byte-for-byte. No scene, physics, water, camera, lighting,
  probe or gameplay changes were made. `veridant_backdrop.build()` applies the replacement; the material generator's
  `impostors` command writes its five materials and two exact generated PNGs. Active shaders are
  `hc1_veridant_horizon_v4.shader` and `hc1_veridant_scrub_v3.shader`. Sources, both built-in imagegen prompts, alpha
  measurements and native scripts are in `Sources/Veridant/inland-vista-v1/distance-fix/`; published textures are
  `materials/veridant/vista/inland-v1.png` and `inland-scrub.png`. The guarded native import atomically replaces existing
  sources to avoid overwriting files mapped by the model compiler. Final stage: `output/veridant/inland-vista-v1/distance-fix/stage-v26/`;
  original meshes remain in the parent run's `before-assets/`. Native shader/material/model compiles and 13 isolated
  captures passed (`distance-fix/after-v26/`). Verification measured less than 0.05% per-sector pixel-scale variation
  and zero internal cracks across 766 ground boundary edges; the source scene and stopped play state were preserved.
- West bar door clearance (2026-10-24): the cafe's two west entrances and the lounge's west entrance were hidden
  behind the continuous wooden backs of `counter_shelves`. `shelves_beside_doors` splits complete shelf units,
  bottles and LED strips around the shared wall-opening definitions, with 4 in of jamb clearance. Only those two
  assemblies were patched in `veridant_buildings.obj` (3,432 triangles replaced by 1,926); all unrelated OBJ bytes,
  materials and physics sources were retained at publication. This task did not write the scene or physics sources.
  Native compilation and 27 collision rays across the three openings passed; a matched screenshot verifies the
  doorway in the user's picture. An optional player-box sweep timed out and is not claimed as passed. Other capture
  attempts overlapped unrelated shared asset recompiles. `Sources/Veridant/door-clearance-v1/installed.json` and
  `output/veridant/door-obstruction/validation.json` record the import and verification.
- Pine planter bushes (2026-10-24): the north terrace's leaning stone pine now has 12 grounded beech bushes
  (`facepunch.beech_bush_small#145429`, also used on Belltower), replacing its 15 crossed grass clumps. Only the
  exact 120 old grass triangles were removed from `veridant_foliage.obj`; the tree and collision stay.
  `Tools/veridant_planter_bushes.py` defines the varied placement and root embed, and `veridant_map.py` retains
  the instances and package reference on regeneration. Saved native scene group: `Veridant/Pine planter beech bushes`.
  Before/after captures and the scoped verification are in `output/veridant/planter-bushes-v1/`.
- Distant bay image impostors (2026-10-18): `Tools/veridant_impostors.py` replaces the headland, castle/town and
  anchored boats with two generated RGBA textures in `Assets/materials/veridant/vista/` (`headland.png`, `boats.png`).
  The headland is a fixed curved strip (96 triangles); the yacht and nine sailboats have separate fixed quads at
  their anchorages (20 triangles). The mainland, near shore and sea stay in 3D. The two backdrop models went from
  346,103 to 164,312 triangles (52.5% fewer); no frame-rate benchmark was taken.
  `veridant_backdrop.build()` applies the replacement by default; `build(impostors=False)` retains the old mesh
  construction below. `veridant_materials.py impostors` writes the two materials. Their custom shader reads the
  PNG alpha directly, uses diffuse lighting without flat-panel specular, and retains native fog/depth coverage.
  For this scoped import, `--stage output/veridant/impostors/stage --source
  output/veridant/impostors/before-assets/Assets/models/maps/veridant` used the actual original meshes so retained
  geometry/UVs did not get regenerated. Native import/compile scripts and the built-in imagegen prompts are in
  `Sources/Veridant/impostors/`. Compile the shader before its materials. Veridant's existing sea/pool materials
  were recompiled against the current water shader to clear stale checkerboard rendering; their sources were not
  edited. Four engine captures are in `output/veridant/impostors/after/`; the scene file and the user's active
  Spillway scene/play state were preserved. Original assets are in `output/veridant/impostors/before-assets/`.
- The user asked for a multiplayer map "as close to this img as possible" (2026-10-15). The picture is a Mediterranean
  cliffside resort at sunset after rain:
  - a wet courtyard round a dark reflecting pool with a boulder;
  - on the left an operations building with a pergola, ivy and a SECURE / EXPLORE / CONTROL banner;
  - behind the pool a gallery lounge and a colonnaded cafe with a roof terrace;
  - on the right the VERIDANT RESORT pylon, an uplit olive in a planter, a grand stair with LED nosings, a furled
    burgundy umbrella and a stone pine;
  - black and olive military cases about the courtyard, a tarp over a railing in the foreground;
  - the bay: the sun on the horizon, a superyacht, sailboats, and a cliffed headland with a castle on its summit.
  Veridant Resort, its three-wave mark and every marking are the picture's made-up names.
- Built by script like Belltower and Riverdale (`map_kit`). Run in this order:
  - `Tools/veridant_materials.py [names] [--out <dir>]`: the vr_ materials, drawn with numpy (boxyard's and
    riverdale's helpers) into `Assets/materials/veridant/`.
    - `painted derived tints` rewrites only the text vmats: the flat paints (`PAINTED`), the tinted copies of another
      surface's maps (`DERIVED`) and the surfaces' tints and roughness exponents (`SURFACE_TINT`, `ROUGH_EXP`), which
      change a surface without redrawing its maps.
    - `g_flRoughnessScaleFactor` is an exponent: the wet paving's 1.45 makes it glossier.
  - `Tools/veridant_sky.py`: the sunset panorama, an 8192-wide EXR on belltower_sky's code. `--width 2048 --no-write
    --preview <png>` shows it as the hero view sees it in about 20 s.
    - The editor took about four minutes to compile the 18 MB EXR, during which the shared editor was frozen (it
      happened once during the user's match). Rebake only when nobody is playing.
  - `Tools/veridant_map.py [--preview <dir>] [--views ...] [--no-scene] [--no-models] [--no-backdrop] [--art]`, with:
    - `Tools/veridant_parts.py`: the resort's pieces on riverdale_parts (stairs with LED nosings, glass and steel
      railings, the tarp, lamps, olives, palms, the stone pine, cases, the pylon, furniture);
    - `Tools/veridant_backdrop.py`: what's seen round the resort, drawn only, in two models: the land (179k triangles,
      39 MB) and what stands on it (167k, 44 MB). map_kit writes each polygon's own vertices, so one model came to
      100 MB: the land's cells are single quads and the clumps five-sided domes to keep both under GitHub's 50 MB
      warning. They are:
      - the sea, and the land as polar meshes;
      - the headland as its own mesh along its crest. Its limestone bosses and crags come from point-sampled noise
        (`vnoise`, `vridged`); its ledges are off (at the mesh's spacing they read as stripes from the promenade).
        Its outcrops are sampled in 3D (`vfbm3`), so they're round in the view rather than
        streaks down the flank. Its steep sea cliffs are bare grey rock, with ~5,300 maquis clumps and ~260 stone pines
        on its skyline;
      - the summit's castle and village, the town on the headland's north shore, the superyacht and sailboats;
      - garden terraces with olive groves rising behind the resort's walls.
    - The scene is rewritten whole on every run: change the layout in the script, not in the editor.
- Layout (plan e, n, z inches; the play area e -1750..1900, n -1350..1000). Levels: the ground (0), 128 (the cafe's
  roof, the garden terrace, the north terrace, the operations building's balcony and lobby, the lounge's gallery) and
  192 (the east terrace). Red Team spawns on the seafront promenade (west), Blue Team in the entrance forecourt (east).
  Three lanes:
  - North: the promenade's stair to the garden terrace, the north terrace (bomb site A, with the stone pine, the bar and
    the umbrella), the head of the grand stair, the east terrace, down to the forecourt.
  - Middle: through the cafe (or over its roof) into the courtyard round the pool, then the colonnade under the east
    terrace to the forecourt. The grand stair and the reception's inner stair climb to the north terrace.
  - South: the gardens (bomb site B among the olive groves at their east end) to the east plaza, or through the
    operations building's hall and up its stair to the lobby and the balcony.
- Modes: the scene lists TDM and Defuse, and it's in `GameUtils`' three map lists (after Collider). It has 36
  deathmatch spawns, Retakes spawns for each site, Domination flags (A the cafe, B the courtyard, C the east terrace),
  Hot Zones and three Cash Grab points (`ObjectiveSpot`s).
- The picture's camera is `HERO`: on the east terrace behind its glass, (801, -40, 256), looking west 9.6 degrees down,
  74 degrees across.
- Checks:
  - Every run checks the 97 spots with railhead_map's `check_spots`, `check_reach` and `check_retakes_sight`: all pass.
  - `Sources/Veridant/editor/navmesh-check.cs.txt` (run_csharp) generates the navmesh in an isolated editor scene and
    paths from the first Red and Blue spawns to every spawn, site, objective and cash point: 99 of 99 Complete.
    `Scene.Deserialize` doesn't apply the scene file's navmesh settings, so the script sets them from the JSON.
- Garden hedges (2026-10-18, the user's "use the bushes from cerroblanco"):
  - The eight low borders and five tall screens use Cerro Blanco's Facepunch
    `models/sbox_props/shrubs/beech/beech_hedge_96x128.vmdl` instead of visible `vr_hedge` boxes. `garden_hedge`
    in the map generator places 88 overlapping, opposed leaf sections under `Veridant/Beech Hedges`;
    `write_scene` records `facepunch.beech_hedge_96x128#145491` so regeneration retains the cloud dependency.
  - The original garden collision boxes, surfaces and all other dressing geometry stay. The live dressing OBJ
    lost only its 156 hedge triangles; its VMDL and physics sources are unchanged. The model compiled, all 88
    instances load with valid materials, and the generator's 97 spot, route and Retakes checks pass.
  - `output/veridant/cerroblanco-bushes/` holds the pre-change sources, staging manifest and reviewed native
    tall-hedge, low-border and garden overview captures. The scene was saved through the editor.
- Terrace stone pine: `veridant_parts.stone_pine` delegates to `Tools/veridant_stone_pine.py`. The old flat dark disc
  and oversized foliage planes are replaced with branching limbs and 13 separate mountain-pine sprays from
  `facepunch.pine_shrub_wide#145484`; their exported mesh/provenance is in `Sources/Veridant/stone-pine-v2/`.
  `veridant_map.configure` preserves its cloud material override and `write_scene` pins that dependency. The scoped
  splice (`Tools/veridant_stage_stone_pine.py`) replaced 606 triangles with 30,310 and retained the other 41,946 foliage
  triangles exactly; no collision or scene transforms changed. Native import/verification scripts are under
  `Sources/Veridant/editor/*stone-pine-v2*`; reviewed map captures and checks are in `output/veridant/stone-pine-v2/`.
- Player clips: a clip's BoxCollider turned to its rail's heading (`K.yaw_rotation( yaw - 90 )`) lies along its local
  x, so its Scale is ( length, thickness, height ). Checked in the engine: with the length on y every path through the
  terraces came back Partial. Riverdale and Riverside write ( size[1], size[0], size[2] ), which lays each of their
  clips across its rail.
- Light and exposure, matched to the picture region by region (its colours against offscreen renders):
  - The engine's exposure runs at about twice belltower_sky's design scale: at a fixed exposure of 4.0 the sky showed
    the colours it was designed for at 2.0. So the sky is baked for 1.1 and the tonemap holds 2.1-2.4.
  - The sky still reads about a fifth darker in the engine than in its own preview (the fog over it), so the SkyBox2D's
    Tint is 1.32.
  - The lamps (`veridant_parts.WARM` and the rest) were first 1.75,1.10,0.58: the pylon and the grand stair read twice
    the picture's brightness, and renders with the lamps off showed the lamps gave most of it. They're about 0.56 of
    that now, so the light pools stay pools. The pylon is lit from its foot only, as in the picture. 108 point lights,
    5 with shadows.
  - The fog is a neutral mauve-grey (`FOG_COLOUR`): a pink one turned the headland brown.
- `Sources/Veridant/editor/` (run each with the native MCP's run_csharp, `{"path": ...}`):
  - `register.cs.txt` registers and compiles the materials, then the models, then the scene;
  - `compile-stale.cs.txt` force-compiles anything whose source is newer than its compiled file;
  - `capture.cs.txt` renders the views in `output/veridant/captures/config.json` offscreen, without touching the open
    scene. A view with `"art": true` also writes the menu picture, `ui/maps/veridant.png`. `fixed_exposure` pins the
    tonemap, and `disable` switches off components by type name (diagnostics: "PointLight", "DirectionalLight").
    `config.main.json` has the hero, menu, sea and aerial views and `config.play.json` views from where players stand
    (the Red spawn, the terraces, the gardens, the forecourt): copy one over `config.json`.
    `compare_reference.png` there is the picture beside the hero view.
- The user played a TDM on it in the editor for a couple of minutes on 2026-10-15 (Red Team, with bots); the log showed
  no errors. Not yet checked: the other modes' objects in a match, a second client, and its frame time with the
  backdrop and 108 point lights.

