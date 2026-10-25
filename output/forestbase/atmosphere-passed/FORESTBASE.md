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

The scene and static building geometry are generated. Change layout in
`Tools/forestbase_map.py`; rerunning it replaces the generated scene and models.
Use Python with NumPy, Pillow and SciPy. The checked-in game assets do not need
Blender or the large source downloads at runtime.

```text
python Tools/forestbase_materials.py
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
Most backdrop trees now use the narrower Fir Tree 01 variants, with approximately
one fifth retaining Pine Tree 01 for variation. Fir near meshes contain 31–55k
triangles, middle meshes 22k, and far crossed-crown cards six triangles. Saplings
use 10k/4k/six-triangle levels. Fir impostors retain source atlas alpha and baked
local branch occlusion, without baking a fixed sun direction. Their ModelDoc
thresholds are 200/500; these are engine thresholds, not stated distances in metres.
Young firs grow on a sloping leaf-litter bank behind the fence. Tree placement uses
separate seeded random streams, keeping the existing rocks and compound reproducible.
The fir importer verifies downloaded MD5 hashes; `--finalize` reuses exported
geometry and bakes. Its Blender path can be changed at the top of the importer.
The current generated backdrop contains 143 firs, 38 pines and 81 saplings,
alongside 82 scanned rock instances. The 20:15 engine overview retains branch
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
These vehicles still need further visual refinement and current runtime timing.
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
hc1_forestbase_perfcapture
hc1_forestbase_perfcontext
dev_perf 600
hc1_forestbase_perfview 1
hc1_forestbase_perfview 2
hc1_forestbase_perfview 3
hc1_forestbase_perfview 4
hc1_forestbase_perfview -1
```

Views 0/1/2 inspect the yard, command-roof overview and close forest respectively.
Views 3/4 inspect the waterfall from the accessible command roof and the torrent
from the sealed entrance bridge.
`perfcapture` renders that inspection camera without HUD into `live-perf-view.png`.
The inspection temporarily raises the runtime TDM early-win limit to avoid a map
change during measurement. View -1 restores the saved limits and camera flags.
It does not change the saved scene or game-mode prefab.

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
Its runtime performance remains unmeasured; a different map was active in the
shared editor during isolated vehicle QA.
Two current runtime captures from the same command-roof camera demonstrate
animated waterfall pixels in `waterfall-uv-motion-audit.json` (29,825 changed ROI
pixels); this verifies visual movement, not physical fluid simulation or
replication. `waterfall-motion-audit.json` retains the earlier water revision.

## Asset provenance

Vehicles, transport cases, buildings, interfaces, palette textures, signage and
water and wet-ground shaders are authored locally by the generator. External assets are CC0
Poly Haven scans: Pine Tree 01, Fir Tree 01 and Fir Sapling (Rico Cilliers / Rob Tuytel), Coastal Cliff 01,
Boulder 01, Asphalt 02, Concrete Floor 02, Concrete Wall 007, Wood Planks,
Corrugated Iron 02, Metal Plate 02 and Container Side. Mud textures are Muddy Tracks
(Amal Kumar) and Mud Forest (eye-candy.xyz), also CC0. Exact source URLs and license
notices are stored beside the imported game assets in `LICENSE.txt`.

## Visual work still outstanding

The current implementation is playable and reference-oriented, but its renders
do not establish the requested modern AAA finish. The next visual work should
address distant foliage silhouettes, further natural waterfall integration, more facade
detail and the remaining simple military props. Scanned muddy vehicle lanes are
implemented; further ground dressing and natural transitions need review. The closed scan
ridge replaces the former repeated, vertically stretched cliff curtains; wetness,
SSR and open railings are implemented, but do not establish the full visual target.
Do not describe the current map as meeting the complete AAA objective.

## Objective-wide status

| Requirement | Evidence / remaining work |
| --- | --- |
| Reference layout, compact A–F compound | Implemented; four primary structures and elevated links. |
| Walkable interiors, stairs and roof | 24 complete paths with endpoint checks and controller traversal, including eight room targets; 22 stair directions passed. Shelves and the roof landing were corrected after the stricter checks exposed failures. |
| Spawns and closed boundaries | 32 floor/clearance samples, six boundary traces passed; exhaustive escape exploits are not proven. |
| Fair fighting routes | Cover, flanks and protected team spawns implemented; 112 sampled spawn rays blocked. Human multiplayer balance remains unverified. |
| Military detail | Vehicles, consoles, tools, shelves, beds and logistics props implemented. Vehicle canopies, sloped armor, fittings and dedicated surfaces improved; 37 wheel proxies and four native collision samples pass. Several props and surfaces still look simple. |
| Forest, rocks and waterfall | Fir/pine variations and young firs with three LODs, sloping forest verge, closed scanned ridge, six animated streams, recessed basin and sloping torrent banks. Distant foliage and water/cliff integration still need refinement. |
| PBR, atmosphere and wet terrain | Scanned materials, mud/tire-track overlays, asphalt repairs, cracks and six drains, leaf-litter floor, reduced cool daylight, 23 downward spots and 13 points, mild fog, rain shader and SSR; visual polish remains outstanding. |
| Multiplayer modes | Local TDM with bots; complete timed plant/defuse rounds and input cancellation at both sites passed under documented controls. 10–15 remote clients remain unverified. |
| Stable performance | Current water/fir-UV sample averaged 46.01 ms with 7–9 bots in a 1140×446 editor view during documented shared GPU activity. Earlier samples, hitch, slow startup and editor hang remain documented. A full-resolution unloaded comparison and remote-client load test remain outstanding. |
| Modern AAA visual finish | Not achieved by the current engine renders; the goal remains active. |
