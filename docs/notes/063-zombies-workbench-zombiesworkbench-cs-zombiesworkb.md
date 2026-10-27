## Zombies workbench (`ZombiesWorkbench.cs`, `ZombiesWorkbenchPanel`)
- One `ZombiesBuyKind.Workbench` station per match (`PlaceBuyStations`). Its model is the user's own Blender workbench
  (`C:/Users/leon2/Documents/Workbench/`, the game-ready copy in `GameReady/Workbench_GameReady.blend`), which the user
  saw had been left out for a stand-in built from dev boxes (2026-10-01).
  - `Tools/zombies_workbench.py` (headless Blender) bakes its procedural materials into three texture sets (the bench,
    the props on it, the pegboard) and writes `Assets/models/zombies/workbench/`: the OBJ, the vmdl, the PNGs and the
    vmats. Its docstring has the axes and the bakes.
  - It bakes a dozen objects at a time onto a joined copy of them (`CHUNK`), then grows each UV island 16 texels
    (`grow_islands`). One bake for all 255 props took minutes a map and left some objects unbaked; Blender's own margin
    can't be used, since one chunk's would paint over the islands of those baked before it.
  - The model faces +X with its back at x -20: 72 wide, 86 tall and 40 deep, with wood shavings 13 further out on the
    floor. The station's BoxCollider is 40 x 72 x 86 (`StationSize`, `CreateStation`), and the vmdl has no collision.
  - `CreateBenchModel` loads `workbench.vmdl`, and builds the old stand-in (`CreateStandInBench`) if it hasn't compiled.
  - A full run (2048 textures, 8 samples, AO 128) took 40 minutes on the RTX 5070; `--size 512 --samples 2
    --ao-samples 16 --out <dir>` takes 25 and is enough to check the look. A render (Cycles, the OBJ with its textures)
    showed every prop in its colours on 2026-10-01: the painted vise, the toolbox, the clamps and the tools' handles.
    About 2% of the bench's texels baked facing away (hidden faces, black in the AO), which didn't show.
  - Not yet seen in the engine: the editor hadn't compiled the vmdl when it was written, and nothing in a match has
    loaded it yet.
- Use opens its menu on the player's own machine (the panel's Tick checks `PlayerPawn.Hovered`); the host's `OnUse` does
  nothing for it. E, Escape (one step back at a time, from MainHUD's chain), walking more than `WorkbenchRange` away,
  going down or dying closes it. It's in `IsInteractiveMouseUiOpen` / `GetCombatMouseBlockReason` (cursor) and
  WeaponInputAction's `menuOpen` (no shooting).
- Attachments are free: the player's gunsmith build for the active class, from their unlocked parts only (locked ones are
  listed with their level). The menu saves each pick (`SetAttachment`) and refits the viewmodel, world model and
  holstered model at once (`RefitAttachments`).
- Armour, ammo and grenades cost points, paid on the host by `ZombiesBuyStation.Buy` ([Rpc.Host], checked again there):
  - Plates of 50, up to 3 (150), at 5 points per point of armour (250 a plate). Plates take damage point for point before
    health, except falls (`ZombiesPlayerState.AbsorbWithArmor`). Zombies spawns with no armour or helmet
    (`zombies.prefab` DefaultEquipment), so plates are the only armour.
  - Spare ammo: a primary's full load is 500, a secondary's 250, charged for the share that's missing. The owner adds the
    rounds (`WeaponAmmo.ReceiveReserve`), since it owns the synced count.
  - An HE grenade (250) into an empty Lethal slot. `Explosion.AtPoint` damages zombies too (`DamageReceiver`: things
    with no HealthComponent that are `IDamageable`), and a grenade kill pays the thrower's points.
- Not yet checked in-game.

