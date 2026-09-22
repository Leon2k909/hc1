# Play layout, Gunsmith rendering and tracer verification

Verified in the running s&box editor on September 22, 2026.

- `play-tall.png`: live menu capture at 1920 x 928. All four Play cards fill
  the available height (823 rendered pixels), retaining the wider Multiplayer card.
  Wrapping remains limited to the existing narrow/portrait layout rules.
- `gunsmith-clean.png`: live Gunsmith capture after reopening the scene. Bloom is
  disabled with strength zero, and depth of field is disabled in the scene resource.
- `build.log`: Code/Editor build result; zero errors, existing warnings remain.
- `tracer-validation.txt`: engine regression result from `hc1_tracer_qa`.

The tracer check creates an isolated scene, checks ordinary and tracer ammunition
for both SWB bullet implementations, and invokes bot shot effects to verify actual
tracer creation. It verifies that the shot payload controls the visible bot trail
even when the observer's ammo setting differs. The temporary scene is destroyed.
This is not a two-client multiplayer playtest.

`UsesTracerRounds` defaults to false in the bot weapon configuration and SWB
`ShootInfo`. The bot sends this choice with each shot; SWB makes the choice before
broadcasting hitscan effects or creating a physical bullet. Existing tracer chance
and effect prefabs only take effect after opting in. The subsequent selectable
Gunsmith ammunition slot and its verification are documented in
`Sources/Weapons/tracer-rounds.md`.
