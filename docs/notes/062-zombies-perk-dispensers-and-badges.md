## Zombies perk dispensers and badges
- Perk machines are turned off: the user will revisit the perk system later. Their placement in
  `ZombiesRoundSystem.PlaceBuyStations` is commented out ("Put back with perks"); everything else (the perk code, the
  dispenser art and the HUD badges below) is kept, unused. Don't turn them back on unless asked.
- One shared dispenser model (`Assets/Perks/build_dispenser.py`, run with Blender) is dressed per perk in
  `ZombiesRoundSystem.CreatePerkDispenser`: the grey enamel is tinted the perk's paint colour, the poster card and lit
  name sign get `Perks/<art>_poster.vmat` / `_sign.vmat` (`ZombiesBuyStation.PerkArt`), the lamps glow `PerkColor`.
- `Assets/Perks/build_perk_art.py` makes the posters, signs, grey enamel and HUD badges (`ui/zombies/perks/<art>.png`)
  from the square `<art>_label.png` illustrations. The poster window is 29.6 x 42.6, so the square art gets name and
  effect plates instead of being stretched. `preview_dispenser.py` renders all five; keep its colours matching the code.

