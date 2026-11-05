# Railhead brick pallet — installed

The user-approved east-yard pallet is installed in the public east dressing model. Exactly 266 old render triangles were removed from `cable-drum-v1/east_without_drum.obj`; all unrelated records/faces remain. The public ModelDoc adds the new import using distinct `rh_bp_` material aliases and retains all other imports and its entire physics suffix. `Tools/railhead_brick_pallet.py` freezes the approved geometry/UVs, called only for the east placement by `Tools/railhead_map.py`, preserving the original collider. The west pallet is unchanged.

The saved public model passed actual offline Railhead play with one player and no error models. The installed screenshot was visually inspected, and the prior editor state restored. Receipts/backups: `output/railhead/brick-pallet-v1/installed.json`, `install-before/`, `runtime-installed/`. Recheck using `rtk python Sources/Railhead/brick-pallet-v1/verify_installed.py`. The original review commands below are historical and should not be rerun against the installed base.

## Historical approved proposal

East goods-yard stack at plan (1884, -1580, 0.3), along n. The original 39.4 × 47.2 footprint and cover height are retained. The proposal models 520 separate bevelled bricks in alternating courses, forty recessed top frogs, seven timber deck boards, cross bearers, nine bearing blocks, three bottom runners, nail heads and four thin packing straps with buckles. It reuses Railhead's existing brick, wood, black and dark-steel materials. Brick UVs sample interior patches to keep photographed mortar out of the individual bricks; wood follows the pallet boards.

24,992 render triangles replace 266 old triangles in a private copy of the live `cable-drum-v1/east_without_drum.obj`. Unrelated vertex/UV/normal records, faces, approved reel/barrier/extinguisher imports, the full east ModelDoc physics suffix and the saved scene stay unchanged. No new lights or texture edits. The public map is unchanged until approval. No performance benchmark.

From the canonical checkout:

```powershell
rtk python Sources/Railhead/brick-pallet-v1/build.py
rtk python Sources/Railhead/brick-pallet-v1/setup.py
rtk python Sources/Railhead/brick-pallet-v1/review.py
rtk python Sources/Railhead/brick-pallet-v1/verify.py
```

Wait for each command to finish. Build stages outside Assets. The editor imports and incrementally compiles the private preview; capture starts only from a stopped, clean editor. Actual offline play uses a player, copied gameplay camera effects, matched camera/exposure and 180 ordinary streaming frames per image. Only its own play session is stopped, then the previous editor scene is restored.

Evidence: `output/railhead/brick-pallet-v1/pallet-comparison.png`, `validation.json`, `runtime-review/checked.json`, `play-state-restored.json`. Those receipts must exist before claiming the in-game review passed.
