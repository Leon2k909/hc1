# Spillway yard floodlight mast v1 (2026-11-06)

The four yard floodlight masts on Spillway, rebuilt as one standalone model: `models/props/spillway/floodlight_mast_v1/mast.vmdl` (3 LODs).

**UPDATE 2026-11-06: the user approved the new masts ("after is much better, delete old"). The old masts are deleted: their triangles are
gone from `spillway_cargo.obj`, `Tools/spillway_map.py` `cargo_yard()` no longer draws them (it still makes their lights), and
`old_mast_*.obj`, `cut_faces.json`, `install.py`, `revert.py`, the test and `retired/` were removed, so the revert and install sections
below are history only. The four `Yard Floodlight Mast` objects are not made by the generator: they live in `spillway.scene` (a generator
rerun would need them added in `scene()`).**

(Original text:) **Installed in the live scene as `Yard Floodlight Mast 1..4` under `Spillway`. The old masts are kept, and
`python Sources/Spillway/floodlight-mast-v1/revert.py <project root> --apply` puts them back exactly (tested, below). Nothing is committed.
The user decides whether to keep the new masts.** Part of the three-model trial (`output/model-trial-20261106/BRIEF.md`).

## The old mast

`Tools/spillway_map.py` `cargo_yard()` builds each mast into the merged `Assets/models/maps/spillway/spillway_cargo.obj`: a 6 in untapered
rod on an 18 x 18 x 13 in box, a bare crossbar and two 20 x 7 x 5 in wall-pack boxes. 528 triangles, five materials (452 of the triangles in
dark Riverdale steel), no LODs, no collision, one dark grey. No base plate, bolts, taper, hand-hole or braces, and the lamp glass is 4
triangles. The masts stand on the yard floor (one on the raised platform) where players walk past them, and against the sky from any distance.

## Where it is now

Each is a `ModelRenderer` on `mast.vmdl`, Rotation `0,0,1,0` (yaw 180, so the heads aim plan south as the old lamps did), no collider.
The scene's lights (`Yard mast <e> +-35`) were not touched.

| # | plan (east, north, floor z) | scene Position (n,-e,z) |
|---|---|---|
| 1 | 570, -400, 0 | -400,-570,0 |
| 2 | -1110, -600, 0 | -600,1110,0 |
| 3 | 1290, -250, 0 | -250,-1290,0 |
| 4 | 1630, -1600, 128 (raised platform) | -1600,-1630,128 |

## BEFORE / AFTER (native editor viewport, matched)

All in `output/model-trial-20261106/spillway/`, 1102 x 455 px, FOV 80, same camera for both of a pair (`camera_poses.json`).

| view | BEFORE | AFTER | camera (world position / angles) |
|---|---|---|---|
| close, 90 in from mast 1 | `before.png` | `after.png` | -325.12,-520.08,64 / 22,-146.31,0 |
| 12 m (472 in) | `before_far.png` | `after_far.png` | -7.27,-308.18,64 / -10,-146.31,0 |
| heads, 260 in, looking up | `before_head.png` | `after_head.png` | -183.67,-425.78,64 / -35,-146.31,0 |
| masts 2, 3, 4 at 420 in (10.7 m), new model only | | `other_masts/mast{2,3,4}_12m.png` | in `camera_poses.json` |

How they were taken: the bridge's `screenshot_game` (its WindowCaptureHandler: a PrintWindow of the editor window), cropped to the 3D
viewport (x428 y100 w1102 h455), with the editor camera placed by `set_editor_camera`. No temporary camera, cloned or isolated scene,
`RenderToBitmap`, changed exposure, lighting or post settings, Blender render or Computer Use. BEFORE was shot with the old masts really back
in the scene (the live `revert.py --apply`), AFTER after `install.py --apply`; both files came back byte for byte each way. 9 s settle, the
model's own textures requested with `MarkUsed` (2048 at most, nothing else). Mean luma of the pairs 29.7 / 30.5 (close), 69.1 / 69.1
(12 m), 129.4 / 129.3 (heads); the rest of each frame (gizmos, ghost figures, light icons) is identical.

The editor's dock layout changed while this was being done (Asset Browser and Console now sit under the viewport, so the viewport is 455 px
tall, not 713). The first BEFORE shots, and AFTER shots with the dock showing, did not match the later ones, so both sides were retaken in
the new layout; the earlier ones are in `superseded/` with `camera_poses_first_layout.json`. `retired/` holds the pre-install copies of the
cargo OBJ and the scene and `install_record.json`.

