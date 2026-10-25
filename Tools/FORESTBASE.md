# Forest Base

Playable S&box military forest compound built from the five supplied reference images.
The compact main footprint is approximately 79 × 74 m, with a sealed entrance spur.
Only four main structures are used: motor shelter, barracks, command and workshop.
The surrounding forest, cliff and waterfall are inaccessible scenery.

## Open and play

Open `Assets/scenes/maps/ForestBase/forestbase.scene` in S&box and press Play.
Forest Base is registered in the existing map selection and match-ready map filters.
The scene includes TDM and Bomb Defusal, buy zones, two bomb sites, 16 team spawn
points, 16 free-for-all points, Retakes points and callout zones. Auxiliary objective
zones are provided for the project's Domination and Hot Zone systems.

Editor console mode checks:

```text
dev_mode tdm forestbase
dev_mode bomb_defusal forestbase
dev_perf 600
```

After regeneration, use `dev_mode` to launch the map through the normal match
launcher. An already-open editor tab can retain older scene roots when selected
again; the 18:23 inspection had no SSR volume and its timing is excluded from
the performance evidence. The subsequent match reload contained the volume.

## Rebuild

The four barracks beds now use tubular steel frames with feet, smoothly shaded
rounded mattresses and pillows, mattress welts and a folded, draped wool blanket.
Three dedicated 512-pixel PBR textiles replace the former tarp/plaster cuboids.
Rebuild those surfaces with `python Tools/forestbase_materials.py --beds`, then
`python Tools/forestbase_map.py --no-trees --chunks barracks`. The barracks chunk
has 52,638 triangles after the facade revision and retains its 299 collision boxes. The full nine-chunk
collision definitions are exactly identical to the preceding revision, recorded
by `python Tools/forestbase_bed_audit.py` in `bed-collision-parity.json`.
The preceding lighting, room and roof evidence is preserved in
`output/forestbase/atmosphere-passed/` and `atmosphere-integration-audit.json`.
The revised beds' engine images and native checks are preserved in `beds-passed/`
and `bed-integration-audit.json`; run the bedding audit with `--engine` to snapshot
fresh successful native reports after running both QA commands.

The scene and static building geometry are generated. Change layout in
`Tools/forestbase_map.py`; rerunning it replaces the generated scene and models.
Use Python with NumPy, Pillow and SciPy. The checked-in game assets do not need
Blender or the large source downloads at runtime.

```text
python Tools/forestbase_materials.py
python Tools/forestbase_shore.py
python Tools/forestbase_map.py --no-trees
python Tools/forestbase_validate.py
```

`--no-trees` preserves the imported conifer models; it skips the older fallback-tree
asset generator. Scanned material overrides are applied automatically when their
materials exist. The geometry is split into nine static chunks. Pine and rock
models have three ModelDoc LOD groups. Visual detail uses simplified box/hull
collision rather than per-triangle physics.
For a visual change limited to existing chunks, use a partial rebuild:

```text
python Tools/forestbase_map.py --no-trees --chunks motor workshop yard logistics
```

This retains other model files and the existing minimap, while collecting all
collision data and regenerating the complete scene. Use a full rebuild when
changing the footprint or layout. The collision validator drops unused visual
faces and uses float32 work arrays. NumPy defaults to one OpenBLAS thread unless
the environment already specifies a value. These changes reduce generation and
audit memory; they do not establish an in-game performance improvement.
Temporary prop models now inherit the collision-only mode, skipping canopy,
rim and pipe tessellation when auditing physics. A paired build verified identical
boxes/hulls across all nine chunks and identical scene metadata. The full visual
build took 22.19 seconds and the collision-only build 1.37 seconds in this finite
comparison; see `vehicle-collision-build-parity.json`.
Near and middle pine LODs retain needle geometry; only the far LOD adds crown
impostors. The source twig alpha mask removes opaque atlas borders. Balcony and
bridge rails use individual physical bars and posts.
The current backdrop uses the narrower Fir Tree 01 variants throughout. The former
38 broad pine placements were replaced while preserving placement seeds and roots. Fir near meshes contain 31–55k
triangles, middle meshes 22k, and far crossed-crown cards six triangles. Saplings
use 10k/4k/six-triangle levels. Fir impostors retain source atlas alpha and baked
local branch occlusion, without baking a fixed sun direction. Their ModelDoc
thresholds are 350/1400 for mature firs and 200/500 for saplings; these are engine thresholds, not stated distances in metres.
Young firs grow on a sloping leaf-litter bank behind the fence. Tree placement uses
separate seeded random streams, keeping the existing rocks and compound reproducible.
The fir importer verifies downloaded MD5 hashes; `--finalize` reuses exported
geometry and bakes. Its Blender path can be changed at the top of the importer.
The current generated backdrop contains 181 foreground firs, 81 saplings,
79 middle-background firs and 96 distant firs, plus four Mountainside escarpment
instances and two sunk distant Mountainside shoulders. The middle/distant placements
use dedicated dimensional branch models, detailed below. Earlier revisions used 82 scanned rock instances. The historical 20:15 engine overview retains branch
geometry where the initial 50/110 thresholds showed conspicuous flat crowns.
Its model/spawn/boundary checks passed, and the eight-unit route grid still
reported 123,064 reachable cells with no problems. This is visual/collision
evidence, not a performance measurement for the new vegetation.
At 21:19, the fir importer was corrected after the waterfall close-up exposed
opaque triangular foliage. The source firs stored `UVMap` as a generic three-
component corner attribute; Blender's OBJ export omitted it. The importer now
converts those authored values into a real UV layer before baking and decimation,
and rejects exported meshes with missing texture coordinates or untextured faces.
All nine fir LOD exports now have valid UV references; triangle counts and bounds
are unchanged. Three fresh isolated engine renders passed with no model errors,
and the 21:20 map views show textured green needles instead of opaque dark faces.
The older fir screenshots/timings predate this correction. Source-attribute and
export checks are saved in `fir-source-uv.json` and `fir-uv-export-audit.json`.
Facade walls use the wall scan, while foundations retain the floor scan.
The asphalt shader varies wetness in world space, and the scene includes an
infinite SSR volume for rain reflections. These remain subject to visual review.
Scanned mud tracks blend into the vehicle lanes without adding collision steps.
The inaccessible forest has a leaf-litter surface at tree-root height, with the
entrance gorge left open below it. Shipping containers have two door leaves,
locking rods, hinges and corner castings; cases have lid ribs, handle wells,
latches and authored cargo labels. The existing cover collision volumes remain.
Exterior walls have folded window sills/rain hoods, doorway trim, round drainpipes
and gutter elbows, guarded bulkhead light housings, distribution cabinets and
conduits. Window openings that overlapped a doorway no longer leave a floating
sill through that entrance. Rooftop HVAC has louvers, fan blades and guard rings;
the equipment and satellite dish use fine satin coatings rather than structural
plate or concrete textures. The existing HVAC cover bounds remain.

The four canvas transports have rounded canopy shoulders, sag between support
bows, gathered rear flaps, rim recesses, cab fittings and authored unit stencils.
The eight-wheel armored vehicle has sloped armor with matching convex body hulls,
round turret/barrel geometry, hatches, engine louvers, suspension, fenders and
radio whips. Front lamps now follow the actual sloped bow; the former mounts lay
inside the hull. Thin service panels and fasteners follow the armor planes.
Dedicated vehicle paint, metal, rubber and canvas materials use irregular lower
body road grime. Separate material keys preserve the building/case bindings.
Run `python Tools/forestbase_vehicle_materials.py` to regenerate only these
surfaces; the default material rebuild also invokes it.
All 37 wheels have twelve-sided convex rubber proxies. Four native traces check
two wheels block and their adjacent underbody gaps remain open. Flat rim-recess
disks removed 20,128 triangles compared with the initial capped-cylinder detail.
Current motor/workshop/yard/logistics chunks contain 45,230 / 34,064 / 64,312 /
59,804 visual triangles and 16 / 9 / 20 / 4 collision hulls respectively. A
verified `--chunks yard` rebuild preserved 61 other model/minimap files and all
other chunk statistics; see `vehicle-partial-rebuild-audit.json`.
These vehicles still need further visual refinement. Later runtime timings are recorded below.
Fresh isolated engine views and native QA completed at 23:19 after the bow-lamp
correction; all twelve native routes and 22 stair directions passed at 23:20.
That vehicle revision's offline audit passed all 79 then-defined sample points. Initial attempts during
system commit exhaustion failed; the later pass follows both leaner allocations
and reduced external memory pressure. `vehicle-integration-audit.json` records
source/export hashes, test scope and remaining limitations. The editor startup
required Steam to be reopened; no active match was stopped for these checks.

Lighting now uses 23 downward spotlights (14 shadowed) and 13 point lights. Each
enclosed room has a warm ceiling fixture above its bed/worktop. Interior shadows
prevent wall leakage; exterior bulkhead lamps have lower intensity and range.
Cool daylight/sky intensity is reduced. These are source/engine-verified light
settings, not a measured FPS improvement. Ten darker asphalt repairs reuse the
existing scan, with fine sealant edges, short branching fractures and six flush
drain gratings. They add 5,092 triangles to the ground chunk and no colliders.
`ground_surfaces()` in the default material rebuild preserves those bindings.

The expanded room audit exposed shelves pinching all four barracks room routes.
Shelves now leave turning space behind their doors, and the beds/consoles fit
within the exterior walls. The roof landing uses a narrow approach and a broad
roof-facing mouth kept outside the stair approach radius. The old test accepted
partial navmesh paths, including a roof path ending on the upper floor. It now
uses `CalculatePath`, requires `Complete`, checks the endpoint's plan/height
error, and traverses the result with the character controller. All 24 targets,
including eight room targets and four roof-transition targets, now pass. The
pre-fix failures are retained in `rooms-before-nav.json`.

The waterfall uses six curved, double-sided streams with continuous normals,
downward animated filament masks, four impact plumes and four softly masked spray
fans. Its irregular plunge basin is recessed below the forest slab; nearby trees
are rooted on the rim. The entrance torrent has 28 descending sections, smooth
sloping banks with wet inner strips and ten sparse flowing foam overlays. Concrete
girders and four bed-rooted piers support the existing entrance bridge. These
background changes add no collision or accessible terrain. The vista chunk is
5,368 triangles, with no collision boxes or hulls.
`forestbase_water.py` regenerates only the water masks and material bindings; the
default `forestbase_materials.py` rebuild also invokes it. The three new shaders
are `forestbase_waterfall`, `forestbase_foam` and opaque `forestbase_river`. Existing
ground puddles retain their separate `forestbase_water` shader.

To rebuild downloaded CC0 scenery and surfaces, run the import scripts below.
They cache downloads under `Sources/ForestBase`, and the pine/cliff mesh exporters
use the configured Windows Blender 5.2 executable. Download and Blender processing
are substantially larger than an ordinary map rebuild.

```text
python Tools/forestbase_import_surfaces.py
python Tools/forestbase_import_pine.py
python Tools/forestbase_import_fir.py fir_tree_01 fir_sapling
python Tools/forestbase_import_cliff.py
python Tools/forestbase_import_cliff.py boulder_01
python Tools/forestbase_map.py --no-trees
```

## Verification

Build the editor project and run these editor console commands after assets finish
compiling. The commands create an isolated scene and write results and actual
engine renders under `output/forestbase`.

```text
dotnet build Editor/razedtest.editor.csproj --no-restore
hc1_forestbase_qa
hc1_forestbase_navqa
hc1_forestbase_treeqa
hc1_forestbase_firqa
```

