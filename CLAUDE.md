# HC1 (Razed) — notes for Claude sessions

## Iron sights: do not change the M4's AimOffset
- `Assets/Weapons/M4A1/weapon_m4a1.prefab` → `ManualOffset.AimOffset` must stay `0,0,0`.
  It was repeatedly "fixed" to `-4,0,-0.5` (believed to be upstream's value); that pushes the rear sight into the
  camera and breaks ADS. `0,0,0` was verified in-game (front post centred in the rear aperture).
- `Code/Weapons/IronSightCalibration.cs` holds the verified values and logs an error at runtime if a prefab drifts.
  Only recalibrate after checking in-game, and update that table at the same time.
- Magnified optics don't use this value: they use the optic's own `OpticAimOffset` (`.gnsmth` files).

## Testing in-game without input
Dev console commands (`Code/GameLoop/DevCommands.cs`): `dev_quickplay`, `dev_give <weapon>`, `dev_force_aim 1`,
`dev_no_damage 1`, `dev_reload`, `dev_aim_offset x y z` (live, not saved), `dev_aim_info`.