## Numbers (`Tools/model_stats.py`; full output in `stats_before.txt` / `stats_after.txt`, JSON beside them)

| | BEFORE (one old mast) | AFTER (new model) |
|---|---|---|
| LOD0 triangles / vertices | 528 / 392 | 8,654 / 5,054 |
| LOD1 / LOD2 triangles (switch thresholds) | none (baked into the cargo OBJ) | 3,842 (38) / 932 (105) |
| Materials / unique texture files | 5 / 13, all `shared` | 3 / 8 (5 new, 3 shared) |
| Largest texture (px) | 2048 x 2048 (shared concrete scans, plinth) | 2048 x 2048 (new colour, normal, roughness; the shared scans too) |
| Total texture pixels (MP) | 23.07 (shared) | 27.26 (new 14.68 + shared 12.58) |
| Est. GPU texture memory (MB, RGBA8 + mips) | 117.33 (shared) | 138.66 (new 74.66 + shared 64.00) |
| Compiled `vmdl_c` / `vtex_c` total (KB) | n/a (inside `spillway_cargo.vmdl_c`) / 24,885 (shared) | 255 / 23,601 (new 5,406 + shared 18,195) |
| Object size (in / m) | 91.6 x 322.1 x 18.0 / 2.33 x 8.18 x 0.46 | 94.0 x 312.6 x 28.5 / 2.39 x 7.94 x 0.73 |
| Instances in the map -> total LOD0 triangles | 4 -> 2,112 | 4 -> 34,616 (net +32,504, 16.4x per mast) |
| Collision (hulls/boxes) | none | none (unchanged, see below) |

Commands (from the project root; `old_mast_1.obj` is the first of the four identical old masts):

```
python -I Tools/model_stats.py --label BEFORE --obj Sources/Spillway/floodlight-mast-v1/old_mast_1.obj --vmat materials/riverdale/rv_dark.vmat --vmat materials/riverdale/rv_steel.vmat --vmat materials/spillway/sw_trim_v2.vmat --vmat materials/riverdale/rv_lamp_warm.vmat --vmat materials/riverdale/rv_zinc.vmat --json Sources/Spillway/floodlight-mast-v1/stats_before.json
python -I Tools/model_stats.py --label AFTER --vmdl models/props/spillway/floodlight_mast_v1/mast.vmdl --json Sources/Spillway/floodlight-mast-v1/stats_after.json
```

Notes on the table:

- BEFORE: the five OBJ materials resolve through `spillway_cargo.vmdl` to Riverdale's `rv_dark`, `rv_steel`, `rv_zinc`, `rv_lamp_warm` and
  Spillway's `sw_trim_v2` (as `rv_plinth`). `rv_zinc` and `rv_lamp_warm` are plain constants, so the 13 texture files are `rv_dark` x5 and
  `rv_steel` x5 at 1024 sq and the `sw_trim_v2` concrete scans x3 at 2048 sq. All of them are shared with the rest of the map: taking the
  old masts out frees no texture memory (the cargo model still draws 2,450 `rv_dark`, 684 `rv_zinc` and 72 `rv_plinth` faces, and other
  Spillway models use `rv_steel`).
- AFTER: `mast_hw` is new (5 files: 14.68 MP, est. 74.66 MB, 5,406 KB compiled). `mast_pier` is the existing `materials/spillway/sw_trim_v2.vmat`
  (the concrete scans the map already loads). `mast_lens` is Riverdale's `materials/riverdale/rv_lamp_warm.vmat` (no texture). So what the
  mast adds to the map is the 5 new files.
- "Est. GPU" is the brief's worst case (RGBA8 with a full mip chain). BC7 would be about a quarter of it (the new files about 18.7 MB); the
  compiled size of the new files, 5.4 MB, is the more realistic footprint.
- `model_stats` shows the roughness and metalness maps as 0 B compiled: s&box packs them into the normal map's generated texture
  (`mast_hw_normal_png_*.generated.vtex_c`, 2048 sq BC7). The AO is its own 1024 sq ATI1N.
- The LOD thresholds are in `mast.vmdl` (`model_stats` prints them as null): 0 / 38 / 105, by the code comment LOD1 from about 19 m and
  LOD2 from about 52 m. The 12 m shots therefore show LOD0.
- Height: the new mast is 9.5 in lower than the old (312.6 against 322.1 in). The scene lights stayed where they were (17.5 in out from the
  pole, 35 in each side, 300 in up), and the new floodlight bodies now sit at them; the old lamp boxes sat above them.

