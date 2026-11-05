# ReefHall filter-room wall light — installed

The approved fixture at (760, 1100), bottom Z 110, is installed. Exactly twelve old render triangles were removed from the active filter OBJ, preserving unrelated records/faces. The public filter ModelDoc adds `installed_wall_light.obj` with distinct `rh_wl_` material aliases and retains its other imports and complete physics suffix. `Tools/reefhall_wall_light.py` freezes the approved geometry/UVs; the targeted `reefhall_map.sconce` hook preserves the original point-light append and leaves other fixtures unchanged.

The saved model passed actual offline ReefHall play with a player and no error models, and its screenshot was visually inspected. Prior scene/play/dirty state restored. The independently installed bronze lobby planters were detected, audited and preserved; `concurrent-changes.json` records those input changes, and generator reversal verifies that this installation changes only the selected sconce recipe. The obsolete unreferenced `filter_without_light` preview sources, metadata/cache were archived outside Assets and removed through the editor after a reference audit.

Receipts/backups/captures: `output/reefhall/wall-light-v1/installed.json`, `install-before/`, `runtime-installed/`, `obsolete-preview-cleanup.json`, `retired-preview/`. Use `verify_installed.py` after installation; historical build/review commands below must not be rerun against the installed base.

## Historical approved proposal

Wall luminaire at plan (760, 1100), bottom Z 110, facing north. The old 7 × 16 × 3 glowing box becomes a cast backplate, sealed chamfered body, curved opal diffuser, gasket seams, stainless trim, end shoes, recessed screws and two small diffuser guards. 4,300 triangles replace 12. The diffuser uses ReefHall's existing soft `rh_frosted_lit` finish rather than the old high-output LED face. Other finishes are existing ReefHall materials.

The existing scene point light, its position/intensity/radius, all other lamps, saved scene and material/texture files stay unchanged. A private base removes only the matching twelve old faces and preserves all unrelated vertex/UV/normal records and faces, installed circulation-pump import and the full public ModelDoc physics suffix. The old fixture has no collision; the candidate adds none. No whole-map regeneration or performance claim. Public installation awaits review and approval.

From the canonical checkout, waiting for each command to finish:

```powershell
rtk python Sources/ReefHall/wall-light-v1/build.py
rtk python Sources/ReefHall/wall-light-v1/setup.py
rtk python Sources/ReefHall/wall-light-v1/review.py
rtk python Sources/ReefHall/wall-light-v1/verify.py
```

Build stages outside Assets. Native editor import/compilation handles private preview resources. Actual offline play captures use a player, copied gameplay effects, matched camera/exposure and 180 ordinary streaming frames per variant, with no added lights or forced residency. The task stops only its own play session and restores the prior scene/play/dirty state. Evidence after successful checks: `output/reefhall/wall-light-v1/light-comparison.png`, `validation.json`, `runtime-review/checked.json` and `play-state-restored.json`. Inspect the actual final images before claiming the in-game check passed.
