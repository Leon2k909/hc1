# Ares transport cases, revision 2

Applied to `C:\sbox-projects\hc1\forked-shooter-main` on 2026-10-26.

The 132 equipment cases in Ares now use four shared models, each with three LODs.
The two original sizes, poses, markings, stack heights and collision envelopes
are retained. The old cuboid faces and painted hardware were replaced with
rounded moulded shells, recessed folding handles, lever catches, hinges, gasket
seams, stacking features, pressure valves and Ares identification plates. Private
polymer, rubber and metal materials include restrained dust and handling wear.
The marked variants retain the original Mars slogan.

## Installed resources

- `Assets/models/props/ares/crate-v2/`: standard/cargo, plain/marked models.
- `Assets/materials/ares/crate-v2/`: nine private materials and their textures.
- `Assets/models/maps/ares/crate-v2/dressing-base.obj`: the existing dressing with
  exactly 12,408 old case triangles removed. Other geometry and OBJ indices are
  unchanged. The original canonical dressing OBJ was preserved.
- `Assets/models/maps/ares/ares_dressing.vmdl`: only the render import changed;
  its physics definitions remain byte-identical.
- `Assets/scenes/maps/Ares/ares.scene`: the saved `ARES transport cases` group,
  containing 132 renderer-only objects. No extra colliders or gameplay components.

The group and models were created using native editor tools and persisted with
native `save_scene`. `scene-instance-ids.json` stores those actual object and
renderer UUIDs so source regeneration keeps the saved references stable.

## Source and rebuilding

`Tools/ares_cargo_case.py` supplies the materials, markings, variant wrapper,
far LODs and saved scene group. `Tools/ares_case_shell.py` is the independent
Ares fork of the established case construction; it does not change Veridant.
The reference snapshot is `reference-case-detail.py.txt`.

`Tools/ares_map.py` keeps the legacy `case` signature. Its helper now appends
reusable case instances and the original collision boxes; `write_scene` adds
their group. Both normal generation and scene-only generation use the saved IDs.
The original baked-case function is preserved in `original-case.py.txt`.

`Tools/ares_stage_cargo_cases.py` builds a guarded asset staging package and
verifies the exact original case poses, dimensions and collision. Current final
asset staging is `output/ares/crate-v2/stage-v7`. Do not replay the initial
`integrate.cs.txt`: that diagnostic used transient C# objects before the saved
instances were created with native `spawn_models`.

Run `rtk proxy python -X utf8 Tools/ares_check_cargo_cases.py` to validate the
installed resources against their recorded native checks and captures. It writes
`installed.json` here and `output/ares/crate-v2/validation.json`.

## Validation

- All nine materials, four models, dressing and saved scene compiled natively.
- 132 saved model references, positions, rotations, scales and UUIDs checked.
- All 12 model/LOD combinations checked for closed lid corners.
- Seven native captures reviewed, including forced LOD 0, 1 and 2 across all
  132 instances. Camera, exposure, material and LOD state restored after captures.
- Standard/cargo collision traces hit the retained dressing collider at 60/90
  inches, matching the original two-case stack heights.
- Original authored scene properties preserved. Native saving adds defaults,
  numeric formatting, typed resource references, editor metadata and reflection
  probe/prefab serialization migrations. Every difference is classified; defaults
  and migrations were measured using inactive disposable objects, without editing
  the user's scene.
- Independent pressure-door work was preserved. Its hall resources were not
  restored from an old snapshot or overwritten by this task.

The models use 8,868/6,356/520 triangles for plain near/medium/far variants and
8,170/5,722/522 for marked variants. Four assets are shared across the map;
frame-rate impact has not been benchmarked.

Final images are in `output/ares/crate-v2/captures/final/` (`hall-stack`,
`hardware`, `player`, `cargo`). The corrected far LOD capture is
`captures/lod-check-fixed/player-lod2.png`. The hall before/after images use the
same camera and exposure. Earlier `after-v1` and uncorrected `lod-check` LOD 2
images are diagnostic history, not the installed result.

`installed.json` records final hashes, model variants, saved group, validation,
native save receipt and screenshots. The pre-edit scene snapshot is at
`output/ares/crate-v2/stage-v5/before/Assets/scenes/maps/Ares/ares.scene`.

## Distance fix (2026-10-31)

The user saw the cases fall apart a short way off. Two causes, both measured in
the engine at 1920 x 1080 with a 90 degree FOV:

- LOD thresholds 10/24 switched at 190 and 456 in, so the plain far shell showed
  from 11.6 m. They are now 30/80: LOD 1 from about 14.5 m, LOD 2 from about 38.6 m.
- The alpha-tested stencil broke into blotches beyond about 11 m. It is now
  `F_TRANSLUCENT`, and fades to a soft grey with distance. At 3 m it looks the same.

Geometry, textures, placements and the scene are unchanged. The comparison is
`output/ares/crate-v2/captures/distance-fix/before-after.png`. `installed.json`
and the stage-v7 manifest predate this fix, so they still record the old hashes of
those five files, and `Tools/ares_check_cargo_cases.py` stops at them until the
cases are staged again.
