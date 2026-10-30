## Battle royale (Warzone, `Code/GameLoop/Rules/BattleRoyale/`)
- Solos on Flatgrass (the user's first pick, for its size) or Ridgeback (below), picked on the hub's Battle Royale
  screen (`br_map`, `BattleRoyaleMatch.GetMaps`: Flatgrass, then every scene whose GameModes list the mode): players and
  bots all against each other (`GameUtils.IsBattleRoyale` is part of `IsFreeForAllMode`, so bots are `Team.Unassigned`),
  no respawns, and the last one standing wins. Flatgrass leaves the mode out of its list, so it's only reached from the
  hub (or `dev_mode`). Ridgeback lists only this mode and isn't a match map, so it's in no other map list.
- `battle_royale.prefab`: Waiting (starts with one player) → Preparing (10 s, frozen: `RespawnPlayers` lands everyone,
  `BattleRoyaleDeploy` drops the bots in, 3 a tick) → Play Game (`BattleRoyaleFight` starts the zone; 20 min cap) →
  Game Over (6 s) → Post Game (15 s, `KillGameOnEnd`: the end screen, then the menu). There's no map vote.
- `BattleRoyaleMatch` (root) counts who's alive, keeps each player's placing (`Placements`, synced) and ends the match
  when one is left, or 8 s after the last real player is out. Drop points (`TryGetDropPoint`) are spread over the first
  circle, only where `LightweightBotManager.IsWalkable` holds (all Flatgrass's own spawns are on its roof). The first
  circle is the scene's `BattleRoyaleArea` (centre and radius) if it has one, else sampled from the whole navmesh.
  Players spawn at drop points too (`BattleRoyaleSpawnAssigner`).
- `SafeZoneManager` (root): six phases of hold then shrink (`GetPhase`, about 9.5 min), each circle inside the last and
  on walkable ground, the last closing to nothing. Only the circles and times are synced; every machine works out the
  moving zone. Outside it, once a second, players and bots take `DamageFlags.Zone` damage (2 to 25 HP/s): it's never
  a hardcore one-shot or a bot's instant kill, and it holds off health regen, which would outpace it otherwise.
- Bots (`LightweightCombatBot.BattleRoyale.cs`): `HeadForZone` comes before fighting when a bot is in the gas, or outside
  the next circle while it closes or will before the bot could walk in (45 s spare for the most cautious, 10 s for the
  most aggressive). They shoot on the way. With no `AwayFromAction` in battle royale, bots fight each other anywhere,
  so the field thins out; they hunt whoever's within 2500, players and bots alike, else roam toward the next circle, and
  don't chase anyone, or investigate a noise, out in the gas.
- HUD: `BattleRoyaleRadar` in the minimap's corner (the zone and next circle turning with the view, alive, kills, the
  zone clock) and `BattleRoyaleHud` (the gas warning, the zone's news, your placing once you're out). The end screen
  reads "VICTORY" or "12TH PLACE" and lists the top ten. After death the freecam starts where your view was.
- The end screen (`EndOfMatchScreen`) couldn't be clicked and showed no cursor (the user, 2026-10-05). It's inside
  MainHUD, whose `pointer-events: none` and `cursor: none` its children inherit, so `.eom-screen` turns them back on, as
  ClassSelect does. Any clickable panel inside MainHUD needs the same.
- Its CONTINUE only hid the screen until the match sent everyone to the menu, so where a match ends that way
  (`KillGameOnEnd`, battle royale, not ranked) it's PLAY AGAIN, which the user asked for, beside LEAVE GAME.
  - PLAY AGAIN starts the same mode on the same map as the map vote's mode cards do (`MatchLauncher.LeaveAndStart`).
    Meanwhile `KillGameOnEnd.IsLeaving` keeps the end of Post Game from loading the menu over it.
  - LEAVE GAME goes to the menu at once.
  - Ranked and the map-vote modes keep CONTINUE.
  - Written without s&box or dotnet, so it hasn't been compiled. Not yet checked in-game.
- Performance with lots of bots (`BotSystem`, all undone by `bot_lod_off 1`): bots far from every viewer look less
  often, share their lists of the living, re-route less, have no bone objects (the gun follows the hand bone,
  `FollowHands`), and skip muzzle flashes and blood nobody could see (`ShouldShowEffect`, judged by on-screen size, so a
  scope counts), and shots further off than their sound carries (`CanHear`, the sound's own `Distance`, 330 m for most
  guns). Close bots are untouched.
- A big map's navmesh can still be building after the scene loads, so the first circle, the bots' drop-in and the zone's
  start all wait for `Scene.NavMesh.IsGenerating` to clear (`EnsureFirstCircle`, `SpawnSomeBots`, `StartZone`).

