## Ammo case v2 (`models/zombies/ammo_case_v2`, `Sources/Zombies/ammo_case_v2/`, 2026-10-30)
- What `ZombiesPowerUp.CreateAmmoCase` now shows, replacing tinted dev cubes with three magazines on top, at the user's word after a before/after. It's a steel
  chest with its lid up, full of magazines and cartons, at the same origin. No collider, as before.
- Players see it at the two Ammo Box stations, at 2.5 times the size. It's also the Resupply drop and the stand-in workbench's ammo can, but neither shows today:
  `DropPowerUps` is off and the real workbench loads.
- At that size its 2048 atlas gives about 6 px/in, so check it up close. If it's soft, rebake at 4096 or lower the scale in `CreateStation`.
- Falls back to two plain boxes with a log warning if the model doesn't load.
- Detail pass (2026-11-04): magazines now have physical curved side ribs, reinforced throats and folded feed lips around
  their cartridges. All three meshes and the 2048 atlas were rebuilt. Triangle counts are 21,548 / 9,422 / 3,078;
  bounds, origin, material count and station collision are unchanged. Native full model/material compilation succeeded,
  matched engine captures show the new details, and all offline geometry checks passed. See `Sources/Zombies/ammo_case_v2/README.md`
  and `output/ammo-case-detail-20261104/`. Native LOD switching and live-match viewing remain unchecked.
