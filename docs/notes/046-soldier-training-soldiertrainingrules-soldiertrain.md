## Soldier training (`SoldierTrainingRules`, `SoldierTraining`, `Client.Training`, `PlayerPawn.Training`)
- Players improve the skills they use (2026-10-18). The existing career level stays 1–55; Endurance and Weapon Handling
  each run from 1–50. Earned skill XP also adds to career XP. Skills survive deaths, map changes and prestige.
- Endurance earns 1 XP per 10 metres of actual ground sprinting. The host samples movement every 0.25 s and rejects
  stationary movement, teleport-sized/stale samples, other movement modes and the first sample after a pawn changes.
  Handling earns 1 practice XP at most every 2 s from the existing synced discharge times, plus 2 XP for an enemy
  bullet hit (3 for a headshot), at most once per 0.5 s across pellets/targets. Accepted zombie hits use the same cap.
  Only living, active players earn it; downed/frozen players, noclip, drone control, developer movement/god modes and
  the gunsmith firing range do not. The game mode must have an active PlayerStatsRule. Bots get baseline modifiers.
- Curves and tuning are in `Code/Stats/SoldierTrainingRules.cs`. Benefits grow within each level. Maximum bonuses are
  +20% sprint capacity, +15% stamina recovery, -12% recoil, -15% weapon sway, and -10% aim/reload duration. No damage,
  health or movement-speed bonus. Attachments, mounting, wounds and Zombies perks keep their existing effects.
- Sprinting now uses a normalized stamina pool: 12 s at baseline, 14.4 s at maximum Endurance. It recovers fully in
  6 s at baseline after a 1.25 s delay; exhaustion holds sprint off until 25% is recovered. Actual ground movement
  drains it, and respawn refills it. Endurance also speeds the existing jump/prone fatigue recovery. The owner drives
  stamina as it does movement; the host owns earned training totals.
- Aimed breathing (2026-10-20): `AimBreathingRules` supplies a small vertical breathing cycle, slower hand drift and a
  tiny smooth tremor. `CameraController.Breathing.cs` applies it to the first-person aiming camera after its per-frame
  rotation reset; the viewmodel, scope and existing `Shootable.WeaponRay` follow the same view. Mouse input and
  `EyeAngles` are not accumulated or rewritten. ADS transitions fade the effect; inactive/dead/frozen/drone/noclip
  cameras reset it, and holstering, lowering, reloads, mantling and climbing fade out the aimed motion.
  Rested novice additional bounds are 0.119 degrees pitch and 0.0555 yaw, before existing animations/effects.
  Handling retains its continuous 15% maximum reduction, including the remaining motion at level 50. Crouching,
  prone and mounting scale this breathing by 0.70, 0.42 and 0.22 respectively. Stamina depletion smoothly raises its
  amplitude up to 1.8 times and rate from 13 to 24 breaths/minute; trained Endurance helps through stamina/recovery.
  The training harness now passes 17 scenarios, including breathing bounds, all skill levels, stance/fatigue effects,
  ADS transitions and 30/60/120/144 Hz continuity. The game project builds with 0 errors, and native compilation
  and the loaded rules passed a read-only check in `output/aim-breathing/native-verified/`. Scene/play/document state
  stayed unchanged. The live aimed view and feel have not been reviewed yet.
- `Reloadable` captures its combined duration multiplier at the start of a reload, including shell continuations.
  Reload completion, sound timing and the viewmodel's existing reload-speed parameter use that captured value, so a
  skill gain midway through cannot move them apart. A cancelled reload's delayed sounds cannot bleed into a new one.
- Progress uses the existing local-cookie trust model, not server-verified account storage. Versioned, account-scoped
  keys are `hc1.training.v1.{Game.SteamId}.Endurance` and `.Handling`. The host imports capped values once per connection
  and merges higher retained values on reconnect. Owner snapshots merge monotonically; they never undo newer saved
  progress or award career XP for an import. Dirty profiles save every 5 s, immediately on a skill improvement, and
  on Client teardown (including after its network owner is cleared). Account changes flush the old keys first.
- `SoldierTrainingPanel` sits in Profile → Career Record between career rank and service milestones. It shows both
  levels, XP remaining, current benefits and caps. `SoldierTrainingHud` puts career progress and stamina below Vitals.
  It hides for spectators and drone control.
  All new text is in the 13 translation languages as well as English; the translation checker adds no new findings.
- A skill's level-up is a medal at the top centre (2026-10-19). The user found the old box beside Vitals horrible
  ("SKILL IMPROVED / WEAPON HANDLINGLEVEL 3": Razor had dropped the "·"), and asked for it at the top middle, like
  the one-shot-one-kill medal.
  - `MedalFeed` watches `SoldierTraining.LevelUpRevision` and queues a `training` medal with the kill medals:
    the skill's name, SKILL IMPROVED, and the new level in the badge's diamond (`.medal-level`), up for 2.4 s.
  - A feed built after a level-up doesn't show it again: the first tick only takes the current revision.
  - The badge is `ui/medals/training.png`, made by `Tools/training_emblem.py` from the plain Ranked shield
    (`ui/ranked/unranked.png`): the steel warmed to brass and its empty diamond filled with dark gunmetal.
  - `dev_medal handling|endurance [seconds]` shows one.
  - Checked in a browser mockup of the flattened SCSS, beside the one-shot medal. Not yet seen in a match.
- Original training validation (2026-10-18): `dotnet run --project Tools/SoldierTrainingChecks/SoldierTrainingChecks.csproj` passed 12 scenarios using
  the actual rules/profile files (only account, cookies and clock are stubbed), covering every level threshold, caps,
  several tick rates, recovery hysteresis, movement rejection and account/save/snapshot behavior. The C: project's
  `Code/razedtest.csproj` builds against the installed engine with 0 errors (95 existing warnings on the final build).
  sbox-cli reported no running editor with this project open, so live HUD rendering, RPC/host migration, respawn and
  weapon feel still need an in-game playtest. No editor was launched or scene/prefab edited for this feature.

