## Skirmish (1v1 / 2v2): bot fill and the arena (`SkirmishArena`)
- The user (2026-10-01): 1v1 Skirmish filled to 5v5 with bots, and big maps should have bounds on the small modes.
- Bot fill: `gunfight_1v1.prefab` and `gunfight_2v2.prefab` had `BotFillRule`'s 5v5 defaults. They now fill to their
  size (MaxTeamSize 1 / 2, MinPlayerCount 2 / 4), and `WaitForPlayers` skips at 2 / 4. As a backstop, `BotFillRule`
  never fills a side past the mode's `TeamAssigner.MaxTeamSize`. The other modes' assigners take 5 or 10 a side,
  so they're unchanged.
- The arena (`Code/GameLoop/Rules/SkirmishArena.cs`, on both prefabs; Radius 1000, ~25 m, for 1v1 and 1300, ~33 m, for
  2v2):
  - It's only used where the teams' spawns are further apart than 2.2 radii (`BigMapSeparation`). That means Belltower
    (4093) and Flatgrass (8315), but not Innocent Hotel (1993).
  - The host picks it once, after `GamemodeInitializedEvent` and once the navmesh has built. Before the event,
    `GameModeObject` hasn't switched off other modes' objects yet, and Belltower's Retakes spawns made its teams' spawns
    look about half as far apart.
  - Candidate middles: the map's `ObjectiveSpot`s (Belltower's fight places), the midpoint between the teams, and 8
    random navmesh points round it. Each must have a complete navmesh path from a team spawn, which rules out roofs and
    other islands.
  - Its spawns are a ring at 0.72 of the radius (16 tries, kept between 0.45 and 0.85 out and 220 apart). Each one has
    standing room, and a route to the middle that stays inside the circle and is under twice the straight line. A
    middle needs at least 6.
  - It's scored on the spawns, plus one for each spawn with another across the ring that it can't see. It picks at
    random among the best 3, so a map isn't always fought over in the same spot.
  - Anyone spawned before it was picked is moved in (`MoveEveryoneIn`): a player outside is respawned, and a bot
    outside is removed for the fill to bring back inside.
- Spawning: `GameUtils.GetSpawnPoints`, `TeamSpawnAssigner` and the bots' `GetSpawnTransform` all go to the arena first
  (`SkirmishArena.Settled`). `PickSpawn` puts each side as far from the enemy as the ring allows, out of their sight,
  near a living teammate, and never on someone.
- Bounds:
  - A player outside the circle gets the play area's "Return to the AO" and is killed after 5 s (`SkirmishArena.Contains`,
    in `PlayerPawn.UpdatePlayArea`).
  - Every point a bot heads for is pulled 96 inside the edge (`NavPoint` → `SkirmishArena.Clamp`).
  - The radar draws the circle in the UI's amber (`Minimap.razor`'s `.arena`, `MinimapRenderer.FromWorldRadar` with
    `clamp: false`).
- If no candidate fits, it logs a warning and the match uses the whole map. Compiled offline (2026-10-01), not yet
  checked in a match. To check: a 1v1 and a 2v2 on Belltower should have one bot per enemy slot, the ring on the
  radar, the warning outside it, and bots staying inside.

