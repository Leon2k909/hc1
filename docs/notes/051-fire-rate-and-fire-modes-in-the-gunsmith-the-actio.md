## Fire rate and fire modes in the gunsmith (the Action and Trigger slots)
- The user (2026-09-30): a suppressor shouldn't change a gun's rate unless a real one would, every part should do what
  the real one does, and there could be a category for changing fire rates "however you would do that in real life".
- What really sets a cyclic rate, and what the game models:
  - A suppressor's back-pressure speeds up gas-operated and blowback actions (`Shootable.SuppressorFireRateScale`):
    about 10% on direct-impingement ARs and AKs (the M4A1 template the rifles copy in `kastov_prefabs.py`), about 5% on
    blowback and roller-delayed SMGs (the MP5's, which the SMGs borrow). It's 1 where a real one wouldn't change the
    rate: the semi-only M18 and Vepr-12 (the trigger finger sets their pace), the FAL, whose adjustable regulator is set
    for the can (FN's procedure), and the MCX Virtus and the HK416 A5, whose two-position gas valves have a setting for
    one, and the MCX-SPEAR, whose adjustable valve has a suppressed setting. The SCAR-H and
    the old pistols and bolt guns have none.
  - The gas system's length: the AR barrels already did it (`GunsmithAttachmentEffects.FireRate`).
  - The buffer's mass, and a gas regulator: the Action slot (`GunsmithPartType.Action`, `GunsmithPart.FireRateScale`,
    `GunsmithPart.SuppressedGasSetting`).
  - A trigger can't change the cyclic rate. A fire control group changes the modes the selector has: the Trigger slot
    (`GunsmithPartType.Trigger`, `GunsmithPart.FireModes`).
- Action and Trigger are internal slots like Ammunition (`AttachmentUnlocks.IsInternalSlot`): no mesh, no socket.
  `GunsmithLoadoutManager.ApplyAttachments` makes their runtime attachment points, and `AttachmentUnlocks.GetSlots` lists
  a slot only for a weapon with a part for it. Their parts carry an explicit `RequiredLevel`, so the unlock ladder
  leaves them out.
- The parts:
  - M4A1 buffers (`Assets/gunsmith/m4a1/action/`), against its factory H2 (4.6 oz) at 800 rpm: Carbine Buffer (3.0 oz,
    x1.095, ~876 rpm, level 12), H Buffer (3.8 oz, x1.045, ~836, level 6), H3 Buffer (5.4 oz, x0.959, ~767, level 18).
    The cycle time goes as (bolt carrier 11.5 oz + buffer) to the power 0.87, fitted to a measured pair: 5.6 oz to
    7.5 oz buffers took an AR from 971 to 886 rpm.
  - AUG A3 Suppressed Gas Regulator (`Assets/gunsmith/aug/action/`, level 12): with a suppressor it keeps the rate at
    715 instead of 10% higher, and without one it changes nothing (the regulator's normal setting).
    `Shootable.SuppressorRateScale` reads it.
  - M4 Trigger Group (`Assets/gunsmith/m4a1/trigger/`, level 10): the real M4's semi and three-round burst in place of
    the M4A1's automatic. The M4A1's `BurstEndDelay` is 0 like the M16A4's, so the next pull follows at the cyclic rate.
  - M16A3 Trigger Group (`Assets/gunsmith/m16/trigger/`, level 14): semi and automatic in place of the M16A4's burst.
- Fire modes: `Equipment.TriggerFireModes` (owner-side, set in `RefreshAmmunitionLoadout`) overrides
  `Shootable.SupportedFireModes`, and everything that lists modes reads `Shootable.FireModes` (the selector, the HUD's
  ammo counter, the gunsmith's figures through `GunsmithStats.BuildFireModes`). When a trigger group takes the mode
  you're on away, `KeepFireModeFitted` switches automatic to burst (or back), else the first mode.
- The DETAILS and COMPARE rate follows the fitted buffer and regulator, as the gun does.
- Made offline (2026-09-30). The open editor compiled the six `.gnsmth` files as they were written, with every new
  field in the compiled data, but nobody has seen them in the gunsmith: if the Action or Trigger slot is missing,
  `recompile_asset` them after the code has hotloaded. None of it has been checked in-game.

