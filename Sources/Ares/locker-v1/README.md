# Ares wing storage lockers — all fourteen installed

The approved design now replaces both seven-locker banks. The installed model has identifiers 01–14, reuses the approved light door finish, and replaces exactly 336 old render triangles with 75,074 triangles. `Tools/ares_lockers.py` preserves the approved prototype geometry and UVs; `Tools/ares_map.py` uses it at all fourteen placements. The active `pressure-doors-v2/hall_base.obj` retains every unrelated face and its existing vertex/UV/normal records. The hall's complete physics suffix, bank collision and scene remain unchanged.

`output/ares/locker-v1/installed.json` records the installed source hashes, geometry checks and actual offline play check with a player and no error models. Both full banks were captured from the saved public model under `runtime-installed/`, then the prior editor scene/play state was restored. Recheck with `rtk python Sources/Ares/locker-v1/verify_installed.py`. The original build/review commands below describe the historical prototype and should not be rerun against the installed base.

## Historical approved prototype

The fourth east-wing locker, centred at plan (1278, -709, 0), faces north. It retains the original 25 × 22 × 84 enclosure and uses existing Ares steel, gunmetal, brass and off-white finishes. The door uses the lighter existing finish so its shape reads in the dark wing without extra lights. The 5,364-triangle proposal adds a folded enclosure, toe plinth, gasket and formed recessed door, two physical ventilation banks, three hinged barrels/leaves, a recessed pull handle, key cylinder, fasteners and an unlit, correctly facing 04 identifier.

Only the two old box meshes (24 triangles) are removed from a private copy of the currently installed `pressure-doors-v2/hall_base.obj`. Every other face and vertex/UV/normal record is preserved, as are the public hall ModelDoc's other imports and entire physics suffix. The saved scene, lighting, materials and other lockers are unchanged. No full Ares regeneration.

From `C:\sbox-projects\hc1\forked-shooter-main`:

```powershell
rtk python Sources/Ares/locker-v1/build.py
rtk python Sources/Ares/locker-v1/setup.py
rtk python Sources/Ares/locker-v1/review.py
rtk python Sources/Ares/locker-v1/verify.py
```

Build stages outside Assets; import and incremental compilation use the connected editor. Captures run in the actual offline map with a player, copied gameplay camera effects, matching camera/light/exposure and normal texture streaming. The task stops its own play session and restores the prior editor scene. The proposal awaits approval before public installation. No performance benchmark.

Artifacts: `output/ares/locker-v1/locker-comparison.png`, `validation.json`, `play-state-restored.json` and the full screenshots under `runtime-review/`.