## The model

A 26 ft hot-dip galvanised lighting mast as a plant yard really has one. Built in Blender by `mast.py` (inches, engine axes: +X is the way the
lamps face, +Y left, +Z up, origin on the floor at the pier) with the capture flag's mesh toolkit (`Sources/Gameplay/capture-flag-v2/build.py`).

- a poured 22 in pier with chamfered corners and a grout pad; a 12 in base plate on four anchor bolts, with ribs and a fillet weld
- a tapered round pole, radius 3.45 in at the plate to 1.9 in at the top (pole top at 299 in) in telescoping lengths with a slip-joint
  sleeve and set screws; the lowest 66 in is safety yellow with a hazard band
- a reinforced hand-hole with its cover and screws, a brass earth lug and a riveted data plate
- a welded hub with a 94 in cross-arm through it and two braces back to the pole
- two LED floodlights on yokes, tilted 28 degrees down, 35 in either side of the pole: cast body with cooling fins, hinged bezel and
  gasket, glass, visor, trunnion bolts, U-bolt clamps, and a cable from each lamp to the pole

125 parts, 956 UV islands, all in one 2048 sq atlas. Every part carries a LOD level. LOD1 leaves out the smallest parts (set screws, lug
fixings) and halves the rest of the steel and the pier to 60 %; LOD2 leaves out every part below level 3 (all the bolts and small fittings)
and decimates the steel to a third, the pier to 35 % and the lens to half.

## Textures

- `mast_hw` (new): colour, normal and roughness at 2048 sq, metalness and AO at 1024 sq. Every map is authored by `paint_mast.py` with
  numpy from the bakes `mast.py` makes (position, normal, part id, AO). **They are procedural, not built from the scan sets.** Wear is worked
  out in 3D from each texel's baked position and normal, so it runs across UV seams and is the same size in inches on every island:
  yellow paint over zinc, chipped on the lower mast where trucks and people reach, rust in and running down from the chips; zinc spangle
  with white rust and soot streaks; dark powder-coated housings chalked on top and rubbed to aluminium on the fin tips and bezel rims.
- `mast_pier`: the project's real concrete scans (`concrete_layers_02`, 2 k) through the existing `sw_trim_v2` material, so the pier matches
  Spillway's other concrete.
- Resolution choice: one 2048 sq atlas for the whole mast. That gives about 29 px/in on the lowest part of the pole and the plate (the 40
  px/in aimed for was **not** reached), and about 7 to 12 px/in on the floodlight heads, which are seen from below and further away.
  Metalness and AO are low frequency, so 1024 sq. Nothing is 4096.

## Reuse search (done first)

Nothing existing is a whole mast, so the model is new; the two shared materials above are reused. Looked at: Orion's yard lamp head
(`docs/notes/orion-yard-lamp-v1-20261104.md`, a single lamp head of about 3,000 triangles, no pole), Riverside's cobra-head streetlight v2
(`docs/notes/riverside-street-lamp-v2-review-20261104.md`) and its searchlight, Sewage's caged work lamps (`docs/notes/sewage-work-lamps-v1-reuse-20261104.md`),
Veridant's forecourt lamp posts (`Sources/Veridant/forecourt-posts-v1/README.md`), and `Assets/models/props/**`. None has a 26 ft pole with
a cross-arm, braces and two floodlights.

## Collision

None, as before. The old masts had no collision (the cargo model's hulls file has 32 vertices, far from any mast), and `scene_trace` rays
through the new pole and pier hit only the `Ground` / `Yard` colliders. The pole stays walk-through, so no route is blocked for players or
bots. A pole collider could be added if wanted; it would change how the yard plays.

## Install and revert (tested)

```
python Sources/Spillway/floodlight-mast-v1/install.py <project root>            # report only
python Sources/Spillway/floodlight-mast-v1/install.py <project root> --apply
python Sources/Spillway/floodlight-mast-v1/revert.py  <project root>            # report only
python Sources/Spillway/floodlight-mast-v1/revert.py  <project root> --apply    # the old masts come back
python Sources/Spillway/floodlight-mast-v1/test_install_revert.py <project root> <scratch dir>
```

Close the Spillway scene in the editor before `--apply` and open it again afterwards, so the editor cannot write its older copy back.

- `install.py` takes the four old masts' 2,112 triangle lines out of the live `spillway_cargo.obj` (recorded line by line in `cut_faces.json`
  with the file's hash before and after) and inserts the four objects into the scene as text (the scene is CRLF; a JSON writer would
  change more than the masts). It checks every line, the hashes, that the model is compiled, and that taking the objects out again gives the
  original scene byte for byte, and stops if anything is not as expected. The copies and hashes go to `retired/install_record.json`.