For actual runtime views during a Forest Base match:

```text
hc1_forestbase_perfview 0
hc1_forestbase_viewport 1920 1080
hc1_forestbase_perfcapture
hc1_forestbase_perfcontext
dev_perf 600
hc1_forestbase_perfview 1
hc1_forestbase_perfview 2
hc1_forestbase_perfview 3
hc1_forestbase_perfview 4
hc1_forestbase_perfview -1
hc1_forestbase_viewport_close
```

Views 0/1/2 inspect the yard, command-roof overview and close forest respectively.
Views 3/4 inspect the waterfall from the accessible command roof and the torrent
from the sealed entrance bridge.
`perfcapture` renders that inspection camera without HUD into `live-perf-view.png`.
The inspection temporarily raises the runtime TDM early-win limit to avoid a map
change during measurement. View -1 restores the saved limits and camera flags.
It does not change the saved scene or game-mode prefab.
The optional fixed-size viewport uses the editor's public rendering/input APIs.
Focus the existing game view before opening it. Wait for window layout, then
confirm the actual resolution with `perfcontext` before sampling: immediately
after opening, the engine can still report the widget's initial 100×30 size.
Closing the test window restores the previous game widget; stopping play also
closes it automatically. `Tools/forestbase_gpu_sample.ps1` records overlapping
GPU engine counters without stopping other processes.

On 2026-10-09, the vehicle/room/roof/ground/lighting/bedding revision was measured
in the fixed viewport at a confirmed 1920×1080 resolution. The 600-frame local
TDM sample had 10–14 living bots and one living local player: average 28.36 ms
(about 35 FPS), p50 28.30, p95 35.83, p99 38.22 and maximum 49.78 ms.
The engine's last-200-frame render timing averaged 15.344 ms (maximum 24.253).
Model errors were zero, with one SSR volume. Dynamic model counts were 825 before
and 777 after the sample in an already-running match. The inspection camera had
priority 100. Overlapping telemetry shows S&box using 87–93% of one 3D engine;
other processes, including the desktop compositor, Discord and capture tools,
also used GPU engines. This is evidence that graphics cost still needs work,
not a verified 60 FPS result or an unloaded comparison. See
`bed-1080-performance-audit.json`, its exact log, before/after context, runtime
image and overlapping GPU samples. Earlier performance evidence is retained in
`performance-audit.json`. The preceding 300×1286 narrow-view sample averaged
20.02 ms with 13–14 bots and is kept separately; its resolution is unsuitable for
a normal-resolution performance claim. Test-window closure, camera restoration
and stopped runtime flags were verified afterward.

On 2026-10-08, the latest geometry passed:

- Editor build: zero errors, three existing project warnings. The obsolete
  navigation API warning was removed by using `CalculatePath`.
- All 32 team/FFA spawn floors and capsule clearances; six boundary traces.
- Twenty-four complete engine navmesh paths reach their requested targets and
  traverse with `Facepunch.CharacterController`.
- All eleven staircases traversed in both directions: 22 controller checks.
- Offline radius-16, height-72, step-18 collision connectivity audit after the
  room/roof corrections: 122,541 reachable cells, all 91 check points pass.
- All four wheel/underbody-gap collision regression traces passed.
- Standing sightline samples from five command-roof positions and two bridges
  to all 16 team spawns: no exposed spawn in the 112 tested rays. This is a finite
  regression sample, not an exhaustive proof of multiplayer balance.
- Actual TDM gameplay with bots; complete local Bomb Defusal rounds at A and B.
  Held Attack1 plants after the production four-second timer; early release
  cancels without spawning a bomb. Held Use starts defusing, early release
  cancels, and a second uninterrupted hold completes the prefab's 7.5-second
  timer and awards the round to CounterTerrorist. Measured completion times
  were 7.504 / 7.517 seconds of game time. Remote multiplayer remains unverified.

Repeat the controlled bomb integration check in a fresh local Defusal match,
after the round has assigned C4 to a living local player (about eight seconds
after `dev_defuse forestbase` on this editor):

```text
dev_defuse forestbase
python Tools/forestbase_bomb_test.py --site 0
dev_defuse forestbase
python Tools/forestbase_bomb_test.py --site 1
```

The Editor-only helper preserves active bot participation, clamps their movement
and sight, protects the actor and bots from damage, teleports the actor into the
site, then changes that same actor to the defender role. It disables the
no-attacker instant-defuse shortcut so the full timer is exercised. It injects
normal actions at scene update boundaries and never calls `FinishPlant` or
`FinishDefusing`. The script restores its temporary controls on success or
failure. `bomb-site-A-passed.json` / `bomb-site-B-passed.json` record both
cancellations, bomb-zone indices, timed completion and round winner. These are
controlled single-host checks, not evidence of remote replication or 10–15
human-client load. Initial manual attempts and incomplete reports are not used
as passing evidence.

Inspect `engine-qa.json`, `engine-nav.json`, `route-audit.json`, `layout.json` and
the eighteen PNG views (including cargo, roof detail, waterfall foot, the gorge,
APC detail, vehicle front, upper barracks and drain detail)
for detailed evidence. The QA aerial render also refreshes the
map selection thumbnail. Performance captures should be taken after compilation
and gameplay warmup; minimized editor frame limits affect observed FPS.
After the open-rail, facade, geometric-pine and rain-reflection changes, the
17:46 roof-overview sample used 600 frames with 7–9 living bots: average 20.04 ms,
p95 20.37 ms, p99 28.03 ms, maximum 43.91 ms; render time averaged 7.87 ms over
the last 200 frames. The 17:47 close-forest sample had a 1060.28 ms outlier
(average 21.78 ms, p95 20.27 ms, p99 25.77 ms); steady render time averaged
6.53 ms over the last 200 frames. Its cause is unresolved. These measurements
precede the closed-rock-ridge revision. The minimized editor ran near a 50 FPS
frame limit; this is not a general 60 FPS guarantee or a remote-client load test.
Two warm repeats after the closed ridge and twig-mask update, at 18:02 and 18:03,
used 600 frames each with 7–9 living bots and one player. Average frame times
were 20.04/20.05 ms, p95 20.43/20.40 ms and maxima 45.41/33.94 ms. Render time
averaged 7.48/7.15 ms over the respective last 200 frames. The earlier one-second
outlier did not recur in these finite samples; its cause is still unresolved.
The 18:30 roof sample, after cargo hardware, muddy lanes and the forest-floor
update, used 600 frames with 7–9 living bots and one player in a match launched
via `dev_mode`: average 20.16 ms, p95 20.36 ms, p99 26.19 ms, maximum 64.88 ms;
render time averaged 7.85 ms over the last 200 frames. The inspection logged one
SSR volume. The earlier 18:24 sample without that volume is not used for comparison.
After facade and roof detail, the 19:34 sample (600 frames, 7–9 living bots,
one living player at completion) averaged 89.21 ms, p95 128.42 ms, maximum
281.65 ms; render time averaged 55.54 ms over the last 200 frames. A 19:41
repeat (300 frames, 7–9 living bots, zero living players at the final instant
before respawn) averaged 50.56 ms, p95 85.36 ms, maximum 157.80 ms; render time
averaged 18.68 ms. These poor results are retained in `performance-audit.json`.
During the second sample, Windows GPU counters recorded another `cod` process
using 55–66% of the same 3D engine, while S&box used 11–16%. The runtime context
recorded a 1156×462 game view, one SSR volume and zero model errors. This concurrent
workload makes comparison with earlier samples and attribution to map changes
unresolved. An unloaded baseline for the new detail is still needed. The helper
`perfcontext` saves resolution, camera priorities, mode and model/SSR counts.
One F5 bootstrap interval also lasted approximately 126 seconds between the
game-mode log and first player spawn, with a stall and 52 cloud-reference logs.
Its cause is unresolved; warm launcher reload was substantially faster.
The first runtime performance attempt after fir integration did not produce a
sample: the editor hung during Play/initialization and exited around 20:17.
Windows recorded an `AppHangB1` event for `sbox-dev.exe`; the exact cause is
unresolved. The pre-recovery log and event are retained in
`fir-before-editor-recovery.log` and `fir-editor-hang.json`. The editor was
reopened using the project's recorded `-project hc1.sbproj` launch arguments.
After reopening, each of the six fir/sapling variants rendered in its own fresh
inspection scene at 20:25, with no model errors. A sequential match retry then
completed a 600-frame sample at 20:29: 6–9 living bots, zero living players at the
final instant before respawn, average 20.83 ms, p95 25.03 ms, p99 35.17 ms and
maximum 107.32 ms. Render time averaged 10.209 ms over the last 200 frames.
The runtime recorded one SSR volume and zero model errors. Its editor game view
was 316×1302, unlike the previous 1156×462 context. Concurrent GPU counters on
the shared 3D engine ranged 0–33% for `cod` and 17–28% for S&box; some samples
fall just outside the frame-sampling interval. This timing is retained with the
full context in `performance-audit.json`, `fir-performance-log.txt` and
`fir-runtime-gpu.json`. It does not establish normal-resolution performance or
comparability with prior revisions. An unloaded comparison is still required.

The first waterfall/basin runtime sample completed at 21:07:48: 600 frames with
8–9 living bots and one living player, average 12.82 ms, p95 22.21 ms, p99 29.94 ms
and maximum 46.99 ms. Render time averaged 0.579 ms over the last 200 frames.
Context recorded 1140×446, 616 model renderers, zero model errors and one SSR
volume. No overlapping GPU telemetry was collected. The different viewport and
unknown concurrent load prevent attribution to the map revision. This sample
precedes the subsequent bank/foam refinement and is not a full-resolution or
remote-client performance result. The exact log/context are retained in
`waterfall-performance-log.txt`, `waterfall-runtime-context.json` and
`performance-audit.json`.
After the bank/foam refinement and fir UV repair, the 21:24:49 sample used 600
frames, 7–9 living bots and one living player: average 46.01 ms, p95 63.12 ms,
p99 74.82 ms and maximum 103.36 ms. Render time averaged 32.649 ms over the last
200 frames. Context recorded 1140×446, 475 model renderers, zero model errors
and one SSR volume. GPU telemetry overlaps 21:24:24–21:24:49 and records `cod`
using 50–67% of the shared 3D engine while S&box counters range 0–26%. These poor
timings are retained in `waterfall-uv-performance-log.txt`,
`waterfall-uv-runtime-context.json`, `waterfall-uv-runtime-gpu.json` and
`performance-audit.json`. The map's contribution remains unresolved without an
unloaded comparison; the earlier faster sample does not resolve this.
The subsequent vehicle, room/roof, ground-dressing and spotlight revisions are
not covered by this timing.
At that stage performance was unmeasured; later local runtime samples are recorded below.
Two historical runtime captures from the same command-roof camera demonstrate
animated waterfall pixels in `waterfall-uv-motion-audit.json` (29,825 changed ROI
pixels); this verifies visual movement, not physical fluid simulation or
replication. `waterfall-motion-audit.json` retains the earlier water revision.

## Historical cascade revision, 9 October 2026

Four proportion-preserving Mountainside photogrammetry instances form the cliff
face. Its separate native LODs contain 24k/10k/3k triangles. An orthographic depth
raster of the highest-detail export fits the narrower flowing water geometry to
the actual placed rock surface. Four streams expose rock ribs; impact foam and
mist cover the plunge zone. The vista has 17,394 triangles and no collision.
All nine authored chunk collision definitions match the pre-cascade snapshot.

