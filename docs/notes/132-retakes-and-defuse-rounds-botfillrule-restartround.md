## Retakes and Defuse rounds (`BotFillRule.RestartRound`)
- The user (2026-10-01): in Retakes on Belltower they spawned among the enemies and died at once. After the first fix
  below they still did ("the spawns are terrible").
- The real cause was `ActiveBombSiteSelector`. Each round it switches on the spawns tagged with that round's site and
  switches off the rest, but it found them with `GetComponentsInChildren`, which only returns enabled components (as
  does `Scene.GetAllComponents`: the scene's index only holds active ones). So the first round at the other site
  switched every spawn off, and they stayed off for the rest of the match.
  - With no spawns, `TeamSpawnAssigner` falls back to the Unassigned team's (Belltower's deathmatch spawns, off in
    Retakes) and then to the world's origin, and the bots' `GetSpawnTransform` to the origin too. So both teams,
    players and bots, spawned on one spot: open ground in the middle of Belltower. Every Retakes map had it.
  - It now goes through every spawn (`Scene.Components.GetAll( FindMode.EverythingInSelfAndDescendants )`), leaving
    those under an object the mode switched off, and warns if the site has none for a team.
- Bots were also never reset between Retakes rounds. They stood where the last round left them, and in the first round
  where the Waiting state's spawns put them. Belltower's Blue spawn road is beside both bomb sites, so a Red player
  could spawn among them.
- Now every round mode (Defuse and Retakes, `BotFillRule.IsRoundMode`) starts each round afresh:
  - `RespawnPlayers` calls `RestartRound` before respawning the players. It clears the last round's bots, so they
    don't count in the players' spawn picks.
  - 0.1 s later the full roster comes back at this round's enabled spawns.
- `ClearBots` disables each bot before destroying it. A destroy only happens at the end of the frame, and the players'
  spawn picks in that frame would still find them.
- Once a round is under way (its bomb handlers are active), a late join or a state change doesn't refill a round mode's
  bots (`UpdatePlayerCount` returns), so teammates killed earlier in the round stay dead.
- A bot's spawn point (`LightweightBotManager.GetSpawnTransform`) is one nobody stands on (within
  `OccupiedSpawnRadius`, 48) where there is one. Retakes places a whole team on as few points as it has players.
- Compiled offline, not yet checked in a match. To check it, play several Retakes rounds on Belltower until the site
  changes: each team should start at that site's spawns.