- `revert.py` puts only its own lines and objects back (by line index and by guid), so other sessions' later edits to the same two files
  survive. If the cargo model was changed since the install it stops and says so; `--restore-retired-obj` copies the retired original back.
  The new model and materials stay on disk, unused.
- `test_install_revert.py` (17 checks, all pass, `test_install_revert.log`): install and revert on a scratch copy give the original files
  byte for byte; a second install or revert is refused or changes nothing; an edit made to the scene by someone else between the two
  survives; a changed cargo model is refused; an uncompiled model is refused. The live files were also reverted and reinstalled once for
  the BEFORE shots and came back byte for byte. Live now: cargo OBJ = the recorded after-cut file, scene = the recorded install result.

## Rebuild from source

Blender 5.1, `numpy`, `scipy`, `Pillow`. Work dir: `output/model-trial-20261106/spillway/work/mast`.

```
powershell -File Sources/Spillway/floodlight-mast-v1/blender_idle.ps1 Sources/Spillway/floodlight-mast-v1/mast.py <log> <work dir> <project root> build bake
python Sources/Spillway/floodlight-mast-v1/paint_mast.py <work dir> Assets/materials/spillway/floodlight_mast_v1
powershell -File Sources/Spillway/floodlight-mast-v1/blender_idle.ps1 Sources/Spillway/floodlight-mast-v1/mast.py <log> <work dir> <project root> export
```

The editor compiles `mast.vmdl` and the material by itself; do not force-compile. `check_faces.py` is the per-face outward check,
`preview.py` the author's quick Workbench looks (neither is review evidence), `extract_old.py` made `old_mast_1..4.obj`, `old_masts.mtl`
and `cut_faces.json` from the live cargo OBJ.

## Files

Created: `Assets/models/props/spillway/floodlight_mast_v1/` (vmdl, 3 LOD OBJs, mtl, compiled vmdl_c),
`Assets/materials/spillway/floodlight_mast_v1/` (vmat, 5 PNGs, compiled), this folder, `output/model-trial-20261106/spillway/`
(captures, `retired/`, `superseded/`, `survey/`, `work/`).

Changed: `Assets/models/maps/spillway/spillway_cargo.obj` (2,112 triangle lines removed; the cargo model recompiled itself) and
`Assets/scenes/maps/spillway/spillway.scene` (four objects added under `Spillway`). `git diff` of these two against HEAD also shows other
sessions' earlier uncommitted work; only those lines and objects are mine.

Not changed: `Tools/spillway_map.py`. Rerunning it would draw the old masts again and overwrite the cut (and the later native work in the
live files), which is also why the earlier Spillway upgrades were not regenerated. If the masts are kept, take the mast calls out of
`cargo_yard()` first. No index line was added to `CLAUDE.md` (a shared file other sessions edit); add one for this README if it is kept.

## Not verified

- A running match: no play session was started (nobody else's was touched). Frame cost was not measured.
- Night or other lighting: Spillway's single lighting setup only; the scene lights were left as they were and not re-tuned.
- The masts were checked in the editor viewport only. Masts 2, 3, 4 were looked at once each at about 10.7 m (`other_masts/`): they
  stand on the floor, the right way round. A `scene_trace` straight down at masts 2 to 4 found no collider under them in the editor
  scene (the `Yard` collider covers only part of the map); that is the same as before the change.

## Verdict

Much better as a model at the distances players see it: a pole with a base plate, bolts, taper, hand-hole and hazard band, and heads with
fins, bezels and visors, against a bare rod, a box and two flat boxes. Where it is weaker, and why the user may still reject it:

- The colour changed. The old mast was one dark grey; the new one is safety yellow low down and bright galvanised above, so the upper pole
  is paler than before, and the yellow is a new colour accent on the yard. The palette is set in `paint_mast.py`.
- The metal textures are procedural, and the 40 px/in aimed for was not reached (about 29 px/in on the lower pole).
- 16 times the triangles per mast at LOD0 (34,616 for four), still 7 times the old at LOD1, and 74.7 MB of new estimated texture memory
  (5.4 MB compiled) that the old masts did not use.
- It is 9.5 in lower than the old mast, and still has no collision.
