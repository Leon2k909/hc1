# ReefHall circulation pump — installed

The approved pump at (-380, 1610) is installed in the public filter-room model. Exactly 220 old render triangles were removed from `reefhall_filter.obj`, preserving unrelated mesh records/faces. `reefhall_filter.vmdl` adds `installed_circulation_pump.obj` with distinct `rh_cp_` material aliases and keeps its complete physics suffix and other imports. `Tools/reefhall_circulation_pump.py` freezes the approved geometry and bakes its projected/grain UVs before joining the room; the targeted hook in `Tools/reefhall_map.py` retains both original collision boxes. Other two pumps are unchanged.

The saved public model passed actual offline ReefHall play with a player and no error models; both installed motor and connection views were visually inspected. The prior editor scene/play/dirty state was restored. Receipts, source backups and captures: `output/reefhall/circulation-pump-v1/installed.json`, `install-before/`, `runtime-installed/`. Use `rtk python Sources/ReefHall/circulation-pump-v1/verify_installed.py` to recheck. The original review commands below are historical and should not be rerun against the installed base.

## Historical approved proposal

The filter-room pump at plan (-380, 1610), yaw 0. The proposal separates the motor, coupling and cast pump housing; adds longitudinal cooling fins, a rear fan grille, stepped end shields, bolted flanges, skid rails/feet, a gasketed terminal box with cable, a front identification plate and a mechanical pressure gauge. All finishes reuse existing ReefHall materials. The gauge uses the existing unlit white finish for legibility. No lights or material/texture files are changed.

16,196 render triangles replace the original 220 in a private copy of `reefhall_filter.obj`. Every unrelated face and vertex/UV/normal record, the public ModelDoc's other imports and full physics suffix, original collision, saved scene and other two pumps remain unchanged. The public map is unchanged pending approval. No performance benchmark.

From the canonical checkout, waiting for each command to finish:

```powershell
rtk python Sources/ReefHall/circulation-pump-v1/build.py
rtk python Sources/ReefHall/circulation-pump-v1/setup.py
rtk python Sources/ReefHall/circulation-pump-v1/review.py
rtk python Sources/ReefHall/circulation-pump-v1/verify.py
```

Build stages outside Assets; import and incremental compilation use the connected editor. Captures run in actual offline ReefHall play with a player and copied gameplay effects. The motor and connection views use matching cameras, locked exposure and 180 ordinary texture-streaming frames per variant, with no added light or forced texture residency. Only this task's play session is stopped and the prior editor scene/play/dirty state restored.

Evidence: `output/reefhall/circulation-pump-v1/pump-comparison.png`, `connections-comparison.png`, `validation.json`, `runtime-review/checked.json`, `play-state-restored.json`. These receipts must exist and images be visually inspected before claiming the in-game check passed. The build passes floating-point lathe profiles to the shared helper; do not alter the helper for this proposal.
