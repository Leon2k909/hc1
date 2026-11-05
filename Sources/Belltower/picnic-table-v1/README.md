# Belltower beer-garden picnic tables — installed

Reviewed at plan (-800, -600, 0), yaw 90°, in the inn's beer garden; approved and installed across all ten mirrored picnic tables on 2026-11-04. Each retains the original 84 × 72 footprint, 30-inch tabletop height, 18-inch seat height and existing wood finish. The 4,244-triangle model replaces the original 60-triangle assembly with six individual top boards, two slats per bench, eased edges, exposed end grain, open A-frame legs with flat-cut feet, cross bearers, a long stretcher, knee braces and separate iron fixings.

The existing scanned `wood_planks.vmat` and `wood_planks_dark.vmat` supply the timber finish. Seam-free strip UVs follow each board; their explicit UVs compensate for the materials' existing shader multiplier. Existing black iron and oak end-grain materials supply the hardware and cut ends. No texture pixels, material definitions, lights or emissive surfaces are changed or added.

The live Belltower west model imports bounded compiler-safe meshes. Only 36 matching faces in its planks import and 24 in its dark-planks import are removed from private copies. All other vertex/UV/normal records and faces stay intact; every other import, material remap and the complete ModelDoc physics section remain unchanged. The original table's broad cover collider remains. The canonical town OBJ, saved scene, other tables and all installed town upgrades are preserved. Do not regenerate the whole town or force-compile its large models.

From `C:\sbox-projects\hc1\forked-shooter-main`:

```powershell
rtk python Sources/Belltower/picnic-table-v1/build.py
rtk python Sources/Belltower/picnic-table-v1/setup.py
rtk python Sources/Belltower/picnic-table-v1/review.py
rtk python Sources/Belltower/picnic-table-v1/verify.py
```

Build stages outside Assets. Native import writes only the private preview files, and compilation is incremental. The capture starts its own offline play session only from a saved, stopped editor, waits for a player, uses the same camera/light/exposure for both variants and allows normal texture streaming to settle. It then stops its session and restores the previous editor scene. No frame-rate benchmark is claimed.

Artifacts: `output/belltower/picnic-table-v1/table-comparison.png`, the pre-install `validation.json`, and full screenshots under `runtime-review/`.

## Installation

`prepare_install.py` stages guarded streaming splices rather than regenerating the town. The four shared compiler-safe wood imports lose all 600 old table triangles. Both canonical town OBJs lose the corresponding 300 old triangles per half and include the new geometry, so regeneration caches agree. Both public ModelDocs import five new tables using `installed_west.obj` / `installed_east.obj` and distinct `bt_pt_` material aliases. Unrelated geometry and complete physics suffixes are preserved. `Tools/belltower_picnic_table.py` supplies the exact approved model; the production `picnic_table()` no longer draws the old boxes and retains the original cover collider.

Native checks loaded both public models and all materials, then captured the west and east gardens in actual offline play with a player and no error models. Scene/play state was restored. Receipt: `output/belltower/picnic-table-v1/installed.json`; screenshots: `runtime-installed/west-installed.png` and `east-installed.png`.

The user requested deletion of the old version. In addition to removing all old production table geometry, `cleanup-preview.cs.txt` audited asset references and removed the obsolete preview-only town ModelDoc, its two base OBJ/MTL pairs, generated metadata and compiled preview model. No production references existed. Receipt: `obsolete-preview-cleanup.json`. The review sources remain archived outside Assets in the output stage and backups. The build/review commands above describe the pre-install trial; reproducing it now requires the archived original sources, rather than running the migration on already-installed geometry. Use `verify_installed.py` for current validation.
