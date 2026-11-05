# Railhead smoking-area ash columns — all four installed

The approved design now replaces both island and both outer-platform columns, at plan e ±601 and ±1131, n -891. The live east base (`cable-drum-v1/east_without_drum.obj`) and west base (`extinguisher-v2/west-base.obj`) each have exactly 588 old render triangles removed: 1,176 total. Unrelated faces and vertex/UV/normal records remain. Both public dressing ModelDocs preserve their existing imports and full physics suffixes and add the corresponding `installed_ashtrays_<side>.obj`, 19,824 triangles per side, with distinct `rh_as_` material aliases. No scene/material changes or full-map regeneration.

`Tools/railhead_ashtray.py` freezes the approved geometry and UVs before translating the copies. `railhead_dress_detail.ashtray_pillar` delegates to it; its old render code is removed. All four original thin collision boxes and yellow floor markings remain. Actual offline play checked all four saved models with a player and no error models; all four images were visually inspected, then the prior editor scene/play/dirty state restored.

The obsolete, unreferenced private `east_without_ashtray` preview sources, metadata and compiled model were removed through the editor after a reference audit, with archived copies outside Assets. Receipts/backups: `output/railhead/ashtray-v1/installed.json`, `install-before/`, `obsolete-preview-cleanup.json`, `retired-preview/` and `runtime-installed/`. Recheck with `verify_installed.py`; `--capture-only` skips compilation when the editor watcher has already compiled both public models. Do not rerun historical build/review commands against the installed bases.

## Historical approved prototype

Island-platform smoking area at plan (601, -891, 0). The new model retains the original 8-inch body diameter, 40-inch height, 11.2-inch foot and yellow band. It adds a rolled foot/lip, four anchor screws, a curved removable service panel with hinges and cylinder lock, eight real side openings, an internal collector and a removable top tray with 37 physical perforations. Existing Railhead brushed stainless, dark-steel, black and yellow materials only; no texture edits, lighting changes or glow.

9,912 render triangles replace 294 in a private copy of the live `cable-drum-v1/east_without_drum.obj`. Unrelated faces and vertex/UV/normal records, the public dressing ModelDoc's other imports and entire physics suffix, original collider, yellow floor markings and saved scene stay unchanged. Other ash columns remain unchanged. The proposal is staged for approval. No performance benchmark.

From the canonical checkout, waiting for each command to finish:

```powershell
rtk python Sources/Railhead/ashtray-v1/build.py
rtk python Sources/Railhead/ashtray-v1/setup.py
rtk python Sources/Railhead/ashtray-v1/review.py
rtk python Sources/Railhead/ashtray-v1/verify.py
```

Build stages outside Assets; native editor import and incremental compilation register only private preview files. Captures run in actual offline Railhead play with a player, copied gameplay camera effects, fixed matched exposure/cameras and 180 ordinary streaming frames per view. Full-column and top-detail views are captured before/after. No capture lights or forced texture residency. Only the task's own play session is stopped, then the prior scene/play/dirty state restored.

Evidence after successful verification: `output/railhead/ashtray-v1/ashtray-comparison.png`, `head-comparison.png`, `validation.json`, `runtime-review/checked.json` and `play-state-restored.json`. Inspect both views before claiming the in-game review passed. No whole-map regeneration.

The initial engine check exposed the old `rw_steel` finish as green paint with rust spots. The final candidate uses the existing `rw_stainless` finish at its authored 24-inch scale, with continuous cylindrical UVs on its shell and access panel. Public material/texture files remain untouched. `--candidate-only` rebuilds only the proposal geometry/manifest after checking the live base hash; use a full build if that base changes.
