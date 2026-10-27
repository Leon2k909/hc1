## Damage indicator (`DamageIndicator`, `PlayerPawn.IndicatorSource`)
- The user, shot in the back, saw the red bar for a hit from the front, from where nobody could stand (2026-10-05). The
  bar pointed from the camera at the damage's `Position`. For a bullet (players' and bots'), a blade or a zombie's
  claw, that's where it struck you, or your own middle, inches from your own eye: no direction at all.
  - A round from behind that clipped the arms or the gun held out in front landed ahead of the eye, so it showed as
    a hit from the front.
  - A fall counted you as your own attacker, and showed a hit from the front too.
- `IndicatorSource` now gives the bar where the damage came from:
  - bullets and blades: back along the round's path (`Force` is its direction);
  - a zombie's claw, which has no direction: the zombie;
  - blasts and burns: their `Position`, the blast's centre or the heat's source, as before;
  - falls and damage you did yourself: none.
- `DamageIndicator.OnHit` also shows nothing for a source straight over or under the view.
- Compiled nowhere (no s&box SDK in the session that wrote it), not yet seen in-game.

