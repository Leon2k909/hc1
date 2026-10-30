## Movement speeds (`PlayerGlobals`, `PlayerPawn.GetWishSpeed`)
- The user asked for faster movement that feels like Black Ops Cold War's (2026-10-13: "make the sprint/movement speeds
  etc faster it should feel cold war"). No mode, menu or text names it; it's only the feel.
- `PlayerGlobals`' code defaults are live (no scene or prefab overrides them):
  - WalkSpeed 250 (was 220), SprintingSpeed 330 (260), CrouchingSpeed 120 (100), SlowWalkSpeed 115 (100), ProneSpeed
    60 (50).
  - BaseAcceleration 11 (9). Friction, the other accelerations and JumpPower 290 are unchanged.
- A gun's SpeedPenalty (0, 20, 30 or 40) comes off the walk in full and off the sprint by half, then WeightSlowdown,
  wounds, perks and the flashbang scale it. On the ground each tick accelerates, then applies friction, so at 50 Hz a
  walk tops out at 86% of its wish speed (friction 7) and the other gaits at 92% (friction 4). Real top speeds:
  - a rifle (penalty 40): walk ~181 u/s (4.6 m/s, was ~155), sprint ~285 (7.2 m/s, was ~221);
  - no penalty: walk ~215 (was ~189), sprint ~304 (was ~239);
  - crouch ~110, slow walk ~106, prone ~55.
  - A walk is at full speed in ~0.14 s (7 ticks; it was ~0.2 s).
- Copies that have to change with them: `GunsmithStats` (`WalkSpeed`, `SprintSpeed`, `CrouchSpeed`, `ProneSpeed`, for
  DETAILS and COMPARE) and the bots' `PlayerWalkSpeed` / `PlayerSprintSpeed` (`LightweightCombatBot.Brain`). Bots'
  walks stay capped at 180 by `MaxShoulderedSpeed`, so only their sprint got faster.
- A vault carries a sprint through it up to `VaultMaxSpeed` 310 (`PlayerPawn.Mantle.cs`, was 260).
- Left as they were: the footsteps' cadence (`PlayerFootsteps.GetStepFrequency`), the guns' sprint-out times (each
  gun's real figure), `IsNoisy`'s 180, and the viewmodel's bob range.
- The legs' clips play at their own pace (players don't set `move_rate`, see Leg animation speeds), so a player's feet
  slide more than they did.
- Compiled with dotnet, not yet checked in-game.

