## Prestige emblem (`Progression.GetPrestigeEmblem`)
- The user asked to show any prestige they've reached, not just their highest (2026-10-13). On Career Record's SERVICE
  MILESTONES, clicking a reached card picks it (EQUIPPED); a locked card does nothing.
- The pick is the cookie `hc1.progress.prestige_emblem` (`Progression.SetPrestigeEmblem`). `GetPrestigeEmblem` returns it
  while it's reached, else the highest prestige, and a new prestige clears it.
- The emblem shows in the menus' header, the squad card, the gunsmith's header, the rank card and the scoreboard. Over
  a match, a pick goes out at once (`Client.Local.RpcUpdatePrestige`). Unlocks and the rank label still go by
  `GetPrestige()`.
- Compiled with dotnet, not yet seen in-game.

