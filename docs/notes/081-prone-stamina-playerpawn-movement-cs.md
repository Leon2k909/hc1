## Prone stamina (`PlayerPawn.Movement.cs`)
- The user could spam prone ("like there's no stamina"). It now works like CS's crouch speed: each drop costs 0.2
  `ProneFatigue` and each get-up 0.3 (`ToggleProne`, the Prone key and Jump), wearing off at 0.2/s. Up to 0.35
  (`ProneFatigueFree`) nothing changes, so a drop and a get-up every second or two never slow. Past it, every stance
  change slows (`StanceChangeRate`, the lerp of `_smoothEyeHeight`, 10/s fresh). At 1 it's down to 30% dropping (flat in
  ~1 s, not 0.3) and 15% getting up (past crouch height in ~0.6 s, fully up in ~2 s). Mashing the key (4-5 presses a
  second) holds the eye between about -31 and -20 within 1-1.5 s (simulated, not measured). At a press a second the
  bob stays near-full, a pace a person could keep up.
- `ProneFatigue` is `[Sync]`, so every machine slows the body's height the same way (the hitboxes follow DuckLevel).
- Getting up is `IsGettingUp` until the eye passes crouch height: crouch speed and no sprinting, so a slow get-up isn't a
  sprint with a 24-unit capsule. A Jump press that gets you up is spent on that: it no longer also jumps off the floor.
- Forced prone (fall knockdown, Zombies' downed) costs nothing. Not yet checked in-game; `dev_prone [count] [interval]`
  presses it through the same path and logs the capsule height and fatigue.

