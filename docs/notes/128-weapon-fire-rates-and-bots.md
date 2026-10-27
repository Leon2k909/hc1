## Weapon fire rates and bots
- The SCAR-H's BaseDamage 36 is the M4's 20 scaled by muzzle energy: M80 at its prefab's 792 m/s is 2,989 J, and the
  M4's M855 at 905 m/s is 1,646 J. So in hardcore a body hit at full damage always kills (see Hardcore hit locations).
  The FAL's 41 is the same sum for M80 from its longer barrel (840 m/s, 3,362 J).
- `Shootable.FireRate` holds real-world cyclic rates (MP7A1 950, P90 900, MCX 850, HK416 850, MCX-SPEAR 850, M4 800, M16A4 and M16A2 800 in semi and
  three-round burst, MP5 800, Vityaz 750, AUG 715, Kastov-74u 700, AK-12 and AK-15 700 (and a two-round burst), RPK-16 700, L85A2 690, Bizon 680, FAL 675, SCAR-H 600, RPK 600,
  Kastov 762 600, AK-105 600, AK-74M 600, Uzi 600, Vepr-12 450 in semi).
  Shots are scheduled with carry-over (`_nextShotTime`), so any RPM fires exactly; don't tune values to the 50 Hz tick.
  Part effects on the rate: `GunsmithAttachmentEffects.FireRate` (AR barrel gas length, the Action slot's buffers) and
  `Shootable.SuppressorFireRateScale` (see Fire rate and fire modes in the gunsmith).
- Bot AI (sight/hearing, reaction, aim error, movement, bursts, reloads) is in `Code/GameLoop/Bots/LightweightCombatBot.Brain.cs`.
  Each bot name keeps its rolled Skill, its `Habits` (see Play styles) and its kills/deaths/score for the match (`LightweightBotManager`
  `_roster`, reused by `SpawnBot`). Every life is a new bot object and bodies last 15 s, so the scoreboard shows one row
  per name (`Scoreboard.ScoreboardBots`). Bot and zombie bodies are tagged `ragdoll` (the player's
  `CharacterController.IgnoreLayers`, so players walk through them instead of snagging) and `corpse` (footsteps). Teams are 5v5 (`BotFillRule` MinPlayerCount 10 / MaxTeamSize 5).
- Each bot name is issued a gun on its first life and keeps it all match (`BotIdentity.Weapon`, `RollWeapon`): half
  get rifles, three in ten SMGs, one in five an LMG, the RPK or the RPK-16 (a fire team's automatic rifleman). Each category's share is split
  between its guns, so a new gun doesn't change the mix. The pool (`WeaponPool`) is every non-WIP Primary rifle, SMG or
  LMG: the M700 is left out because bolt-action doesn't suit the bots' bursts. Its world model, BaseDamage with falloff,
  rate, magazine, reload times, shot sound and flash come from the gun's own prefabs (`WeaponShootable`,
  `ReadWeaponStats`). `WeaponResource` is set before `NetworkSpawn`, so clients get it in the spawn snapshot.
- The host can add/kick bots from the scoreboard (`LightweightBotManager.AddBot` / `KickBot`, `CanManageBots`). They're a
  per-team adjustment on top of `BotFillRule` (up to `MaxTeamBots` 12), gone next match. Modes with `TeamScoring` list
  both teams on the scoreboard even when one is empty (`Scoreboard.ListsBothTeams`): kicking a team's last bot used to
  take its heading, and so its Add Bot, off the scoreboard.
- The user wants the fight to come to them: real players are the bots' objective, other bots second. Enemy bots always
  hunt a real player (`PickHuntTarget`); the player's teammates go for the enemy bots nearest the players, or move up
  with them (`RegroupPoint`). Further than `ActionRadius` (2500) from every player, bots don't chase each other or go
  after noises. Navmesh spawns are around the players (`TryGetNavSpawn`: enemies ~`PreferredSpawnDistance` 2000 away,
  out of sight if possible, teammates at half that, all within `MaxSpawnDistanceFromPlayers` 3000), not anywhere on
  Flatgrass's ~32000-unit navmesh.
- A real player's bot teammates are support, so the player gets the kills: against enemy bots their aim error is
  x`SupportAimErrorScale` (2.5) and their reaction x`SupportReactionScale` (1.5) (`IsSupporting`). Enemy bots, and
  every bot's aim at real players, are unaffected.
- A bot covering a threat it can't see (last seen, a noise, a callout, being shot) looks at `_watchPoint`
  (`UpdateWatchPoint`): the threat if it's in view, else as far along the navmesh route there as it can see, or the shut
  door in front. Aiming straight at the threat through walls looked like a wallhack (the user's report).
- Navmesh islands (Flatgrass's building roof, sealed rooms) can't be walked to: `GoTo` checks the path and holds
  instead, a contact up there is only watched (`_contactUnreachable`), and `TryGetNavSpawn` needs a Complete path to the
  player. Map spawns and the fallback team spawns need one to a team spawn (`IsOnMainNavMesh`, cached per point). All
  190 of Flatgrass's own map spawns are on that roof, so bots never use them there. Before that, bots spawned on the
  roof and never came down, and bots going after them piled up underneath. Players still spawn there.
- Living bots have the player's movement box (`AttachMovementBox`: a local "Collider" child tagged `movement`,
  32x32x64, made on every machine and removed on death), so players can't walk through them. Shots and sight checks
  skip `movement`. Bots move on the navmesh, which ignores players, so `WaitForPlayer` stops a bot for 0.5 s at a time
  when a player is in its next stride instead of letting its box shove them.
- Bots keep apart (the user saw them "all grouped up together" on Innocent Hotel). The whole hotel is inside the hearing
  and callout ranges, and each team leaves one wing by the same corridors, so every sighting or burst sent a team to one
  point in a bunch. Bots after the same enemy, noise, callout or last sighting each take their own spot (`PickFreeSpot`:
  the usual one unless a teammate is on it or headed there, else one up to `SpotSpread` 500 off), and `KeepInterval`
  eases a bot off behind a teammate going its way, keeping an `Interval` of 200 (~5 m). Not yet checked in-game.
- Real players first, and no bunching (2026-09-29, the user: bots "end up clumped up together rather than their main
  objective being to take out real players"). Bot-on-bot fights drew every bot in earshot to one spot. Now:
  - A real player counts as half their distance (`PlayerPriority` 0.5) when a bot picks whom to fight
    (`FindVisibleEnemy`) or which noise to go after (`Listen`). Fighting a bot, it turns on a real player it can see
    within twice that bot's distance.
  - Bots' gunfire draws other bots only within half of `HearingRange` (`BotGunfireDraw`). A real player's is heard at
    the full range.
  - A callout about a bot reaches only the caller's two nearest teammates (`FireTeamSize`), as in a fire team. A
    callout about a real player still reaches everyone in `CalloutRange`.
  - While every real player is dead and a respawn is coming (`BotSystem.AwaitingRespawn`: a `Respawner` is active),
    bots don't go after each other or noises (`AwayFromAction`). Round modes have no active respawner, so it's off.
  - A bot closes on an enemy to its own spot at fighting range (`EngageSpot`, kept until the enemy moves 250), not onto
    the enemy, and strafes away from a teammate beside it (`NearestTeammateSide`).
  - Hunt guesses keep half their uncertainty apart from each other (`HuntSpot`), and in Hot Zone and Domination bots
    spread over the zone (`ObjectiveSpot`).
  - Teammates spawn at least `MinSpawnDistanceFromTeammates` (400, ~10 m) apart, and a spot within twice that scores
    lower (`TryGetNavSpawn`). At 150 a team's reinforcements came in as a bunch.
  - Compiled on 2026-09-29, not yet watched in a match.
- Suppressors (the user asked for some bots to have them): about one soldier in four is issued one of the gunsmith's
  Muzzle-slot suppressors for their gun (`RollMuzzle`, `SuppressorShare`, kept all match in `BotIdentity.Muzzle`). It's
  fitted on the bot's world model, its shots use the gun's suppressed sound, and the flash comes from the gun's
  `DischargeMuzzle`. A bot's gun keeps its suppressor on the floor (`DroppedEquipment.Build`), but picked up it has none.
  - A flash shows on some shots only, by the gun's `MuzzleFlashChance` (through a suppressor, its suppressed one), as
    for a player's gun. Bots used to flash on every round.
  - A suppressed shot is heard only within `SuppressedHearingRange` (800, ~20 m), players' included
    (`PlayerPawn.TimeSinceSuppressedShot`). Before, bots never heard a suppressed player.
- Fire discipline (`RollString`, `PauseAfter`), after FM 3-22.9: past `ControlledPairRange` (1600, ~40 m) single aimed
  rounds, one every 0.8-1.4 s plus 4 ms a metre; within it, controlled pairs (two presses 0.2-0.32 s apart by skill);
  under `CloseQuarters` (600, ~15 m) short bursts of 2-4 (SMGs 2-5). An LMG gunner fires 3-5 round bursts at every
  range (3-6 up close), then pauses 1.4-2.4 s at range. Burst-only guns fire one burst a pull. Before, bots fired 3-7
  round bursts under 13 m and 2-4 under 33 m, a quarter to half a second apart: five to eight rounds a second at anyone
  in view (the user: gunshots "far too often").
- Turns (the user: bots "run forward and then slow right down and then slow turn"). s&box's NavMeshAgent steers
  straight at the route's next corner and changes velocity no faster than its Acceleration. The prefab's 250 u/s² took
  1.3 s to turn 90 degrees and 1.8 s to turn back, and a bot faced its velocity, so its body swung round just as
  slowly. Three fixes, not yet watched in-game:
  - `MoveAcceleration` (800, set on the agent in `ConfigureComponents`, overriding the prefab) makes a 90-degree turn
    take 0.4 s.
  - With nothing to watch, a bot faces along its route (`RouteAhead`: `GetLookAhead( RouteLookAhead 160 )`, ~0.7 s
    ahead), so it turns into corners.
  - `Hunt` stays after one enemy for 20-30 s (`PickHuntTarget`, `_huntTarget`), and its spot follows them from the
    same side (`HuntSpot`, `_huntGuess`). While roaming it keeps its goal until it gets there (`KeepRoaming`). Before,
    it guessed a new enemy and spot every 5-9 s, which was a turn in the middle of a run.
- Sprinting and awareness (2026-09-29, the user: "i never see any bots running to get the sprint to fire penalty",
  and round a corner they were "standing still or slowly moving forward instead of like real people who sometimes dont
  have the full situational awareness"). Bots used to move at 195-230 everywhere, gun carried but free to fire. Now:
  - A bot walks and sprints at a player's speeds with its gun (`ReadGaits`): a walk of 250 less the gun's
    SpeedPenalty, at most 180 (under `MaxShoulderedSpeed` 190), and a sprint of 330 less half the penalty, both slowed
    by WeightSlowdown (see Movement speeds). The M16A4 (penalty 40) walks at 180 and sprints at 310. A NavMeshAgent
    loses nothing to friction, so a bot's sprint is ~8% faster than a player's with the same gun (~285).
  - With no enemy in view it sprints, gun carried, and walks with the gun up only near where it's going
    (`ApproachSpeed`: `Lerp( 700, 150, Aggression )`, about 620 for the most cautious and 220 for the most
    aggressive). Getting somewhere it must (`UrgentSpeed`: out of the heat, into the zone) it sprints unless an enemy
    is in view. Where it's going is often a guess, so it can come round a corner at a run.
  - Faster than 190 it's sprinting (`IsSprinting`):
    - It can't fire until 0.25 s after (`SprintOutTime`, a player's "no_shooting" time).
    - It notices enemies in a 90-degree cone (`SprintFieldOfView`; 120 otherwise). At the corner of its eye it sees
      only within 350 and 80 degrees (700 and 100 otherwise).
    - It doesn't hear footsteps.
    - It looks along its route, not at the threat it's covering.
    - Caught at a run it stops and gets the gun up, rather than running on into a strafe.
  - Footsteps are heard only half of `FootstepHearingRange` (550) through a wall. From further off, bots faced the
    corner a player would come round before they came round it.
  - A callout takes 0.8-2 s to be taken in (`HearCallout`, `TakeInCallout`) and lands 200 plus a tenth of the distance
    off. Before, every teammate knew at once, to within 200, where a bot had just seen someone.
  - A hunt's guess at an enemy (`HuntSpot`) is 500-1200 off them, never closer (it was 200).
  - Bodies on the human model (`citizen_human_male`) aren't driven through the ring below: their graph picks walk, run
    and sprint clips by speed, so a bot there gets its true velocity and `move_style` Run, as a player's body does.
    Clamped to the ring, a sprinting bot's legs jogged.
  - Live in the user's match since a hotload on 2026-09-29, but not yet watched.
- Play styles and moving in a fight (2026-09-29, the user: bots "are often just stood still rather than moving and
  shooting, running and then not shooting", and "behaviour should be unique, as real players would be").
  - Each soldier gets a `BotStyle` and its own `BotHabits` (`LightweightCombatBot.Style.cs`), rolled with its gun and
    kept per name (`BotIdentity.Habits`). The gun weights the style, as players pick a gun that suits how they play:
    - `Rusher`: pushes to close range, quick strafes, quick crouches mid-fight, straight after anyone who ducks away.
      Most SMGs.
    - `Flanker`: closes in and hunts round one side (`EngageSpot`, `HuntSpot`), and moves to a spot out of sight every
      two or three strings.
    - `Rifleman`: middle range; strafes, plants and steps up, and moves spot every few strings.
    - `Anchor`: fights from further back, peeks either side of its spot, crouches to shoot, backs off when rushed,
      searches only half way, and holds each spot it reaches while hunting for 2-5 s. Most LMGs.
    - `Marksman`: long range, planted (often crouched) single aimed shots, moves after two or three, holds spots 3-6 s.
    - Aggression now comes with the style. Each bot also rolls its own range, strafe rhythm and pace, how long it
      plants, how often it crouches, how patient it is and which side it likes to peek.
  - In a fight a bot always has a move on, and fires through all of them (`Manoeuvre`, `NextMove`):
    - a strafe (mostly back the other way, a player's A-D);
    - a plant of at most about a second, for an aimed shot (never two in a row, more often for recruits);
    - a push in at an angle, or a step back;
    - a new spot to the side after `RelocateAfter` strings or a hit.
    Before, each 0.6-1.5 s it rolled a strafe or stood still (recruits three times in four), and it stood through every
    reload. Now a reload is spent strafing or backing off. Closing in is at the gun's walk, gun up (it was 138).
  - Running: a bot that notices someone at a sprint lets the sprint go `SprintBreak` (0.18-0.35 s) later, before it
    has registered them, instead of running on at full tilt with its gun down. It goes after someone who ducked out of
    sight at a walk (the keenest used to run at 207, gun down).
  - Moving costs aim: at a 180 walk, 1.7x the error for a recruit and 1.4x for a veteran (`AimError`). That's why the
    holders plant.
  - `dev_bot_styles` logs every living bot's style, habits, gun and current move.
  - Crouching (2026-10-19, the user: bots "crouch spam erratically" and snap between standing and crouching):
    - A plant used to roll its own crouch and last 0.15-1.3 s, so bots bobbed down and up every second or two (a
      rusher's 0.15-0.35 s plants had a 35-70% crouch). Now a crouched plant lasts at least the drop plus 1-1.6 s (rusher),
      1.3-2.4 s (rifleman, flanker) or 1.8-3.2 s (anchor, marksman), and after getting up a bot waits 3.5-7 s before it
      crouches again (`Plant`, `_crouchRest`). A rusher crouches on 8-20% of plants. Being hit still ends the plant.
    - Every machine eases the stance from the synced `IsCrouching` (`CrouchBlend`, `UpdateStance`): down in 0.35 s, up
      in 0.45 s, smoothstepped. The graph's `duck`, the eye (`BotPronePose.EyeOffset( float, ... )`) and so the
      shouldered gun follow it. The movement box still changes at once. A slide doesn't sink it (its own pose does).
    - Compiled with dotnet and in the editor (0 errors). Not yet watched in a match.
  - Compiled and hotloaded into the user's match on 2026-09-29, not yet watched.

