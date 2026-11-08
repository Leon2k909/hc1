# Landing impacts on moving surfaces — 2026-11-05

`PlayerPawn.GroundedChanged` uses vertical closing speed against the contacted ground collider for its existing
landing sound, fall damage and knockdown thresholds. Previously it used the absolute world vertical speed of the
player, regardless of the surface's motion.

`PlayerPawn.LandingImpactSpeed` samples `GroundCollider.GetVelocityAtPoint` at the player's feet. This includes
the collider's point velocity rather than only its centre's linear motion. `LandingImpactRules.ClosingSpeed`
computes `max(0, surfaceVerticalVelocity - playerVerticalVelocity)`. A surface descending with the player softens
the impact, one rising toward them increases it, and separating motion produces no impact. Missing ground
colliders use static ground as a fallback. Non-finite inputs are handled without propagating invalid values.

This remains the existing vertical fall model: static-floor downward impacts and thresholds are preserved.
It does not add a contact-normal injury model, platform riding, or a new damage curve. The pre-movement player
velocity is still the existing controller sample, rather than a new continuous collision-time measurement.

Validation: 36 checks execute the production rule and pawn sampling method with engine seams. They cover static
floors, matching motion, approaching and separating surfaces, invalid values, finite extremes, foot-position
sampling and horizontal-velocity independence. Offline game compilation passed with zero errors. No editor
connection or live physics/gameplay validation was performed. Changes were left local, uncommitted and unpushed.
