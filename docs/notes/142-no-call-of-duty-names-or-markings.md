## No Call of Duty names or markings
- The user's rule (2026-09-26): nothing players see may come from Call of Duty, so the game isn't a CoD clone. That
  means no CoD names for weapons, attachments, perks, modes, streaks or camos, and no CoD writing, numbers, logos or
  QR codes on textures. Weapons go by their real-world names (AK-47, AKS-74U, PP-19-01 Vityaz, RPK, PP-19 Bizon,
  AK-105, Vepr-12, M16A4, FN P90, MP7A1, Steyr AUG A3, Uzi, FN FAL, SIG Sauer M18, SIG Sauer MCX Virtus, L85A2,
  HK416 A5, AK-12, AK-15, AK-74M, SIG Sauer MCX-SPEAR, M16A2, RPK-16) and
  attachments by plain descriptions ("Vented Suppressor").
- Renamed:
  - Zombies perks: Juggernog → Iron Tonic, Speed Cola → Bolt Soda, Double Tap → Hot Shot, Quick Revive → Second Wind,
    Stamin-Up → Fleet Foot (`ZombiesPerk`, `ZombiesBuyStation.PerkName`). Their art (`Assets/Perks/<perk>_*`,
    `ui/zombies/perks/<perk>.png`) was redrawn with the new names.
  - Zombies power-ups: Max Ammo → Resupply, Insta-Kill → One-Hit Kills, Double Points → Point Boost, Nuke → Clean
    Sweep. The Mystery Box is the Weapon Crate.
  - Multiplayer perks: Flak Jacket → Blast Vest, Ghost → Off the Grid, Lightweight → Light Load, Ninja → Soft Step,
    Sleight of Hand → Deft Hands.
  - Modes: Hardpoint → Hot Zone, Gunfight → 1v1 / 2v2 Skirmish. Scorestreaks are Streak Rewards (Kills or Score). The
    Dark Matter camo is Violet Storm.
- Stored names stay, because scenes, prefabs, cookies and saved loadouts hold them: the mode idents `hardpoint`,
  `gunfight_1v1` and `gunfight_2v2`, the `Hardpoint*` and `Scorestreak*` classes, `UseScorestreaks`, the `Scorestreak`
  input action (titled "Streak Reward"), the `.perk` files (perks are saved and checked by ResourceName, `HasPerk`),
  the `weapons/kastov/...` paths and the `darkmatter` camo files. Players only ever see the new names.
- Textures: `Tools/texture_markings/` (its README has the rules) takes the writing, numbers, logos, QR codes and labels
  off the ripped guns' and parts' textures. `specs/*.json` lists every region it covers, and `cleaned.json` each map's
  pixel hash before and after, so `clean.py --check` finds a map that's back to the rip's. The converters clean
  again after a re-rip (`markings.after_rip()`). The MWII optics' decal sheets are hidden (`hidden.vmat`) and their
  textures deleted. A new port goes through the README's steps before it ships: `after_rip()` leaves a material with
  no spec as ripped, without a warning. The M16A4 has `specs/m16.json`, the Vepr-12 `specs/vepr12.json`, the P90
  `specs/p90.json`, the MP7A1 `specs/mp7.json`, the AUG `specs/aug.json`, the Uzi `specs/uzi.json`, the FAL
  `specs/fal.json`, the M18 `specs/m18.json`, the MCX `specs/mcx.json`, the L85A2 `specs/l85a2.json`, the HK416
  `specs/hk416.json` (Ready or Not's made-up maker, HaKa, and HK's and Magpul's markings) and the AK-12
  `specs/ak12.json` (Kalashnikov's stamps and the sights' and magazine's numbers), the AK-15 `specs/ak15.json`, and the AK-74M
  `specs/ak74m.json` (Kalashnikov's stamps and sight numbers, and Zenit's markings on its B-13 mount), and the MCX-SPEAR
  `specs/spear.json` (SIG's, Lancer's and Magpul's markings), the M16A2 `specs/m16a2.json` (Colt's markings), and the RPK-16 `specs/rpk16.json` (Kalashnikov's stamps and the
  rear sight's numbers).
- Still CoD's: the ported guns' and parts' models, animations and sounds, and the Zombies numbers (the crate's 950, the
  perk prices, the points for kills). Only the names and markings have changed. The sounds of every ported gun but the
  Kastov-74u have been voiced towards the real thing: shots, suppressed shots and reloads (see RPK and The ported
  guns' sounds).

