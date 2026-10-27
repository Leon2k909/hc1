## Spawn camping: bots' spawns flip (`LightweightBotManager.TryGetUncampedSpawn`)
- The user (2026-10-12): "i can spawn camp bots on lowtide". Bots came in at their own 12 team spawns whatever stood
  over them, so a player in their square shot each one as it appeared.
- Where a bot spawns at its team's spawns (the scripted maps: `MapSpawnSettings` with navmesh spawns off), each one is
  scored for danger (`SpawnDanger`) against every living enemy, player or bot:
  - 2-4 for an enemy within 1200 (~30 m, `CampedRadius`), seen or not, more the closer;
  - 1 for one that can see a body standing there (a ray to its chest or head) from within 3000 (~76 m,
    `WatchedRange`), 2 if they're facing within 60 degrees of it.
- A bot takes one of up to five safe spawns (danger 0), best by `GetSpawnScore` first. When none is safe, the team's
  spawn flips, as in CoD (`TryGetFlipSpawn`):
  - The pool is every spawn on the map that isn't switched off for another reason: this mode's (the enemy team's
    too), plus those a `GameModeObject` left off for other modes (`OffForAnotherMode`). So on Lowtide, Belltower,
    Railhead, Boxyard, Cerro Blanco and Reef Hall, the 16-36 deathmatch spawns round the map. Innocent Hotel has no
    deathmatch spawns, so there it's the other wing's team spawns.
  - Not Retakes' spawns (the `retakes` tag), nor one a map switched off itself. It also has to be free, at least
    `MinSpawnDistanceFromTeammates` from a teammate, and on the main navmesh.
  - Maps with navmesh spawns on (Flatgrass, Refinery, Edinburgh, Depot, Motel, Shipment) spawn bots round the players
    first (`TryGetNavSpawn`), so this only runs there when that finds nothing.
  - Scored by the nearest enemy's distance (up to 4000), a little for a teammate within 1500, and -3000 within 1000 of
    the enemy team's spawns. The best 24 get the danger check, which stops at three safe ones.
  - It takes a random one of the safe ones. With none, it takes the least dangerous, but only if that's less camped
    than the team's own best; otherwise the team's least camped spawn.
- Free-for-all already picks from every spawn, so it only gets the danger ranking. No flip in round modes (Defuse,
  Retakes, 1v1 and 2v2 Skirmish: `IsRoundMode`), and nothing changes with no enemy alive.
- Players' spawns (`TeamSpawnAssigner`) are unchanged. They already score enemies' distance and sight, but only
  within their own team's spawns.
- Compiled offline with dotnet (2026-10-12), not yet checked in a match. To check: a TDM on Lowtide
  (`dev_mode team_deathmatch lowtide`), standing in the bots' spawn square (Red's at y 1620-2020 in the scene, Blue's
  at -1620 to -2020) or watching it from the cross street. They should come in at the deathmatch spawns away from you.

