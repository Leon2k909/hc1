## Weapon tuning is off (`WeaponTuningManager`, `WeaponTuningPanel`)
- The WEAPON TUNING sliders (damage, fire rate, reload, ADS move, recoil and magazine size, -10 to +10 per weapon,
  kept in `hc1.tune.<weapon>.<stat>` cookies) were turned off on 2026-09-30. The user may bring them back, so nothing
  was deleted.
- What's commented out, each marked "Put back with tuning":
  - the gunsmith's TUNING card and its modal (`GunsmithPanel.razor`);
  - the gameplay reads: `Shootable.GetEffectiveDamage` / `GetEffectiveFireRate` (and `TuningId`),
    `ShootRecoil.GetRecoilScale`, `Reloadable.DurationMultiplier`, `Aimable.GetAdsMoveScale` and
    `WeaponAmmo.GetEffectiveMaxAmmo`;
  - `GunsmithStats.Compute`, which now works every build out untuned.
- Players' saved tunings stay in their cookies but do nothing. Turning tuning back on brings them back as they were.
- `ShowTuning`, `ToggleTuning`, `CloseTuning` and `IsTuned` are still in GunsmithPanel, with the Escape and back
  chains that close the modal. The styles and the `Tr` keys are still there too.
- COMPARE's captions still say "no tuning" / "with tuning". They weren't changed, because that needs new keys in all
  ten tables.

