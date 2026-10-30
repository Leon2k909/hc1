## Vepr-12 (MWII's "KV Broadside", mg_iw9_vecho, addon 3499492742)
- The real Molot Vepr-12 (category Shotgun) under its real name: a semi-automatic 12-gauge on the RPK's receiver, here
  the short VPO-205-03 (its barrel measures ~305 mm in the model). Its figures are in `kastov_prefabs.gameplay_vepr12`:
  - 2 3/4" 00 buckshot: nine 8.4 mm, 3.49 g pellets at 365 m/s (Ballistics.cs's sphere table, BC 0.071). The sights sit
    48.7 mm over the bore, zeroed at 25 m like the other buckshot guns.
  - Semi only, capped at 450 rpm: the action's cycle rate. That's the figure quoted for full-auto Saiga-12
    conversions, not checked against a source.
  - The pattern is a cylinder bore's ~49 cm at 25 yd: BulletSpread 0.026, because Shootable's spread puts nine pellets
    0.82 x BulletSpread apart on average.
  - Falloff follows the pellets' kinetic energy along their path (`BUCKSHOT_FALLOFF`, from the sphere model): 68% at
    25 m, 49% at 50 m, 29% at 100 m and 11% at 200 m, where they stop (MaxRange).
  - The damage per pellet (8) and the shot effects are the Spaghelli's (`Gameplay.borrow`).
  - It weighs 4.2 kg, 4.8 kg loaded. By the RPK's scaling against the AKM's 3.75 kg that gives WeightSlowdown 0.01 and
    0.27 s ADS. The recoil scale (3,7.6) is the M4's (2,5) scaled by free recoil (~2.8 against 1.86 m/s).
- Materials and sounds are from `Tools/vepr12_assets.py`: its own shot (-5 dB, to the Kastovs' level) and reload foley
  at the viewmodel QC's event frames. It has no suppressed shot.
- It was ported with CoD's markings still on: "Verdansk Arms Factory" and "Made in Kastovia" on the receiver, "First
  Signal Solutions" and FSS on the drum, a maker's emblem on the 12-round mag and "CORVUS DEF" on the shells.
  `Tools/texture_markings/specs/vepr12.json` takes them off (the drum's ring lettering and the headstamps as `ring`
  regions), checked in before/after renders on 2026-09-28.
- Parts (`PARTS_VEPR12`, `Assets/gunsmith/vepr12/`):
  - The AK-platform stocks and grips, with the 74u's materials. Stock recoil is relative to its factory strut stock.
  - Its own 12-round mag and 25-round drum, each with its own reloads (`reload_variants` `_xmag`, `_drummag`). Reload
    times are when the left hand is back on the grip (the clips' grip-pose events): 2.3/2.87 s for the factory 8, then
    2.67/3.27 and 3.17/4.2.
  - Left out: CoD's barrels, bolts and conversions, and the grips and launcher that move the left hand.
  - `GunsmithPart` has no weight or ADS time, so the bigger mags only slow the reloads. CoD also slows ADS with them
    (x1/0.9 and x1/0.75).
- Slots: Optic on the dust cover's rail, Underbarrel on the handguard's bottom rail and Laser on its right-side rail
  (the `laser_rail` bodygroup, shown only under a laser). There's no Muzzle slot, because the M4's devices are 5.56
  ones, so the brake always shows.
- Its `OpticAimCorrection` `3.396,0,-1.26` is derived with the Bizon's formula, NOT checked in-game. The iron sights
  (ads_in's last frame, post centred in the notch) were checked in a render, not in-game.
- No `GripFit`. The idle left hand has 303 vertices inside the handguard, but they're at most 0.23" deep (mean 0.06"),
  which is about where the RPK's fit left it (85, 0.21"). None of it shows from the camera at the hip or aiming. The
  best fit found (shift `0,0.15,-0.25`, fingers 0.35, thumb 0.3) only got to 86 at 0.19", and it put a fingertip
  beside the handguard in the ADS view.
- The drum clips the left forearm (36 vertices, ~0.87" deep): its lua sets `grip_bartac_offset`, which isn't ported.
  The clash is below the view in idle, ADS, walk, sprint, draw and fire.
- Bots don't use it: shotguns aren't in their pool (`LightweightCombatBot.CategoryShare`). None of it has been checked
  in-game yet.

