# Radial blast impulse — code only, 2026-11-04

`Explosion.AtPoint` previously used `distance * 50` as the impulse magnitude: farther targets received more
force. It now uses `BlastImpulseRules.Magnitude`, which decreases linearly from `radius * 50` near the source
to zero at the blast radius. The original maximum envelope and midpoint force are preserved. This is a gameplay
falloff, not a simulation of overpressure, reflection, fragmentation or target mass.

Both HealthComponent/Prop damage and generic engine damage receivers (including zombies) use the same helper.
Existing line-of-sight cover checks and health-damage curves remain in place. Invalid or nonpositive explosion
radii now exit before a physics query or division by radius. Helper inputs are finite and overflow guarded.

Callers are the HE grenade, LPG canister and `Tec.Exploder`; the bomb site's separate detonation damage is outside
this change. No scenes, prefabs or graphics assets were edited.

Validation: 85 production-rule checks cover several radii, strictly diminishing impulse, the radius boundary,
preserved midpoint scale and invalid/extreme inputs. No editor connection or live gameplay check was performed.

## One damage application per target — 2026-11-05

`Explosion.AtPoint` now also deduplicates HealthComponent/Prop targets by root after a successful line-of-sight
check. Several collider objects belonging to one target previously multiplied its damage and impulse. An occluded
collider does not claim the target, so a later exposed collider can still receive the blast. The set is local to
each explosion; another detonation can damage the same target normally. Damage curves and cover traces are unchanged.

`Tools/ExplosionTargetChecks` executes the production explosion loop with engine seams, covering one/two/eight
collider objects, player and prop damage, successive detonations, separate bodies, full cover and partial cover
where the first collider is hidden. All 21 checks and offline game compilation passed. No editor was used;
live physics queries and multiplayer remain unverified.
