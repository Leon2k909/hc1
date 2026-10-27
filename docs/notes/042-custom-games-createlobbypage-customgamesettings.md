## Custom games (`CreateLobbyPage`, `CustomGameSettings`)
- The header's CUSTOM GAME tab (`/new`) was PRIVATE / Private Match. The user renamed it when WHO CAN JOIN got a public
  option. The page picks a match map, mode, player limit, bot fill and who can join. START CUSTOM GAME puts the
  choices in `CustomGameSettings.Current` and loads the map, and opening the main menu clears them.
  - `GameNetworkManager` makes the lobby from `CreateLobbyConfig()`, named "<host>'s Custom Game".
  - `BotFillRule` fills to the page's player limit.
- WHO CAN JOIN is the lobby's `LobbyPrivacy`: Invite Only (`Private`, the default), Friends (`FriendsOnly`) or Public.
  Only Public lobbies show in SESSIONS' server browser and s&box's own server list.
- In the editor, s&box makes every lobby with `Networking.EditorLobbyPrivacy` and marks it as a dev lobby, which the
  server browser hides outside the editor. So the Public listing can only be checked in a published build.
- `hc1_private_ui` (Editor/Hc1PrivateMatchQa.cs) clicks through the page's options. `hc1_private_ui start` starts a
  4-player TDM from them; once it has loaded, `hc1_private_ui check` checks the lobby.
- Match rules, like CoD's private match options (2026-10-05). The user found the page "too bare bones" and asked to
  change "values like health etc like cod does".
  - The page has three tabs: MATCH (map, mode, player limit, bot fill, bot difficulty, who can join), RULES and PLAYER.
    Zombies plays by its own rules, so it has only the first and gets no rules.
  - A tab shows how many of its rules differ from a normal match's, and a normal match's value is underlined. The
    summary lists the limits and every rule that's changed, in orange. RESET RULES puts the RULES and PLAYER tabs back.
  - The picks go into `CustomGameSettings.Rules` (`CustomGameRules`). They hold for every map the lobby plays through
    the map vote, since `Current` lasts until the main menu.
- The rules:
  - TIME LIMIT: 5-30 min or none. It's the mode's "Play Game" state's `DefaultDuration`
    (`CustomGameSettings.IsTimedPlayState`), so only TDM, Deathmatch, Domination, Hot Zone, Gun Game and the Skirmishes
    have one. No limit is an infinite duration, and `GameMode.DisplayedTime` then shows no clock.
  - SCORE LIMIT: `TeamEarlyWinCondition.TargetScore`, from a list for each mode. "No limit" is int.MaxValue, offered
    only where the clock still ends the match. Defuse's is ROUNDS TO WIN, which also sets `RoundLimit.MaxRounds` to
    twice it (the prefab's 6 of 12), and Retakes' is ROUND LIMIT (`MaxRounds`).
  - RESPAWN DELAY: instant to 10 s (`Respawner.RespawnDelaySeconds`). It isn't offered in the round modes, which
    respawn everyone at the next round. Bots wait it out too: `LightweightBotManager.AwaitingRespawn` counts a bot
    killed within the delay as still there. Without a custom game, a dead bot is replaced at the next fill check, as before.
  - FRIENDLY FIRE: on, as in every hardcore match, or off. Off, `HealthComponent.IsRuledOut` drops a teammate's
    damage (bullets, blades, blasts, fire) before anyone hears of it, so there's no hitmarker. Your own still hurts you.
    Team modes only.
  - MAX HEALTH: 30-300, for players (each spawn) and bots (`CustomGameSettings.ApplyMaxHealth`).
    `HealthComponent.MaxHealth` is synced now, since the HUD shows health against it. Head and neck hits still kill.
    A body hit's chance to kill outright scales by 100 over the health (an M4's 50% at 100, 25% at 200), and the body
    and limb wounds take more hits to add up.
  - HEALTH REGENERATION: normal (4 s, then 25 a second), fast (2 s, 50), slow (8 s, 10) or off
    (`CustomGameRules.RegenSpeed`, `PlayerPawn.UpdateHealthRegen`).
  - HEADSHOTS ONLY: bullets anywhere but the head or neck do nothing. Knives, blasts and fire still hurt anywhere.
  - BOT DIFFICULTY: mixed (the usual roll), recruit, regular, hardened or veteran. `LightweightCombatBot.RollSkill`
    narrows the skill roll round the level.
- How they reach the match: `GameMode.OnStart` calls `CustomGameSettings.ApplyTo` on the host, which writes the
  limits and the respawn delay into the mode's own components before play starts. Those are all synced. The rest is
  read where it applies, through `CustomGameSettings.ActiveRules` (a normal match's defaults outside a custom game).
  Everything is on the host but `MaxHealth`, which is synced.
- Made without an s&box SDK, so it has been compiled nowhere. Watch the editor's log for errors after the hotload.
  Checked only in a browser mockup of the page's real SCSS. Nothing has been seen in-game.

