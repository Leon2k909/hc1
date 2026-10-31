## Ammo case v2 (`models/zombies/ammo_case_v2`, `Sources/Zombies/ammo_case_v2/`, 2026-10-30)
- What `ZombiesPowerUp.CreateAmmoCase` now shows, replacing tinted dev cubes with three magazines on top, at the user's word after a before/after. It's a steel
  chest with its lid up, full of magazines and cartons, at the same origin. No collider, as before.
- Players see it at the two Ammo Box stations, at 2.5 times the size. It's also the Resupply drop and the stand-in workbench's ammo can, but neither shows today:
  `DropPowerUps` is off and the real workbench loads.
- At that size its 2048 atlas gives about 6 px/in, so check it up close. If it's soft, rebake at 4096 or lower the scale in `CreateStation`.
- Falls back to two plain boxes with a log warning if the model doesn't load. Built offline and **not yet compiled as an asset or seen in s&box**: see the folder's
  README.