Native diagnostics isolated the obvious triangular water artifacts to shadows
cast by the scanned rock. Diffuse emission on the aerated water and mist avoids
those hard shadow silhouettes while retaining engine fog and tonemapping. This
is a visual approximation, not simulated volumetric multiple scattering. Filament opacity now breaks up the sheets; the lower fade occurs above the
opaque pool intersection using world height, and downward flow is also driven
by world height independently of OBJ UV conventions. Every foam phase fades
at the footprint boundary.
The waterfall still needs further natural breakup and impact-zone refinement.

The built-in image_gen tool generated `waterfall_froth_v2.png`, now a project
asset consumed by the actual waterfall shader and plunge foam. Its full prompt
and original path are saved in `waterfall_froth_v2.provenance.txt`. It is a
texture input, not evidence of the final map appearance. Engine images remain
the visual evidence. The original procedural texture is retained.

Rain-film roughness reaches .025 in puddles, with 99% leveling of the asphalt
normal at full wetness. Dry patches retain the scanned aggregate.

Cases have three coating variants and separate beveled hardware. A dedicated
shader sets metalness explicitly on paint, equipment and the satellite dish.
All six coating materials were explicitly compiled after shader creation; the
intermediate red-checker images are not the final material state.

The scene's global postprocessing now serializes `SceneVolume.Type=Infinite`.
The former read-only `IsInfinite` field was ignored by the engine; earlier SSR
component counts did not prove that the volume applied globally. Fresh native
QA confirms the effective infinite volume, AgX tonemapping and the authored
exposure settings. Lamp glass uses explicit warm emission. The sky is less blue,
and the mountain fog extends above the distant shoulders.

A preliminary two-visible-view 1080p diagnostic averaged 52.44 ms. It is not the
final benchmark. Hiding the original editor viewport produced 30.38 ms over
300 frames before final shader/texture changes. Neither sample substitutes for
a fresh 600-frame test of the final graphics revision. `cascade-verified/` and
`cascade-integration-audit.json` preserve source hashes and the latest native
visual/collision evidence.

Historical cascade graphics sample, 9 October at 10:52:03: 600 frames, 10–14 living
bots and one living local player at confirmed 1920×1080, with the original
editor viewport hidden. Average 28.30 ms (about 35 FPS),
p95 32.19, p99 39.63, maximum 48.97. Last-200-frame render average
16.590 ms. Native context contains zero model errors and one
SSR volume. Raw context, viewport visibility, overlapping GPU counters and log
are preserved in `cascade-1080-performance-audit.json` and `cascade-verified/`.
This is one fixed yard view in an aged editor match, not an unloaded multi-view
benchmark or a remote multiplayer test. The 35 FPS result is below 60 FPS.
The prior 29.52 ms sample is retained as `cascade-before-breakup-*`.

Two final command-roof runtime images five seconds apart changed 44,429
pixels in the waterfall ROI. `cascade-motion-audit.json` preserves that check;
it proves animated appearance, not a physical fluid simulation. Play was
stopped and the original editor viewport restored after the capture.

## Facade and forest revision, 9 October 2026

The facade scan now uses a dedicated neutral mineral shader: desaturated albedo,
explicit zero metalness and roughness clamped to .58–.96. Panel joints and anchor
plates dress all exterior walls; joints clip around every door and window. Folded
window sills and frames use satin equipment paint. Barracks/command/workshop chunks
contain 52,638/28,098/39,820 triangles. Their collision counts and all nine authored
physics arrays are identical to `facade-before/`.

Fir/sapling bark, needles and impostors explicitly bind `TextureMetalness` to zero.
Concrete, wood, roofing and forest-floor scans also have explicit dielectric inputs
where the source supplies no metal map. The fir importer's old scalar metalness
setting did not supply that texture channel.

The added second forest layer uses real branch geometry. Its background models
contain 20,443/21,347/9,900 triangles for variants a/b/c, retain authored needle
geometry and UVs, and simplify opaque wood and dead branches. Native elevated-view
inspection rejected full-crown crossed cards here, and uniform decimation removed
too much needle geometry. These heavier dimensional models are limited to 79 middle
and 96 distant placements. `distant-fir-geometry.json` records counts, UVs and bounds.
Regenerate them with Blender in background mode using
`Tools/forestbase_distant_fir_blender.py`, then run the fir importer with `--finalize`.
The normal fir import runs that reduction automatically.

Fresh native QA at 11:20:54 reported zero model errors, 32 clear/floored spawns,
six blocked boundary samples, four passing vehicle collisions and 112 blocked
roof/bridge-to-spawn rays. Earlier 24-path and 22-stair-direction native navigation
checks remain applicable to the identical collision arrays. This is not an
exhaustive escape test or a remote-client multiplayer test.

The 11:23:03 runtime sample measured 600 frames with 12–14 living bots and one
local player in one visible 1920×1080 game viewport: average 27.08 ms (36.93 FPS),
p95 29.97, p99 31.95 and maximum 56.39 ms. Last-200-frame render average was
18.572 ms. The runtime context contained zero model errors and one SSR volume.
`facade-1080-performance-audit.json` preserves overlapping GPU counters, before/after
context, viewport visibility and hashes including the tree assets. This is a fixed
yard view in the editor; it does not establish a general performance improvement
over older match states, stable 60 FPS or remote-client load performance.

`facade-integration-audit.json` and `facade-verified/` preserve this revision's
native images, checks, sources and performance evidence. Run
`python Tools/forestbase_facade_audit.py` to refresh the snapshot after successful
native QA; it rejects stale performance evidence. Play was stopped and the original
viewport restored after measurement. Reference fidelity, waterfall naturalism,
prop finish and overall AAA quality remain unfinished.

## Falling-water revision, 9 October 2026

The current four jets use a monotonic outward envelope of the scanned cliff.
Water can pass a ledge and continue vertically; the old path repeatedly returned
toward the rock and looked like curved fabric. Each exported jet has 73 falling
rows, never climbs, and extends to -345 below the pool surface at -255. Its
width contracts initially and spreads toward the foot. Four materials supply
their individual source height and phase; the world-height flow remains independent
of the model compiler's vertical UV convention. The generated density texture is
stretched more vertically, with softer irregular edges and a faded entry lip.

Impact spray occupies smaller ellipses. The basin center moved from north 3500
to 3370, and its inner bank follows it. Shader masks constrain low spray and foam
to the basin interior rather than letting them end as bright planes on dry ground.
All four exported impact centers lie well inside the water footprint. The wet-rock
shader uses lighter mineral albedo and roughness .42–.80 instead of the former
.24–.61, retaining the original scan detail. The vista has 17,390 triangles and
zero collision; all nine authored collision arrays still match the earlier layout.
The close-up now exposes a simple basin bank, which still needs natural shore detail.

Native scene QA at 11:44:30 reported zero model errors, 32 clear/floored spawns,
six blocked boundary samples, four passing vehicle collisions and 112 blocked
roof/bridge-to-spawn rays. The prior complete 24-path/22-stair-direction navigation
results apply to the unchanged authored physics. `forestbase_flow_audit.py` checks
actual exported OBJ rows and impact locations, and preserves the native evidence
in `flow-integration-audit.json` and `flow-verified/`.

`hc1_forestbase_flowcapture` records three unedited runtime images from the fixed
command-roof camera. The actual capture intervals were .585/.649 seconds, including
render and file-write time. Three unobstructed jet regions changed 9,568 and 9,958
pixels by more than eight RGB levels across the successive pairs. The motion audit
proves animated appearance; it does not independently measure flow direction or
prove physical fluid simulation. Editor compilation passed with zero errors and
the three existing unrelated warnings.

The fresh 11:50:36 single-view 1920×1080 sample measured 600 frames with 12–14
living bots and one local player: average 28.45 ms (35.15 FPS), p95 30.50, p99
32.85 and maximum 46.45 ms. Last-200-frame render average was 18.692 ms. Both
native contexts had zero model errors and one SSR volume. The original editor
viewport was hidden; overlapping GPU processes are recorded. These results are
one fixed editor yard view, not a standalone multi-view benchmark or a remote
multiplayer test. They do not establish stable 60 FPS. Evidence and revision hashes
are in `flow-1080-performance-audit.json`; earlier samples retain their own files.
Play was stopped and the original viewport restored after capture. Reference fidelity,
shore detail, props, lighting finish and AAA quality remain incomplete.

## Shoreline revision, 9 October

The waterfall basin now has six scanned boulders, 34 smaller stones merged into
the vista and 24 sparse grass clumps. The bank uses 96 circumferential segments
and eight radial bands with smooth normals and irregular interior relief. The
separate shore shader applies darker, less rough surfaces near the waterline;
rock and soil remain dielectric. The grass model/material copies reuse existing
project geometry and wind shading, without changing the shared grass originals.
The vista contains 52,538 triangles and no collision. All nine authored physics
arrays remain exactly identical. All shore instances contain only model renderers.

To rebuild this dressing, run `python Tools/forestbase_shore.py`, then
`python Tools/forestbase_map.py --no-trees --chunks vista`. Collision-only and
other partial builds also collect the shore instances into the regenerated scene.

Native QA at 12:05:06 reported zero model errors, 32 clear/floored spawns, six
blocked boundary samples, four passing vehicle samples and 112 blocked sampled
roof/bridge-to-spawn rays. Previous 24-path/22-stair navigation applies to the
unchanged authored collision. Current images and revision evidence are preserved
by `python Tools/forestbase_flow_audit.py --prefix shore` in `shore-verified/`.
Earlier runtime motion captures only establish animation of the unchanged water
shader; they are not captures of this new shore dressing.

The 12:13:26 single-view 1920×1080 diagnostic measured 600 frames with 11–14
living bots and one player: average 157.78 ms (6.34 FPS), p95 395.53 ms and maximum
1129.03 ms. It includes GPU fence/present-event waits and one native bitmap capture
during sampling. GPU telemetry overlaps only part of the sample and records the
concurrent `cod` process, along with other applications. This is an actual poor
runtime result, not a clean comparison with the preceding 35 FPS water sample;
the evidence does not isolate the cause or prove a shore-related regression.
Both contexts have zero model errors and one SSR volume; the original editor view
was hidden. Details are in `shore-1080-performance-audit.json`. Play was stopped
and the original view restored. An uncontended measurement remains outstanding.

The new stones break up the uniform bank outline. The basin surface still looks
flat, the spray remains too even, and the wider scene still lacks reference fidelity.
This revision does not achieve the requested AAA finish.

## Integrated plunge-water revision, 9 October

The four falling streams now have broader unequal channels, irregular width
changes and lateral drift. Coarse density and UV warping break up the former
uniform fine threads. Geometry still follows a monotonic outward cliff envelope
and continues below the pool. The old paired foam/plunge quads at each impact
were removed. Compact impact plumes and two overlapping low mist bands replace
the previous stack of rounded spray footprints; the mist shader adds moving wisps.

`forestbase_basin.shader` shades the opaque basin itself with damped expanding
impact ripples, small surface waves, drifting broken froth and foam-dependent
roughness. The generator writes the four actual jet impact positions into
`plunge_basin.vmat`. This is an animated shading approximation, not fluid simulation.
The foreground gorge retains its separate river material. The vista now has
52,506 triangles and no collision; all nine collision arrays remain identical.
`turbulence-source-check.json` checks actual exported rows and collision parity.

Editor code compilation passed with zero errors and the three existing warnings.
The new shader compiled in the native engine. The first view exposed hard repeated
foam flecks; preserving soft texture density and narrowing the aerated-water
envelope corrected that in the final close-up. Native QA at 12:44:06 reported
zero model errors, 32 clear/floored spawns, six blocked boundary samples, four
passing vehicle samples and 112 blocked sampled roof/bridge-to-spawn rays.
Previous navigation results apply to the identical authored collision.

