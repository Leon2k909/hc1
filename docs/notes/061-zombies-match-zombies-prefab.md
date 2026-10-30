## Zombies match (`zombies.prefab`)
- The prefab has one state, "Zombies" (respawns after 3 s). It was a copy of TDM's, and the user saw TDM's
  "Preparing to start..." after their Zombies game had begun, so its Waiting, Preparing, Play Game and Game Over (team
  victory) states are gone. `ZombiesRoundSystem`, which `ZombiesGameMode` adds at runtime, runs the waves.
- Everyone is on Blue Team (`TeamAssigner.OnlyTeam` CounterTerrorist, no balancing), so every player gets the CT
  loadout.
- The scoreboard has no teams in Zombies (`Scoreboard.IsZombies`): one list of players with their Points and Kills from
  `ZombiesPlayerEconomy`. The pawn is replaced on respawn, so both carry over through `ZombiesGameMode.CarriedPoints` /
  `CarriedKills`, which a restart clears.
- Editing `zombies.prefab` while a Zombies match runs reloads the mode without its runtime `ZombiesRoundSystem`, so no
  zombies come: start a fresh match.
- TDM's Play Game state also gave 10 s of spawn protection, which Zombies doesn't need: the dead respawn in the break
  between rounds, with no zombies alive.
- Checked in-game 2026-09-26 (`dev_zombies`): the Zombies intro and no "Preparing to start", Blue Team, and the
  scoreboard's Points and Kills list. Solo, an idle player with the class menu open (it opens on joining a match) is
  downed about 17 s into round 1, and with nobody to revive them that's game over.
- The pause menu pauses the match only for a player on their own (`ZombiesRoundSystem.ApplyMenuPause`). The pause is
  the scene's TimeScale, and any player's menu used to freeze everyone where they stood. A match paused solo plays on
  when someone joins.
- A revived player stands up (`PlayerPawn.BuildInput`'s `_wasDowned`): they used to stay prone after a revive.
- The points and perk badges are `ZombiesPointsPanel`, in MainHUD's right column above the weapon list, which pushes
  them up as it grows. Pinned at a fixed height in `ZombiesRoundUI`, they were drawn over the list's rows (the user's
  screenshot, 2026-10-01).

