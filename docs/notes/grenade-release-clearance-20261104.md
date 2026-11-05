# Grenade release clearance — code only, 2026-11-04

`Throwable.SpawnProjectile` previously checked a 10-unit forward ray, then placed a grenade 32 units forward and
10 units toward the throwing hand. That unchecked forward/sideways offset could place it beyond close cover.

The release now sweeps a 2-unit-radius sphere from the aim position to the complete desired hand position and
uses the sweep's `EndPosition` (the sphere centre at contact). No offset is applied after the clearance check.
The thrower's hierarchy, triggers, player clips and movement volumes are excluded. Clear throws keep the same
spawn position, throw power, inherited velocity, spin, attribution and skin logic.

The radius is a conservative gameplay clearance approximation, not a per-model collision hull. This applies to
grenades using the base Throwable implementation; the recon drone has a separate spawn override. A camera
already embedded in solid geometry is not independently recovered by this change.

Validation: 86 checks against production Throwable/input code passed, including the actual spawn method with
deterministic trace seams, unobstructed position, full diagonal sweep, contact placement, inherited velocity
and attribution. Offline game build: 0 errors, 108 warnings. No editor connection, scene/prefab edits or live
physics verification was performed.
