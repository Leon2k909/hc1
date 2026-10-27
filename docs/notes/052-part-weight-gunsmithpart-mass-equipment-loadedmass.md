## Part weight (`GunsmithPart.Mass`, `Equipment.LoadedMass`, `Tools/part_masses.py`)
- The user asked whether the parts have real-life downsides and wanted the missing ones in (2026-09-30). The main gap
  was weight: a drum, a scope or a can weighed nothing.
- Downsides that were already modelled:
  - tracers give the shooter away;
  - lasers show on the world model;
  - brakes are louder, heard further and flash more, and compensators flash more;
  - suppressors change the rate as the action would;
  - bigger magazines reload with their own, slower clips;
  - stocks change the recoil by how they brace.
- Left out: a magnified optic's eye box, reliability, heat mirage off the barrel, a can's shift of the point of impact,
  and gas in the face.
- `GunsmithPart.Mass` is what a part adds against the factory part it replaces, in kg, so it can be negative (the
  RPK's AKM 30 against its 75-round drum, -1.304). Magazines count loaded. `Equipment.LoadedMass` is the gun's own
  weight with a loaded factory magazine, from the makers' figures (0 = unknown, read as 3.75 kg).
- `GunsmithAttachmentEffects.ApplyMass` works out three things from the gun plus its parts (at least half the gun):
  - Recoil: times gun / total, since free recoil goes as one over the weight.
  - Aiming in: times the square root of (total + 4) / (gun + 4), where the 4 kg is the arms swung up with it.
    `ViewModel` stretches `AimTime` by it, and the Facepunch-graph guns get `speed_ironsights` 1 / that.
  - Moving: 1% slower per kg over 3.75 kg (`AttachmentWeightSlowdown`, added to the gun's own `WeightSlowdown` in
    `PlayerPawn.GetWishSpeed`). A gun under 3.75 kg doesn't get faster than the rifles.
  - Examples: the M4 with a 60-round mag (+0.61) kicks 15% less and aims in 4% slower. The Vepr-12's drum (+1.63)
    kicks 25% less, aims in 9% slower and moves 1.6% slower.
  - The owner works it out in `RefreshAmmunitionLoadout`, which runs on every shot. A magazine doesn't get lighter as
    it empties.
- The gunsmith shows it:
  - each part's weight change under its description (`GunsmithAttachmentBrowser`, "+0.61 KG");
  - WEIGHT in DETAILS and COMPARE (`GunsmithStats.Mass`);
  - the recoil and ADS bars and figures include it.
- `python Tools/part_masses.py` writes every part's Mass (tables with sources, by gun and file) and every gun's
  LoadedMass (`GUN_KG`). `--check` lists what it would change and any part without a figure. `kastov_prefabs.py` and
  `m16_gunsmith.py` write the same figures when they regenerate parts and prefabs. The Kastov-74u's hand-tuned prefab
  got the new field only.
  - A gun's own choices (`OWN_CHOICES`) are looked up as `"<group>/<choice>"` first, then by the plain choice name,
    so a gun with a factory choice in several groups keys each one by its group (the AK-74M's `stock/factory` and
    `pistol_grip/factory`).
- Made offline, and compiled with dotnet. The new `.gnsmth` and prefab fields only load into files compiled after the
  code has them, so `recompile_asset` the parts and weapon prefabs after the hotload. None of it has been checked
  in-game.