Three unedited command-roof runtime captures at 12:42:22–26 have identical camera
positions. Their actual intervals are 2.432 and 1.973 seconds, including native
render/write time. The three unobstructed jet regions change 10,758 and 10,912
pixels by more than eight RGB levels across successive pairs. This establishes
animated appearance, not physical fluid simulation or independently verified
flow direction. The new `--prefix turbulence` capture/audit options retain earlier
water evidence. Current source hashes, native checks and images are preserved in
`turbulence-integration-audit.json` and `turbulence-verified/`.

The editor recovered after the long project load and Play was stopped after the
runtime captures. GPU fence/present waits remain in the engine log. No new
uncontended performance sample is claimed. Earlier `shore-verified/` images and
its poor, contended runtime diagnostic remain historical evidence; neither verifies
this new water revision. The reference's broad terraced cascade, lighting depth,
forest silhouette and detailed military props remain incompletely matched.
The complete visual target and current uncontended performance remain unproven.

## Lighting, shelter and cliff infill revision, 9 October

The eleven exterior floodlight groups now have three pitched lamp heads and
visible supports. Downward spots align with the housings; warm lighting, cool
daylight and two bounded fog volumes were adjusted together. The native QA at
13:03 preceded the shelter, container and cliff changes below. The later fog
diagnostic showed little image difference between tested strengths, so it does
not establish the reference's atmospheric depth.

The logistics shelter now uses a curved, perforated cloth roof, edge valances
and supporting ribs instead of a flat opaque sheet. Its six existing collision
posts remain. Three desaturated olive, grey and khaki container materials use
the existing scan; shader defaults preserve other coated equipment. These
assets were inspected in independent Blender previews and compiled in S&box.

The cliff undercuts are closed by a separate scan-fitted background mass.
Rock Face 03 supplies 2K albedo, normal, roughness and AO at approximately
2.7-metre tiling, replacing the fine grey terrain texture. Inclined ledges add
relief to exposed infill; smoothly shaded faces avoid a rectangular facet grid.
The vista contains 82,494 triangles and no collision. The four falling streams
retain their exported geometry. Native images and QA at 23:52:25 cover the final
revision: zero model errors, 32 clear/floored spawns, six blocked boundary samples,
four passing vehicle samples and 112 blocked sampled spawn rays. The close view
has a continuous rock backdrop; the aerial view still exposes an unnatural
striped vertical surface at the distant cliff. Tapering the infill ends did not
remove it, so it remains an explicit visual defect requiring investigation.
The independent cliff preview uses approximate lighting and does not reproduce
the engine's wet-rock shader. The waterfall remains too narrow and regular.

The preceding all-nine-chunk collision parity report remains available in
`output/forestbase/atmosphere-collision-parity.json`; this infill adds no physics.
No new performance or remote-client result is claimed for these visual changes.

## Broader crown channels and projected cliff infill, 10 October

The four crown channels now span approximately 31 metres instead of 14.5 metres.
Their widths and start heights follow the placed scan, then converge over the
upper slope toward the existing lower jets and compact plunge basin. The small
rectangular inlet cards were removed after native views exposed bright straight
edges above the fall. Stream meshes still have 73 descending rows each; exported
checks establish downward height, an outward-only envelope and impacts within
the basin. Gameplay collision remains unchanged across all nine chunks.

The near background fill recesses nearest-filled scan gaps into wider transitions
and smooths its crown independently of the water. The distant ridge instead uses
a continuous sloping backing behind three overlapping, uniformly scaled scans;
the third scan covers the exposed central gap. A separate
`forestbase_cliff_infill.shader` projects albedo, normal, roughness and AO on three
world planes using actual triangle derivatives. Original scanned cliffs retain
their authored UVs in `forestbase_cascade_rock.shader`; wetness modulates their
scanned roughness. Both shaders compiled in the native engine. The vista contains
82,486 triangles and no collision. Native review at 00:28:38 shows the formerly
exposed flat wall covered by scanned rock in the aerial view. Full native QA
reports zero model errors, 32 clear/floored spawns, six blocked boundary samples,
four passing vehicle samples and 112 blocked sampled spawn rays. Images and
revision evidence are preserved in `output/forestbase/crown-verified/` and
`crown-revision.json`. Other viewpoints still require visual scrutiny.

`hc1_forestbase_materials` records the actual loaded vista material shaders.
`hc1_forestbase_qa` still captures all views by default; a comma-separated view
filter, such as `hc1_forestbase_qa aerial,waterfall`, avoids unrelated captures
during visual iteration. Its report lists `capturedViews`; collision and spawn
checks remain complete even when the captured-image set is limited. Only a run
that includes `aerial` rewrites the map thumbnail.

The reference's continuous terraced fall, forest atmosphere, detailed compound
and stable multiplayer performance remain unfinished. Broader upper channels
alone do not establish the complete visual target.

## Structural frames and bridge junctions, 19 October, offline

`forestbase_structures.py` adds chamfered rolled sections, balcony knee braces,
column bases, bolted gussets and braced bridge sides. Front-frame strips now stop
at door and window apertures. The current links model has 23,146 triangles and
148 collision boxes. The latest side-bracing pass adds 5,800 triangles without
changing those boxes or any of the other eight ModelDoc sources. Its preceding
model/source snapshot is in `output/forestbase/rail-truss-before/`.

The earlier structural revision also fixed a gameplay defect: both bridge rails
had been placed on the same side. Mirroring the second rail required clipping
the guards at the east elbow and landing, and filling the missing outer deck
quarter. That repair changed links from 141 to 148 boxes. Consequently the
historical all-nine collision-parity and native navigation/spawn results above
do **not** verify the current bridge revision.

`forestbase_structure_audit.py` checks the serialized boxes independently of the
map generator, using a 24-inch-radius, 72-inch-tall capsule at 342 samples along
five elevated route segments. Current samples have no capsule overlaps and no
unsupported centers. The old junction has 26 blocked samples across two segments.
Four circular perimeter samples near the diagonal west-bridge abutments fall
outside the deck union; center support remains present. These are explicitly
retained for follow-up rather than treated as complete footprint coverage.
The audit also checks finite exported vertices, normalized normals, face indices,
unchanged latest-pass physics and hashes of the other eight ModelDoc files.
Evidence is in `output/forestbase/structural-route-audit.json`.

`forestbase_structure_preview.py --state rail-before|after --view bridge-junction`
renders the saved and current meshes in separate Blender CPU processes, with
matched 1024x682 views and 48 samples. These use independent approximate lighting
and surface shaders. They inspect geometry; they do not establish S&box appearance,
collision compilation, native player movement, navmesh connectivity or performance.
The user has reserved the editor for another project, so no editor was accessed
for these changes. Native checks remain pending. The broad terraced waterfall,
dense reference forest and the full requested visual finish remain incomplete.

## Connected terraced cascade, offline revision

The four thin, independent jets are replaced by one connected surface spanning
approximately 33.4 metres at the crown and 16.3 metres at its foot. Four adjacent
OBJ material bands share their complete edge vertices, global UVs and the single
`waterfall_0.vmat` binding. Flow retains texture density through `FlowTiling`.
Two irregular rock shelves follow the water profile at approximately z650 and
z230; their ends retreat into the scanned escarpment. Each water column follows
the actual rock envelope without returning into it. Available basin clearance
limits its outward ledge advance. The basin outline and water level are unchanged;
impact and spray positions are derived from the new surface.

A fifth uniformly scaled Mountainside instance fills the formerly deep crown
notch. It reuses the existing mesh, textures and three LOD groups. The generator
appends this instance after existing scenery, preserving the index-based IDs of
the previous forest objects. The vista mesh now has 99,682 triangles and no
collision, compared with 82,486 triangles before this revision. This pass adds
no bitmap texture assets. The new water shader retains three flow-texture reads,
preserves the real surface normal at ledges and keeps a translucent water body
between foam filaments. UV orientation is derived from the triangle's height
gradient so a V-axis flip cannot reverse the intended progress direction.
Shader compilation and actual animated direction remain unverified in-engine.

`forestbase_cascade_audit.py` checks the exported OBJ independently: finite
vertices/normals, normalized normals, nonzero triangle areas, descending columns,
outward-only column profiles and all three shared material seams. Its 660 sampled
principal-view rays are not occluded by added/refitted rock. All 100 basin-entry
checks, including the duplicate seam columns, are inside the existing basin;
maximum normalized radius squared is approximately 0.9263. These tests do not
establish every view, realistic fluid behaviour or native rendering quality.

Installed hashes and preservation checks are recorded in
`output/forestbase/terrace-integration.json`. The eight other ModelDoc files and
all 655 previous scene objects/components remain unchanged; the scene gains only
one renderer-only rock object. The previous scene, materials, shader and vista
are retained in `output/forestbase/terrace-before/`. Staged files, geometry audit
and scene comparison are in `terrace-stage/`.

`forestbase_cascade_preview.py` renders the actual exported geometry and scan
placements in Blender CPU front/side views. Its static water, lighting and rock
shaders are approximations; spray and foliage are omitted. These images are
geometry evidence, not S&box captures or native shader/atmosphere acceptance.
No editor was opened or controlled. Fresh shader/model compilation, water motion,
shore blending, multi-view appearance and uncontended GPU timings remain pending.
The larger water area may change fill cost; no stable frame-rate claim is made.
The preceding crown/native audit files describe their historical revisions and
must not be used as proof of this new cascade or the earlier bridge repair.

## Forest proportions, understory and dimensional distance meshes, offline

`forestbase_forest.py` adjusts the generated forest once, after the existing
instance list is complete. Mature firs are narrower and taller, middle trees
change more subtly, and saplings retain their original proportions. Existing
roots, rotations, parentage and index-based scene identities remain unchanged.
The forest now contains 525 trees instead of 437: 64 additional outer trees and
24 smaller dimensional firs form an intermediate canopy above the saplings.
All new horizontal tree bounds stay outside the complete playable AO. South
understory roots are farther back to remain outside the entrance's longer bounds.

The outer distance models use real reduced branch geometry. A trial using
whole-crown cross cards was rejected after the elevated preview exposed flat
silhouettes; it was not installed. `forestbase_horizon_fir_blender.py` reduces
connected branch islands, protects outer groups in height/azimuth cells and keeps
the trunk. Interior needle fans can expand by up to 1.35 within the original used
bounds to retain coverage. Existing source UVs and PBR atlases are reused, with
no new bitmap textures. Variants A/B/C contain 4,998 / 5,000 / 5,000 triangles.
The 139 explicit horizon trees have roots at least 92.46 metres from the playable
rectangle; closer outer trees retain the earlier dimensional meshes.

Normal fir ModelDocs retain LOD0/LOD1 and their existing switch thresholds.
Their LOD2 now also uses the reduced dimensional mesh, replacing large whole-crown
cards. Native transition distances and visual acceptance have not been measured.
The importer regenerates these meshes after the source fir export; the map writer
preserves the ModelDocs idempotently. Existing sapling LODs remain unchanged.

`forestbase_forest_audit.py` checks object identity/order, allowed tree-only field
changes, source bounds, root placement, mesh references, UV indices, finite/unit
normals and nondegenerate reduced triangles. All 656 prior objects remain; only
356 tree scales/model references change, and 88 renderer-only objects are added.
All non-forest objects and all nine main map ModelDoc sources remain unchanged.
The sum of maximum declared LOD triangle counts changes from 12,346,229 to
12,185,295 despite the extra trees. This conservative sum is **not** active GPU
geometry, measured culling, shadow/alpha cost or a frame-rate result. More objects
and alpha surfaces can add other costs; current native performance remains open.

