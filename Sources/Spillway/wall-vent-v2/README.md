# Spillway turbine hall wall vent v2

Built 2026-11-03, **approved and installed 2026-11-04** after the matched s&box review.

Selected after the approved yard hose installation. The first turbine hall wall vent is a block housing with shallow repeated blades,
386 triangles, at plan e -1328..-1304, n about 220, z 25..118. It is merged into `spillway_west.obj`; the same arrangement also exists
farther along the wall at n 1150. Only the first unit has been replaced; the second remains as it was.

The new unit has separate folded cheeks and pans, an actual recessed plenum, two banks of eight folded drainable blades with front
drips and upturned back edges, a central mullion, backing screen, a rain cap, captive bolts, lower service panel and EXTRACT T1 plate.
The housing is weathered blue-grey paint, the blades dull alloy, with modest edge wear and rain streaks beneath fasteners.

- Place at engine `220,1328,25`, no rotation. Local X runs across the face, -Y projects from the wall, Z is up. Main body 100 x 93 in,
  24 in projection; the rain cap adds .5 in each side and .6 in height. The old unit's approximate wall envelope is preserved.
- 5,096 / 2,548 / 238 triangles, LOD thresholds 30 / 80. One material, one 2048 atlas, about 4.8 px/in across this large unit.
  The far mesh retains the blade silhouette while dropping bolts, screen and plate geometry. Forced LOD 2 checked in s&box.
- No physics shapes. Installation retains the existing west-model collision box and hulls, with no new collider on this unit.
- Native asset compilation succeeds on engine 26.11.03a. Outward-face check: 88 connected pieces, zero inside-out triangles. Five
  same-camera before/after views checked (standing, front, low, detail, far), plus forced distant-LOD captures. No gameplay test or
  performance benchmark. The active Railhead document was preserved.

`vent.py` reuses the verified pallet mesh pipeline for UVs, LODs, bakes and OBJ export, and the capture flag's mesh toolkit. Intermediate
objects and baked arrays keep the shared `pallet` / `bake_pl_` names. The bake occluder is changed from a floor to a wall. Export removes
the generic pallet physics block. `paint_vent.py` paints from world position, normal, part and AO bakes; all materials are procedural,
with no external images or new dependencies. `vent_parts.json` records the mesh's parts.

From the canonical project root, run sequentially. The Blender helper uses four threads and idle priority and exits when done:

```powershell
$ventRoot = 'C:/sbox-projects/hc1/forked-shooter-main'
$ventWork = "$ventRoot/output/asset-improvement-20261030/spillway-vent"
rtk proxy powershell -NoProfile -File Sources/Belltower/props/pew-v2/blender_idle.ps1 -Script "$ventRoot/Sources/Spillway/wall-vent-v2/vent.py" -Log "$ventWork-build.log" $ventWork $ventRoot build bake
rtk python Sources/Spillway/wall-vent-v2/paint_vent.py $ventWork "$ventRoot/Assets/models/maps/spillway/wall_vent_v2"
rtk proxy powershell -NoProfile -File Sources/Belltower/props/pew-v2/blender_idle.ps1 -Script "$ventRoot/Sources/Spillway/wall-vent-v2/vent.py" -Log "$ventWork-export.log" $ventWork $ventRoot export
rtk python Sources/Spillway/wall-vent-v2/prepare_review.py
rtk python Sources/Spillway/wall-vent-v2/review.py compile
rtk python Sources/Spillway/wall-vent-v2/review.py capture
rtk python Sources/Spillway/wall-vent-v2/review.py lod2
rtk python Sources/Spillway/wall-vent-v2/sheets.py
rtk python Sources/Spillway/wall-vent-v2/review.py check
```

Captures and receipts: `output/asset-improvement-20261030/spillway-vent/`, main sheet `matched/comparison.png`. The native client is
`Sources/Spillway/hose-coil-v2/native.py`: it attaches to the editor, writes scripts in its exchange directory, and closes its connection
and deletes those exchange files when done. Each render uses an isolated scene which is destroyed in `finally`.

Archived comparison resources: `Assets/models/compare_old/spillway_vent_v2/old_vent.*` and `west_rest.*`. For the comparison, four shared material
slots on the west renderer are hidden; `west_rest` restores the 20,558 other faces in those slots, leaving out only the first vent's
386 faces. All original UVs and normals are retained. The comparison was refreshed against the current west mesh after the interruption.
`review_manifest.json` holds the saved west mesh, scene and generator hashes; `review.py check` requires matching saved mesh and scene
hashes and separately reports generator drift. Unrelated service-cabinet work changed the generator during this review; the hose's
placement remains present, and this vent review has not written the generator.
The shared `models/compare_old/hidden.vmat` is reused and must be retained for other reviews.

## Installed state

`install.py prepare` staged the current west model, saved scene and generator without overwriting any of them. `install.py apply`
checked their hashes and both west collision hulls, backed up the three files, removed exactly the selected 386 faces through the editor,
and saved the unopened Spillway `SceneFile` using the native resource API. The user's Riverside document stayed active.

The saved scene differs from its backup only by `Turbine Wall Vent 1`, a renderer at `220,1328,25` with no collider. Both west hull OBJ
files are byte-identical to their pre-install versions. The generator keeps the first unit's invisible metal collision box, draws the
original second unit, and places the new first renderer on rebuild. Other generator edits, including service cabinets, were preserved;
the map generator was not run.

`rtk python Sources/Spillway/wall-vent-v2/install.py validate` checks those saved changes and uses an isolated native scene to confirm:
one valid vent, one retained hose, no added colliders or error models; rays hit the old vent's front at y 1310 and top at z 118, the floor
just in front at z 0, the unchanged second vent's top at z 118, and the hose's floor at z 0. Three installed renders were checked.
Native installation/validation receipts are in the work folder, with captures under `installed/`. Not playtested in a match.

`install.py archive` moved the twelve vent-specific comparison sources, metadata and caches to `retired/comparison_sources/`, keeping
the shared hidden material. The old mesh, scene and current generator backups are under `retired/`. The one-time apply step refuses
changed inputs or existing backups rather than overwriting them. The original candidate review commands require restoring their
comparison assets and original source geometry first; use installed validation for the current map.
