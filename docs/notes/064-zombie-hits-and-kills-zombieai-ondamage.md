## Zombie hits and kills (`ZombieAI.OnDamage`)
- Zombies have no HealthComponent, so hitting one raises none of the events a bot hit does. `OnDamage` (host only) sends
  the shooter's hitmarker itself (`ShowHitmarker` → `Crosshair.ShowHit`, on whoever is viewing the shooter).
- A kill goes in the score feed right of centre, like a bot kill's "Killed a player": `ZombiesPlayerEconomy.AddPoints`
  with a reason ("Killed a zombie") also sends the owner an `OnScoreAddedEvent`. The amount is what the kill paid: 60,
  100 for a headshot, doubled under Point Boost. Hits, the Clean Sweep and revives pass no reason, so they stay out of it.
- Zombie kills still raise no `KillEvent`, so they stay out of the kill feed, medals, daily challenges and stats.
- Checked in-game 2026-09-26 with `dev_zombie_hit`: the hitmarker on a hit, and "Killed a zombie 100" for a headshot kill.