Evidence and installed hashes are in `output/forestbase/forest-integration.json`,
with the previous scene/regular fir ModelDocs in `forest-before/` and staged
assets/audit in `forest-stage/`. Layout metadata now separates actual `trees`
from `sceneryInstances`; the earlier `trees` value counted all backdrop instances.
`forestbase_forest_preview.py` provides matched ground views, an elevated view
and an explicit LOD2 inspection using real assets. Its lighting/materials and
LOD selection are independent approximations; it does not establish native
appearance, alpha stability, LOD transitions or performance. Native acceptance
should include ModelDoc's AutoLOD and Rendering Info views, as described in
[Facepunch's ModelDoc guide](https://sbox.game/learn/facepunch/modeldoc-basics).
The editor was neither opened nor controlled. Forest-ground integration, wider
view coverage and the full reference finish remain incomplete.

## Hall roofs and steel framing — offline revision

`forestbase_sheds.py` replaces the thin roof planes and protruding rafters of
the vehicle canopy and workshop. Both retain their positions, footprint and five
frame bays. The roofs now meet the existing 180-inch wall tops, with folded ridge
and edge flashings, raised sheet laps, gutters, rear downpipes, smaller purlins,
I-section posts/rafters, truss webs, gussets and bolts. Existing PBR maps and
coated-steel materials are reused. The motor canopy's former visual-only side
panels are removed, leaving the open-sided parking structure in the reference.
The workshop has closed triangular gables, and facade strips no longer run
across the open garage doorway. Hall signs sit ahead of the gutters on short
brackets so the roof edge does not hide their lettering. Vehicles, tools, lights and scene
objects are unchanged in this pass.

The old ModelDocs had no explicit sloped roof boxes. Two correctly oriented
metal boxes per hall now follow the roof skin; the workshop also gains two gable
hulls. This **changes physics**. The workshop center post is removed from the
garage opening and replaced by a spanning lintel above it. All remaining boxes
and convex hull elements retain their geometry and order; hull elements are
compared by geometry rather than global shape index. Motor boxes change 17→19,
with 16 hulls retained. Workshop boxes change 45→47 (one post removed, a lintel
and two roof slabs added) and hulls 9→11. Roof skins, hardware and
drainage are otherwise visual geometry. Final motor/workshop meshes contain
55,282 / 48,958 triangles, up from 45,230 / 39,820; no native performance result
is available for this added geometry.

`forestbase_sheds_audit.py` independently parses the serialized boxes and
disconnected OBJ hull elements. It checks preservation of retained physical geometry,
126 vertical roof samples against the analytic surface (maximum error under
0.00014 inch), standing-capsule clearance from the new roof slabs, 33 capsule samples crossing
the workshop entrance (previous center obstruction removed), finite/unit
normals, valid UV/normal indices and nonzero triangles. The scene and seven
unrelated main ModelDocs remain unchanged. These sampled checks do not establish
native import, roof access, controller behavior, bullets, navigation or spawn
fairness. Those need new engine checks, including possible new roof perches;
earlier movement and visibility results do not cover this revision.

Evidence and file hashes are recorded in `output/forestbase/sheds-integration.json`.
The original assets are preserved in `sheds-before/`; candidate exports and the
independent audit are in `sheds-stage/`. `forestbase_structure_preview.py` has
matched roof comparisons and interior inspection views using the real exported
assets with approximate Blender lighting/materials. These images do not prove
the final S&box appearance. No editor was opened or controlled.

## Forest floor and low vegetation — offline revision

`forestbase_floor.py` replaces the inaccessible flat forest slab tops and coarse
verge strips with a continuous height field. Relief is positive and limited to
12 inches; it tapers out at the playable edge, world limits, entrance gorge and
plunge-basin cutout. Existing soil texture scale and the recessed water areas are
retained. Existing trees keep their complete transforms; soil at the 525 checked
roots rises by 0.15–10.42 inches, burying their bases rather than lifting them.
The backdrop mesh changes from 99,682 to 111,714 triangles and still has no
physical boxes or hulls.

Eight renderer-only groups add 1,024 small grass tufts in irregular clusters
outside the conservative full AO bounds. They reuse HC1's existing short-grass
geometry, UVs and colour map, with three geometry LODs. Local slope shear keeps
the bases close to the actual triangulated terrain; normals use the inverse
transpose of that deformation. Aggregate grass triangle counts are 61,440 /
10,240 / 7,168. These are declared mesh counts, not measured active geometry or
GPU cost. The existing short-grass switch thresholds 110/170 are retained;
native switching distances and quality remain unverified.

The new Forest Base material reuses `hc1grass.shader` without changing that
shared shader or other maps. Wind/gust and distance-rise are disabled for the
merged terrain-aligned groups. Distance collapse starts at 40,000 units, beyond
this map; blade normals blend upward and retain the existing foliage wrap and
backlight. Shadow casting remains disabled as in the source grass material.
No new image textures or HLSL shaders are introduced.

`forestbase_floor_audit.py` independently reads exported OBJ/ModelDoc files and
the staged scene. It verifies all 744 existing objects and scene properties,
eight new renderer-only objects, all vegetation vertices outside AO bounds,
valid mesh/UV/normal data, three decreasing LODs and unchanged eight other main
ModelDocs. Its 3,072 sampled grass roots are found in the exported meshes and
lie from 1.98 inches below to 0.59 inch above the exported soil. All nine main
map collision sources remain unchanged in this pass. Existing hall/bridge
physics changes from earlier revisions still require native acceptance.

Snapshots, export recipe, staged files and audit are under
`output/forestbase/floor-before/` and `floor-stage/`; installed hashes are in
`floor-integration.json`. `forestbase_forest_preview.py --revision floor` has
matched verge/raised views and a forced LOD0 close inspection. Actual source
meshes, material sources and scene hashes are recorded. Blender approximates
foliage lighting with thin diffuse/translucent leaves and disables grass shadow rays to follow the material's native
flag; it does not validate game appearance, wind, LOD transitions or performance.
Native multi-view and performance checks remain outstanding. The editor was
neither opened nor controlled. Broader ground coverage, mossy wet rock treatment
and full reference fidelity remain unfinished.

## Wet boulder surfaces and rim proportions — offline revision

`forestbase_rocks.py` gives the map's 49 boulder renderers a Forest Base wrapper
ModelDoc and a dedicated material. Original scanned OBJ/UV files, the source
ModelDoc/material, all three LODs and their thresholds remain unchanged. The
wrapper changes only the material reference; shore-boulder variants and other
maps' references to the original scan are unaffected.

Of the 32 surrounding ring boulders, 30 had excessive vertical scaling. Their
Z scale is capped at the geometric mean of the existing horizontal scales;
already flatter rocks stay unchanged. Positions, rotations and both horizontal
scales are preserved. The ring's maximum top above the compound's zero plane
changes from 13.66 to 5.41 metres, exposing more conifers behind the outcrops.
Rock 87, the existing central cover rock, keeps its entire transform. The 16
gorge rocks also keep their transforms. No objects or physical shapes are added.

`forestbase_rock.shader` retains the scan's colour, normal, roughness and AO maps.
It neutralizes most of the orange mineral cast, applies a restrained cool tint
and dampens/softens exposed stone. Two world-space polynomial noise fields form
large patches and vertical moisture streaks; an additional low-height wetness
band treats submerged gorge bases. Moss favours upward slopes and retains scan
variation; it has higher roughness than the wet mineral surface. Normal-film
blending is small, metalness stays zero and opacity stays one. No new bitmap
textures or mesh triangles are introduced, but the shader adds arithmetic cost;
current native performance is unmeasured, and active LOD/pixel cost can change
when silhouettes become lower.

`forestbase_rocks_audit.py` checks all 752 existing objects, permits only the 49
renderer model references and 30 vertical scales, and restores those fields to
prove all other scene content/properties identical. It checks all nine main
ModelDocs, the unchanged original scan ModelDoc/material, the wrapper's exact
material-only difference, absence of new physical shapes and numerical surface
bounds on 8,192 positions at four slopes. Numeric formula sampling is not a
native shader compilation or rendering test.

`forestbase_rock_preview.py` builds the corresponding world-coordinate Blender
nodes for matched ground, verge and elevated views. Texture sources, scene and
ModelDoc/mesh/material hashes are recorded. Noise precision, tangent normals,
lighting and shading can differ from native rendering; images do not establish
engine appearance, LOD transitions, shadow quality or performance.

The installed engine's `Material.CommonInputs.hlsl` and `material.hlsl` were read
to check actual material fields. Its separate `resourcecompiler.exe -help`
worked, but two isolated shader-build attempts failed in startup with missing
`assettypes.txt`/core fallback resources and exit `0xC0000005`. Supplying the found
asset-type configuration and a revised working directory did not initialize its
resource system. No `forestbase_rock.shader_c` was produced and the shader was
not compiled; this is a compiler-startup failure, not a shader error report. No
S&box editor was started, connected to or controlled. Diagnostics, staged assets,
export recipe and audit are in `output/forestbase/rocks-stage/`; snapshots are in
`rocks-before/`, and installed hashes/evidence are in `rocks-integration.json`.
Fresh native acceptance remains required, and the newly exposed farther forest
and ground still need denser coverage and complete reference composition work.

## Cascade crown width and whole-compound inspection — offline revision

The connected waterfall's upper crown now spans east 40–820 inches (19.81 m)
instead of -245–1070 (33.40 m). Its existing 110–750-inch foot (16.26 m), basin
outline and two terrace levels remain. Source heights, front envelope, shelves
and impact parameters are refitted from the actual cliff scans. All four paint
bands still share vertices/UV progress and bind the same waterfall material.
This reduces the earlier funnel-shaped silhouette without splitting the fall
into disconnected jets. The relative width is a reference-driven design choice,
not a dimensional measurement recoverable from the reference image.

`forestbase_cascade_audit.py` now accepts an explicit baseline. Against the
preceding installed mesh it finds 1,836 refitted shelf triangles; all 660 sampled
principal-view rays remain clear. All 100 band-column entry samples (97 unique
columns plus three shared seams) enter the existing basin; maximum normalized
radius squared is 0.7792. Shared edge errors remain below 0.002 inch, and exported
water heights/forward paths stay monotonic. `forestbase_cascade_width_audit.py`
also hashes reconstructed face positions, UVs and normals for every unrelated
material group. All thirteen unrelated groups are identical, all nine main
ModelDoc sources are identical, the scene/layout stay unchanged, and Vista still
contains 111,714 triangles with zero boxes/hulls. These are offline checks, not
fresh native playability, water rendering or performance results.

`forestbase_overview_preview.py` inspects all saved explicit model-renderer
nodes and practical-light placements together, with forced LOD1 and independent
Blender light energies. `forestbase_waterfall_preview.py` uses the saved native
water shader's t=0 sampling, density, foam, edge and opacity formulas instead of
the earlier plain bright-sheet approximation. Native importer-flip recovery,
animation, fog, exposure, shading and sampling precision remain unverified.
The Blender AgX inspection does not reproduce the shared gameplay camera's
accepted native ACES profile; neither that camera nor map lighting was changed.

The overall view still exposes incomplete reference fidelity: the wider forest
background is thin, the courtyard lacks the reference's cover/detail density,
and architecture/ground presentation needs further work. No AAA-quality claim
is supported. Snapshots and candidates are in `cascade-width-before/` and
`cascade-width-stage/`; installed hashes and matched overview evidence are in
`output/forestbase/cascade-width-integration.json`. The editor was not accessed.

## Loading islands and FFA clearance — offline revision

`forestbase_cargo.py` adds six deliberate cargo pockets in the motor and central/
eastern logistics courts. Thirty transport cases, six pallets, restraint bands,
labels and four small service cans reuse existing materials/textures. Their
placements break up previously uniform spaces while retaining the main lanes
and workshop garage bay. Low and two-tier loads vary the cover silhouette. All
geometry is merged into the existing yard/logistics chunks; no scene renderers,
buildings or bitmap textures are added.

This pass **changes gameplay collision**: 30 case boxes, six low pallet-deck
proxies and four can boxes are added after the old shapes. Yard boxes change
24→40 and logistics boxes 72→96; all old boxes and hull files remain intact.
Yard geometry changes 67,384→75,692 triangles and logistics 71,392→84,068, a total
increase of 20,984 declared triangles. This is not measured GPU cost or FPS.
Fresh native navigation, climbing/perch, sightline and multiplayer checks are
required; older native gameplay results do not cover these new pockets.

The pre-change source-grid audit with conservative radius 24 found two tight
FFA locations and two room probes near expanded furniture bounds. DM 5 moves
from plan (-1180,850,96) to (-1050,770,96); DM 12 moves (1400,410,0) to
(1310,350,0). Their object IDs/components remain, and the existing `spawn()`
routine supplies the same two-inch lift and regenerated inward facing. Team
spawns and objectives are unchanged. East barracks room probes now stand at
(-940,904) on each floor, inside the same rooms between the partition and
shelves, rather than near the conservative shelf footprint. Probe relocation
does not assert that the former points failed the live controller's clearance.

`forestbase_validate.audit(radius=24, output=...)` leaves its default radius 16
unchanged and provides reproducible before/after reports. The candidate reaches
all 91 sampled spawns, rooms, stairs, roof and objective locations in its
8-inch grid, with height 72 and step 18. Its conservative hull-AABB/box treatment
is not a native capsule or navmesh simulation. `forestbase_cargo_audit.py`
additionally confirms generated collision boxes and convex hull elements match
the actual serialized collision for all nine chunks, old yard/logistics shape
preservation, unchanged seven other ModelDocs, 752 retained scene objects and
only the two intended FFA pose edits. Scene/layout content outside these poses
and the two chunk statistics is preserved.

Matched whole-compound Blender inspections are saved as `cargo-before-compound`
and `cargo-after-compound`. The latter's exact scene input is archived as
`cargo-stage/render-input-before-spawn-pose.scene`; final spawn lift/facing were
corrected afterward using the existing routine. All model-renderer and light
nodes are identical between that image input and the final scene, so the visual
inspection remains applicable. No live characters/prefab expansion, native
rendering or frame-rate acceptance is implied. Snapshots, source-grid reports,
export recipe and audits are in `cargo-before/` and `cargo-stage/`; installed
hashes and limitations are in `output/forestbase/cargo-integration.json`. The
editor was not opened or controlled. Full reference fidelity remains incomplete.

## Existing-tree groves — offline revision

`forestbase_forest.regroup()` redistributes existing middle and outer-infill
trees once after the freshly generated instance list. West/east middle trees
form staggered mixed-variant groves, and southern middle trees keep the gorge
opening clear. West/east/south outer infill concentrates along the compound's
visible backdrop. The northern trees around the waterfall are excluded. Near
trees, saplings and intermediate understory keep their positions.

The saved scene changes 112 tree positions only. All 752 object identities,
parentage/order, root heights, rotations, scales, model references, components,
lighting, spawns and other content are preserved. Tree count remains 525, all
139 horizon trees remain at least 92.46 metres from the full AO rectangle, and
the nine main ModelDocs and layout metadata remain identical. No instances,
textures, shaders or declared mesh triangles are added. This does not imply
equal native cost: closer and overlapping crowns can increase alpha, shadow
and visible-pixel work, so performance and native LOD acceptance remain open.

`forestbase_groves_audit.py` verifies scene identity/allowed fields, actual
horizontal bounds of every LOD outside AO, soil contact and root separation.
Moved roots are at least 64.27 inches apart from any other tree root and are
buried 1.67–10.21 inches into the existing soil rather than floating. Median
nearest-root distance for the moved middle trees changes 259.98→158.34 inches
(6.60→4.02 m). This is a geometric spacing metric, not measured needle coverage.
Fresh generation matches all 525 saved tree positions within 0.00734 inch;
the audit allows 0.02 inch for two applications of the scene's six-significant-
digit coordinate encoding, with identical model references.

Matched `groves-before/after-compound` and `forest-groves-ground-before/after`
images inspect saved/staged source geometry using the existing Blender tools.
They retain the documented independent lighting, forced LOD1, static water and
shading approximations; they do not establish native appearance or FPS. Wider
forest/terrain coverage and the full reference composition remain incomplete.
Snapshots/export recipe/audit are in `output/forestbase/groves-before/` and
`groves-stage/`; installed hashes are in `groves-integration.json`. No editor
was opened, connected to or controlled during this revision.

## Aligned facade frames — offline revision

`forestbase_structures.facade_piers()` replaces the old 96-inch front-face grid
with full-height posts in the actual solid wall bays. The former grid cut
through apertures and left disconnected steel strips above/below windows. Both
storeys now share their pier positions. The frame also follows the rear and
side walls of B/C; narrow head bands, flanged connections and outward bolt heads
finish the posts. No glass or bars close the existing openings.

The two installed OBJ meshes contain 88 full-height piers across sixteen
storey/wall faces. Barracks changes 54,210→62,786 triangles and command
29,670→37,462, an increase of 16,368 declared triangles. No scene objects,
textures or shaders are added. Existing material remaps and all nine main
ModelDocs remain byte-identical, including every serialized physics shape.
The scene is unchanged; layout metadata changes only the two triangle counts.
This pass does not resolve the pending native acceptance of earlier collision
changes, nor establish unchanged rendering cost or measured FPS.

`forestbase_facade_piers_audit.py` verifies exact ModelDoc preservation, valid
exported mesh/UV/normal data, all geometry outside structural-steel/hardware
groups, sixteen actual wall definitions, vertically aligned frames and plate
clearance outside every aperture. Minimum plate-to-aperture separation is 29
inches. Matched `barracks-frame-facade-before/after.png` images inspect the
actual meshes under independent Blender lighting. Their metadata was recovered
after the render recorder incorrectly assumed unchanged links were staged;
the importer had correctly used the active unchanged link mesh. The recorder
now follows that same fallback. These previews do not reproduce native shading,
post-processing, import, shadow cost or performance.

Snapshots and the export recipe are in `facade-piers-before/` and
`facade-piers-stage/`; hashes, audit and preview evidence are recorded in
`output/forestbase/facade-piers-integration.json`. Only two active OBJ meshes
and the layout statistics were installed. The editor was not accessed. Full
reference fidelity and current native verification remain unfinished.

## Wooded background relief and continuous soil UVs — offline revision

`forestbase_floor.ridge()` adds broad side/southern shoulders to the existing
outer floor. The northern basin and the southern channel remain open. Control
samples within the first 1,000 inches beyond the compound retain their height;
the existing 192-inch triangulation interpolates the transition in the adjacent
cell. Relief fades to the original world-border height. The accepted amplitude
is 440 inches with a 1,100-inch southern shoulder transition. The initial
720/450-inch candidate produced 64.48-degree remote channel slopes and overly
dominant bare hills; it was rejected and never installed. Its mesh, scene,
overview and diagnostic are archived under `woodland-relief-stage/rejected-tall-ridge/`.

`forestbase_forest.fit_roots()` shifts existing tree roots by the difference
between the new and former triangulated floor heights, retaining their prior
burial. Of 525 trees, 291 change vertical position, by at most 11.15 metres.
Every horizontal position, rotation, scale, model reference, object/component
identity, hierarchy and all other full-scene properties remain unchanged. All
twelve referenced tree ModelDocs have no physics shapes. No objects, trees,
mesh triangles or bitmap textures are added; Vista remains 111,714 triangles.
The other eight main ModelDocs remain identical. Vista's sole ModelDoc change
is one soil-material remap; it still has no boxes or hulls. Layout stays exact.

`forest_soil.vmat` reuses the existing Mud Forest colour/normal/roughness/AO maps
through the engine's standard complex shader, with a darker neutral/green tint.
It affects the outer floor tops. Retained banks, river banks and underside faces
keep their original materials/geometry. The floor now receives a continuous
horizontal world UV chart at its existing 92-inch scale. The automatic uphill
projection rotated between inclined facets; explicitly supplied UVs remove that
discontinuity. `main()` writes the soil material during normal regeneration.
This adds one material surface, so fixed triangle/texture counts do not imply
fixed draw cost, LOD selection, occlusion, shadow work or native frame time.

`forestbase_woodland_relief_audit.py` checks actual exported meshes, all scene
nodes, material remaps, source/scene parity and retained root burial. Its 552
near-field terrain samples and 3,072 grass-root samples have zero height change.
Root burial differs by at most 0.00106 inch; source generation matches the saved
scene within 0.00734 inch after coordinate serialization. The accepted exported
floor has upward faces and maximum slope 40.41 degrees. A separate face-counter
audit proves all 2,184 retained mud triangles preserve positions/UVs/normals,
and the 10,480 replaced floor triangles keep the exact horizontal footprint.
Continuous world UV error is below 0.000005 in texture coordinates. Restoring
the 291 root positions makes the entire scene document identical, including
its top-level settings. Staged cascade materials are byte-identical to active
ones and were not installed.

Matched `woodland-relief-before/after-compound` and
`woodland-relief-before/after-east-rim` images inspect both an elevated view and
a 64-inch eye-height camera inside the eastern perimeter. All final preview
source hashes and scene hashes match the installed candidate. The previews use
the documented independent Blender lighting, forced LOD1, static water and shader
approximations. The elevated view still exposes sparse distant canopy and open
soil; this revision does not establish full reference fidelity or native quality.

Snapshots, recipe and audits are in `woodland-relief-before/` and
`woodland-relief-stage/`. Five active assets (Vista OBJ/MTL/ModelDoc, the new
soil material and scene) were installed; their hashes and evidence are in
`output/forestbase/woodland-relief-integration.json`. The S&box editor was not
opened, connected to or controlled. Fresh native visual/LOD/performance checks,
and acceptance of earlier bridge/hall/cargo collision changes, remain pending.

## Native shader dependency investigation — 2026-10-20 follow-up

Forced material/shader builds did not clear special-dependency mismatches on the
original optic reticle and Forest grass in that process. An identical fresh-name
control material was current. A clean restart with compiled shaders present made
the originals current without material-source edits. This supports stale process
state, but does not identify the precise native cache.

Four editor starts then exited with native access violation c0000005. The
inspected dump identifies rendersystemvulkan.dll +0x25c6ab. Waiting for bootstrap,
empty tabs, Forest Base alone and -vulkan_disable_pipeline_cache did not establish
a stable editor. Missing other-map source textures were logged; causality remains
unproven. Logs, material states and the dump are in
output/forestbase/dependency-repair-20261020/.

The installed CLI was subsequently located at bin/managed/sbox-cli.exe. The old
recursive search had missed it. Read --skill sbox-cli and use its native tools;
use run_csharp scripts in the session exchange directory for uncovered operations.
Temporary bridge shader diagnostics were archived and removed after this discovery.
Their successful build results remain historical evidence, not permanent tools.
The six initial probe asset files were archived and scene-tab preferences restored.

The root .version still reads 26.10.02, but executable files changed at 04:23 UTC
and native CLI game process 33040 reported 26.10.13a. Use running instance_status
as the current version evidence. Official release notes describe later startup
shader reload fixes; they do not prove the cause of the earlier crash. See
[s&box release notes](https://sbox.game/release-notes/).

## Waterfall ribbons and native daylight revision — 2026-10-20

A local CLI-owned game was stable independently of the editor. Its menu was
replaced in memory with the saved map's eight visual groups and the actual
player camera's Sandbox components: 629 model renderers, zero model errors,
1920x1080, ACES and authored map effects. No lobby, actors or bots were started.
The game exited cleanly before source installation. This is native visual
inspection, not a full-match or multiplayer acceptance result.

The installed waterfall shader uses unequal, spatially meandering water ribbons
with wet-rock gaps and bright aerated froth. Geometry, three texture samples,
shared UVs, downward phase progression and the plunge transition are unchanged.
Both candidates actually compiled (four vertex variants and one pixel variant).
ShaderCompiler resets cwd to the engine root and enumerates beneath it; a path
outside that root can exit zero without compiling anything. Successful checks
used fresh scoped sample directories and explicit search paths. Those directories
were then archived outside the engine.

Evidence is in output/forestbase/native-waterfall-ribbons-20261020/. Valid final
captures are native-final-candidate-compound.png,
native-final-candidate-waterfall-player.png and native-final-candidate-entrance.png.
Earlier checker-texture and ineffective shader-switch probes are rejected in
runtime-comparison-notes.json. The test material needed exact native FlowTexture
binding: this legacy project's public texture setter prefixes names with g_t.
The installed map retains its original compiled material and texture sources.

Three timed captures and native-final-motion-audit.json establish changing froth
in three unobstructed stream regions at a fixed camera. Pixel changes do not
independently measure direction or prove physical fluid simulation. The audit
now accepts explicit manifests, regions, shader paths and outputs, validates
image bounds and keeps its historical defaults.

Only six scene fields change: direct sun (0.75,0.80,0.88), ambient sky
(0.14,0.17,0.22), sky tint (0.22,0.26,0.32), gradient-fog alpha 0.45, start 2800
and end 11000 inches. The generator matches. Three lighting candidates were
compared; the final preserves cool daylight and warm practical lights while
revealing more shadow detail and reducing pale background silhouettes. Shared
camera settings are unchanged.

The source audit preserves all 752 scene objects and every field outside those
six values. All 28 protected non-scene core assets (including the accepted stair
correction) and 85 protected material/texture sources are identical. No geometry,
collision, spawn, tree, texture or renderer is added. Source changes are installed;
fresh editor compilation and installed-scene validation follow in the updated
editor. An isolated waterfall-view sample measured 11.78 ms average frame and
11.23 ms GPU time without actors. This must not be called full-match FPS or
compared directly with the old 13-bot diagnostic. Full reference fidelity and
AAA finish remain incomplete.

## Asset provenance

Vehicles, transport cases, buildings, interfaces, palette textures, signage and
water and wet-ground shaders are authored locally by the generator. External assets are CC0
Poly Haven scans: Pine Tree 01, Fir Tree 01 and Fir Sapling (Rico Cilliers / Rob Tuytel), Coastal Cliff 01,
Boulder 01, Mountainside (Dario Barresi / Rico Cilliers), Asphalt 02, Concrete Floor 02, Concrete Wall 007, Wood Planks,
Corrugated Iron 02, Metal Plate 02, Container Side and Rock Face 03
(Dario Barresi / Rico Cilliers). Mud textures are Muddy Tracks
(Amal Kumar) and Mud Forest (eye-candy.xyz), also CC0. Exact source URLs and license
notices are stored beside the imported game assets in `LICENSE.txt`.

## Visual work still outstanding

Installed revisions have native saved-scene renders and model/material checks,
but do not establish the requested modern AAA finish. The next visual work should
address crown shape/shading and native LOD transitions, further natural waterfall integration, more facade
detail and the remaining simple military props. Scanned muddy vehicle lanes are
implemented; further ground dressing and natural transitions need review. The closed scan
Mountainside escarpment replaces the former repeated, vertically stretched cliff curtains; wetness,
SSR and open railings are implemented, but do not establish the full visual target.
Do not describe the current map as meeting the complete AAA objective.

## Objective-wide status

| Requirement | Evidence / remaining work |
| --- | --- |
| Reference layout, compact A–F compound | Implemented; four primary structures and elevated links. |
| Walkable interiors, stairs and roof | Current native audit: 24 complete nav/controller paths and all 22 stair directions pass after moving a cargo pile off the east command entrance stair. Exhaustive mantle/perch and edge-case movement remain unverified. |
| Spawns and closed boundaries | Lower closure installed. Native post-guard: 7,392 boundary-only MoveTo cases and 3,072 cases from all 32 saved spawns pass; 32 floor hits. Unstuck recovery: 96 forced wall/ceiling/floor overlaps plus 96 stance/ordinary-prop regression trials pass. Source floor/ceiling partition closes at radius 0/16. Arbitrary teleports, exhaustive mantle/perch/explosion and remote-client escape tests remain outstanding. |
| Fair fighting routes | Current 112 sampled direct spawn sightlines from seven roof/bridge vantages are blocked. Cover/flanks and loading islands remain. Human balance, all perches and all sightlines remain unverified. |
| Military detail | Vehicles, consoles, tools, shelves, beds and logistics props implemented. Vehicle canopies, sloped armor, fittings and dedicated surfaces improved; 37 wheel proxies and four native collision samples pass. Four beds now have tubular frames, rounded cushions and draped textiles with unchanged collision. Several props and surfaces still look simple. |
| Forest, rocks and waterfall | 525 firs/saplings, denser source-needle LODs, surveyed roots and 24 adjusted shore grass instances installed. Pool bank now covers the actual water contour and joins the floor tangentially; animated soft mist verified. Native views remain visibly below the reference; crown shading/shape, full LOD transitions, waterfall polish and performance remain open. |
| PBR, atmosphere and wet terrain | Scanned materials, localized puddles, mud/tire-track overlays, asphalt repairs, cracks and six drains, leaf-litter floor, improved flat roof finishes, eleven flood fixture aims and stronger warm light pools, reduced cool fill, mild fog and SSR. Visual polish remains outstanding. |
| Multiplayer modes | Fresh offline TDM loads with thirteen bots and one local player, zero model errors. Earlier controlled timed plant/defuse tests remain historical. No 10–15 remote-client test. |
| Stable performance | Historical 600-frame offline 1080p TDM sample predates current roofs/forest/lighting: mean 16.675 ms, p99 20.35 ms, GPU counter 26.11 ms; 90 FPS target unmet. Later native TDM load succeeds, but Vulkan presentation stalls invalidate newer timing windows. Current multi-view and remote-client performance acceptance remains open. |
| Modern AAA visual finish | Not achieved by the current engine renders; the goal remains active. |


### Forest Base project relocation and verified continuation — 2026-10-20
- User confirmed current root: C:/Users/mimi-/Documents/S&box Projects/hc1. The former OneDrive folder contained remaining pieces of an incomplete move. Copied 16,071 missing files (5,437,651,470 bytes), using exclusive creation and retaining originals; no existing destination file was overwritten. All 375 copied Code/Library files match SHA-256; 28 protected Forest core hashes match. Evidence: output/forestbase/project-relocation-20261020/.
- Steam was stopped; started it with -silent. Native editor PID 29888 reports 26.10.13a, correct new root, current Forest Base tab, stopped play, no dirty scene, and successful compilers with zero errors. The failed pre-copy launch's 1,273 cascading diagnostics are historical. Do not recreate missing classes: original sources were recovered.
- The moved files were not all indexed as local source/compiled pairs. Registered 838 supported Forest assets; then registered grass/default texture dependencies and rebuilt forest_grass/shore_grass. The two captured overview passes show the red grass error disappearing. A broad all-Assets registration exceeded its CLI timeout and is NOT claimed complete. Use targeted dependencies and inspect state before retrying timed-out changes.
- Installed shader-only wet-ground revision: localized puddles, rough aggregate between pools, less extreme smoothing/blackening. Native watcher compiled ten variants in 4.65 seconds. Fixed-pose native entrance/overview comparisons and an actual TDM player view verified the installed shader. No map geometry, collision, material or texture source changes in this revision. See output/forestbase/ground-patches-integration.json.
- First 600-frame native offline TDM sample at confirmed 1920x1080, fixed entrance view: one player + nine bots during both measured windows; 16.675 ms mean engine frame cadence (~60), p99 20.35 ms, max 36.17 ms, one >33.3 ms. Native GPU counter averaged 26.11 ms; target 90 FPS was not met. CPU/GPU counters are recorded separately, not added or converted into a claimed GPU frame rate. This single-view editor test is not a multi-view, remote-client or full performance acceptance.
- Console still reports missing first-person shirt/glove PNG source paths; equipment appearance and those dependencies remain to investigate. No repeated special-dependency messages were in the queried runtime buffer. NoDamage and temporary viewport were restored; editor remains stopped on clean Forest Base. Full reference fidelity, forest/prop/facade quality, broad movement/escape coverage and optimization remain unfinished.


### Forest Base roof finishes — 2026-10-20
- Current confirmed project remains C:/Users/mimi-/Documents/S&box Projects/hc1. The active native editor is PID 32080, 26.10.13a, stopped on clean Forest Base; all C# compilers report success/zero errors. It was launched with Windows Start-Process. Do not restart a live editor merely because its attached CLI's startup wait elapsed.
- Barracks and Command now use a flat asphalt/bitumen PBR roof surface, welded lap seams, folded edge caps and screened corner drains. Existing HVAC cover has service doors, latches, condenser fins and attached conduits. Both sheds retain corrugated roofs. Broader, slightly raised seams replaced a first native pass that shimmered.
- Source: Tools/forestbase_rooftops.py, hooks/material mapping in forestbase_map.py, new materials/forestbase/roof_deck.vmat, two OBJ/MTL/ModelDoc sets. Both models and the material are natively compiled/current. Exact serialized PhysicsShapeList tails are unchanged, as are the saved scene and unrelated protected model sources. Existing material slot counts stay 23/20. Added geometry: 1,816 Barracks +1,852 Command triangles. No new texture sources or scene objects.
- Accepted native evidence: output/forestbase/rooftops-integration.json and rooftops-stage-20261020/final-*.png, including the close roof view. The isolated full-map visual scene has 629 models and zero model errors. This is not a new match-performance or remote-client result; the earlier 600-frame sample predates the roof revision. Full forest/props/facade/reference quality and complete gameplay/performance acceptance remain unfinished.


### Forest Base native forest grounding — 2026-10-20
- Confirmed Documents HC1 project, editor PID 32080 / 26.10.13a. Corrected eight tree roots buried beneath the visible Vista rock escarpment and relocated eight existing far-north infill trees onto native-surveyed bare eastern soil. Retained all original crown scales/rotations. Six moved trees use the existing far variant at their new distance; no new renderer or texture files. Global wider/shorter proportions were previewed and rejected.
- Applied in the live editor, explicitly marked the session dirty, and saved with native save_scene. Current scene SHA-256: 2b9ae5afae174ad7b02be33e6ebc7b783abe14249313e7aae1d5f84584a05796. Native save adds defaults, asset Path/Id records and component migrations; an engine-normalized baseline comparison proves all other scene content unchanged (752 serialized nodes, 525 trees). All 16 roots hit native visible ground and sit four inches below it.
- Tools/forestbase_forest.py applies Tools/forestbase_grounded_trees.json after floor fitting, guarded by expected original positions; generator parity passes for all 525 trees (maximum coordinate error 0.007286 inches). Re-survey after landscape geometry changes. Stage audit requires SciPy; current bundled Python lacks it, so dependency is installed outside the project at C:/Users/mimi-/.codex/tmp/hc1-python-deps (PYTHONPATH).
- Native saved-source views: forest-proportions-stage-20261020/final-{compound,waterfall,entrance}.png, 629 models, zero model errors. C# successful/zero errors, stopped clean scene. Evidence: output/forestbase/forest-grounding-integration.json. Maximum declared triangle delta from six existing model-variant changes: 61544; no new match performance claim. Full reference fidelity, movement/escape coverage and multi-view/remote-client acceptance remain unfinished.


### Forest Base flood lighting and fixture aim — 2026-10-20
- Native source scene d53d6691a8fdf850c4f88d2c4aca0b4190315ab4a946203e6616ea4beb2db13b in the confirmed Documents HC1 project. Eleven existing flood heads/light directions now point down 40 degrees (was 58), radius 950in (was 760), with spot RGB x1.8 and point RGB x1.15. Reduced cool daylight/sky fill/tint and darker fog color make the existing warm floor pools more visible; fog distances/density, light counts and shadow settings are unchanged.
- Only source assets changed: ground.obj and Forest Base scene; generator forestbase_map.py matches all 36 light colors and eleven flood poses. Exactly 39 scene nodes changed; all other scene content matches. Ground topology/material slots stay unchanged (10,052 triangles, 14 collision boxes, 6 hulls), exact serialized PhysicsShapeList preserved. Only vertices, face normals and world-projected UVs within 70in of existing lamp heads differ. Ground imported/current with no reported compile failure; the explicit asset_compile observation timed out, so current asset_info and loaded model were inspected instead of blindly recompiling.
- Native saved-source overview/entrance/waterfall and near fixture/interior views have 629 model renderers and zero model errors. Offline native TDM loads at actual 1920x1080, one PlayerPawn + nine lightweight bots, 719 models, zero model errors. This is a load/render check, not a performance acceptance. Evidence: output/forestbase/flood-lighting-integration.json; flood-lighting-stage-20261020/final-*.png and tdm-entrance-1080p.png.
- New FPS sampling could not be validated: Vulkan repeatedly reports no swapchain image/present/fence waits. perf_overview has only 2–3 frames and zero-second timing windows, so its counters are invalid for map FPS. Existing measurement window was shown/active and resized/restored; editor was not restarted. All temporary runtime settings were restored, viewport/camera removed, play stopped, clean scene, C# compile success/zero errors. The earlier 600-frame sample predates current roofs/forest/lighting and is not current acceptance.
- Generic foliage shader candidate was previewed with real twig alpha/PBR inputs but thinned aggregate crowns; rejected and deleted via native Asset.Delete after archiving. Original tree materials remain installed. Full reference fidelity, prop/console finish, exhaustive movement/escape coverage, valid multi-view performance and remote-client checks remain unfinished.


### Forest Base waterfall shore and spray — 2026-10-20
- Current scene SHA-256 8cbf8990611f17e70814d43f5a6d0ea931509b145367c668420813228dc05f52; confirmed Documents HC1 root, editor PID 32080 / 26.10.13a, clean/stopped with successful C# compile and zero errors. Native Vista and shore_bank imports report current/no failures.
- Corrected the exposed rectangular front rim: widened the nonplayable pool-bank opening from plan E[-220,1080], N[2850,4150] to E[-420,1280], N[2650,4150]. The outer slope meets the forest floor tangentially; its scan UVs and dry soil color now continue across the join. Inner bank follows the shared unchanged water-mesh contour (86% inset), with cubic easing that covers the water polygon edge. Source coverage passes at 96 edge samples, minimum bank-over-water edge height 6.791 inches. The opaque water mesh itself, falling sheets and all other 17 material geometry groups are unchanged.
- Rebuilt existing shore stones on the revised slope and adjusted 24 existing shore grass transforms. All other 752-node scene content is identical to the native saved baseline. Native ground traces hit for all 24 grass roots, burial 1.057..2.340 inches. Fresh generator parity passes all 620 scenery instances (max 0.007286 inches). Tree count remains 525. Vista now 111,666 triangles (48 fewer), 21 material slots, no collision; ModelDoc and material table unchanged. No new renderer or texture sources.
- Existing mist shader now advects distinct detail phases, retains low-density wisps, and uses the engine sprite-style depth feather at rock/water intersections. Native isolated valid-material probe confirms animation and softer intersections; initial empty-material checker probe was rejected. No fluid-simulation claim. Mist shader SHA-256 82cecf64a9770d0df4b494a7b401585468d3c7bae1b54281c5fa8449ccfeeba1. Falling-water shader remains 4a234f051858bcd9fb7c486e192a117b16fe0faa4b9cc63ac656344c676bed46.
- Evidence: output/forestbase/impact-mist-integration.json, impact-mist-stage-20261020/installed-audit.json and final-{front,basin,basin-side,compound,waterfall,entrance}.png. The source group patch avoided re-exporting the distant cliff after each bank iteration; patch-shore.py checks 96 actual water-edge points. Final source model/scene is actually installed and rendered (629 models, zero model errors), with no preview transform/material overrides.
- Full AAA/reference finish, complete movement/escape/perch tests, current valid multi-view match performance and remote-client acceptance remain unfinished. No new FPS result: the previous native Vulkan presentation stall is still an open diagnostic, and was not restarted or relabeled as map performance in this pass.


### Forest Base lower closure and unstuck guard — 2026-10-20
- Confirmed Documents HC1 root, native editor PID 32080 / 26.10.13a, stopped/clean with all compilers successful and zero errors. Saved scene SHA-256 c50bc70cbf3154287b6e5ee821bb719672c16ff0286573536bb6a70591c0d3d2. Eight existing walls extended to -1088in and two lower caps added at [-1120,-1024]; 64in wall overlap and 20in main/entrance overlap. Original nine IDs, XY footprint and ceiling preserved. Scene diff contains only 16 wall fields and two new clip objects; all visuals/spawns unchanged, 754 objects/629 renderers. Generator and exact source-partition audit updated.
- Actual CharacterController recovery previously escaped in 11/32 forced wall overlaps and all 32 forced ceiling overlaps. The shared controller now rejects free unstuck destinations whose root ray crosses playerclip from the last known clear root, honoring original ignore/rule settings. After hotload: 96 forced overlaps, zero escapes/unresolved. Stance growth under ceiling and ordinary-prop recovery with/without history: 96 additional trials, zero escapes/unresolved; explicit playerclip ignore preserved.
- Post-guard native MoveTo: 7,392 boundary-only cases across joins/heights/directions/step modes, zero solid starts/escapes; 3,072 saved-map cases from all 32 spawns, zero solid starts/escapes and 32 floor hits. Source partition verifies floor/ceiling closure for radius 0 and 16. These are controlled probes, not exhaustive gameplay/network proof. Forced overlaps do not establish a reachable old escape route from normal play; arbitrary teleports, mantle/perch/explosion and remote-client acceptance remain open. Shared controller applies to other maps too. Evidence: output/forestbase/closed-boundary-integration.json.
- Graphics/reference quality and valid current multi-view performance remain incomplete. No new FPS claim.


### Forest Base cascade relief and canopy width — 2026-10-20
- Confirmed Documents HC1 project. Current native editor PID 31124 / 26.10.13a is stopped on clean Forest Base, C# successful/zero errors. Prior editor and Steam were absent. Cold launch before Steam logged on stalled at SteamAPI_Init; the empty startup process was replaced after Steam login, using verified AppID 590830 in child SteamAppId/SteamGameId and engine working directory. Do not restart a live editor during its asset scan; this cold scan/bootstrap took several minutes.
- Installed waterfall shader de1591b5736b80abf9a7e559b872e72686967a176dcf5d688e8f13364b18fc6e: existing dense grid has up to 5.2in moving normal relief (including recalculated clip position), varying channel centres/widths and advected edges, finer froth patterns and denser core aeration. No mesh/texture/material-path/collider/renderer added. Native material compile passes; loaded material/shader have IsError false. Three installed 1920x1080 views plus three timed fixed-camera captures verify appearance/animation. Editor Time.Now is zero here; pixels change, but this does not measure direction or prove fluid simulation. Source remains visibly below reference/AAA quality. Evidence: output/forestbase/water-volume-integration.json.
- Accepted width-only +18% for 444 dimensional adult/middle/far/understory trees, retaining exact heights/roots/rotations/models/materials and all 81 saplings. Saved natively; source generator ASPECTS/understory match. Scene SHA-256 1c92c90503530224d3af848159a218d473e777a197d6d96cd1f6bdd4f06b6347. Source audit: 444 scale fields plus two unused prefab-map entries regenerated by native save. An independent unchanged-prefab native Deserialize/Serialize yields exactly the same two maps; all other scene content identical. Fresh parity for all 620 scenery instances: max position error .007286in, max scale error .000821 (unchanged Rock 104); pre-existing .001 scale tolerance retained, each actual width-plan change verified to .00001. No new tree, model, material or texture.
- Official foliage-shader preview still thinned crowns with original alpha/reference, no grazing fade and no distance alpha relaxation; rejected, archived and deleted through native Asset.Delete. Original complex twig materials retained. Native GetIndexCountForLod counts the first material mesh in this build (fir_a 15834 = source bark), not aggregate tree triangles. No stale-tree mismatch demonstrated; fir_a asset_info has actual source path/current import. Width increases projected canopy area/overdraw; full-match effect remains unmeasured. Evidence: output/forestbase/canopy-width-integration.json; canopy-width-stage-20261020/installed-hd-*.png.
- Fresh editor now returns nonzero native performance windows (e.g. 37 frames/2.02s), but the saved 54.72ms editor diagnostic has two scene tabs, no controlled player viewport and no aggregate GPU timing. It is not match FPS or a canopy before/after benchmark. The earlier Vulkan stall is historical to that process; valid current multi-view TDM performance still needs measurement. No restart was used to relabel old timing. Full reference finish, gameplay-edge coverage and remote networking acceptance remain unfinished.


### User requested essentials only — 2026-10-20
- Stop expanding graphics scope for now. Saved scene remains 1c92c90503530224d3af848159a218d473e777a197d6d96cd1f6bdd4f06b6347. Latest native compile succeeded/zero errors; TDM started with one player/nine bots and actual 1920x1080 test viewport. Additional bot probe returned zero; no 15-actor result or new FPS acceptance claimed.
- Editor process ended with Source2Shutdown. Temporary runtime camera/window and non-saved NoDamage state are discarded. EditorLobby was false before/during test. No scene/source change during this test. Evidence: output/forestbase/current-performance-stage-20261020/minimal-handoff.json. Further comprehensive work is deferred following the user's request to do only essentials for now.


### Targeted brightness fix — 2026-10-20
- User reported map too dark. Increased sun RGB to (.75,.82,.92), sky fill (.20,.23,.28), sky tint (.30,.36,.45); map tone exposure 1..2, compensation +.15. Applied/saved through native editor and matched in forestbase_map.py. Native entrance/compound/waterfall plus two indoor views checked: 629 models/zero errors. Play resumed with updated lighting; C# zero errors, scene clean. Evidence: output/forestbase/brightness-fix-20261020/integration.json. This is a narrow requested fix; comprehensive goal remains paused.
