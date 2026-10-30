## Bullet drop (real exterior ballistics on hitscan shots, Warzone only)
- Only in Warzone (Battle Royale): a game mode has drop if it has the `BulletDrop` rule (`battle_royale.prefab`'s root).
  The user wants the main game's shots dead straight along the sights, and plans to come back to this system later.
- Shots still hit instantly, but they follow the real bullet's path: `Shootable.ApplyBallistics`
  (`Shootable.Ballistics.cs`) starts the shot `SightHeight` below the eye and follows the arc in straight segments
  (25 m, then 100 m past 300 m) to the first one that meets something. It traces from there, and damage falloff counts
  the path already travelled. Gravity drop is scaled by the cosine of the aim angle (rifleman's rule). No time of flight
  or lead (`Trajectory.TimeAt` has it if that's wanted).
- `Code/Weapons/Ballistics.cs` is a point-mass RK4 solver (ICAO sea-level air) with the standard G1/G7 drag tables and a
  sphere table for buckshot. One trajectory per load is cached, to 1500 m. It was checked against FM 3-22.9 (M855) and
  the AK/RPK/AKS-74U manuals' tables to within about 2 cm.
- Per-gun data are real loads and real sights, with no tuning: `MuzzleVelocity` (m/s), `DragFunction`,
  `BallisticCoefficient` (the published BC in lb/in²), `SightHeight` (in) and `ZeroRange` (the doctrinal zero: M4, M16A4,
  M16A2, MCX, L85A2 and HK416 M855 and SCAR-H M80 300 m, AKM/RPK/AK-15 PS 300 m, AKS-74U 7N6 275 m (sight "П"), AK-105, AK-12, AK-74M and RPK-16 7N6 300 m, MCX-SPEAR 6.8x51 300 m, M700 M118LR
  100 m, 9 mm guns, the P90's SS190 and the MP7A1's DM11 100 m (the two PDWs zeroed like the SMGs; the MP7's own zero
  wasn't found), pistols and buckshot 25 m). The battle zeros put the rifles 15–30 cm HIGH at 150–200 m. That's real,
  not a bug. The P90's BC (G1 0.155) is an estimate: none is published for SS190. The AUG takes the M4's zero (M855,
  300 m). The FAL's M80 is zeroed at 200 m, its rear sight's lowest setting (the battle zero).
- The Kastov 762, Vityaz, RPK, Bizon, AK-105, Vepr-12, M16A4, P90, MP7A1, AUG, Uzi, FAL, M18, MCX, L85A2, HK416, AK-12, AK-15, AK-74M, MCX-SPEAR, M16A2 and RPK-16
  take theirs from `kastov_prefabs.ballistics()` (`PS_BALLISTICS`); the other guns, including the patched 74u, have them set in the
  prefab. Optics don't change `SightHeight` (a few cm at most), and barrel parts don't change `MuzzleVelocity`: their
  length only moves the damage falloff (see the pipeline notes).
- Each gun also has its bullet's `BulletDiameter` and `BulletLength` (mm, from the load's drawings; a buckshot ball's
  length is its diameter), which set its supersonic crack (see Bullet cracks). The ported guns' come from
  `kastov_prefabs.py` (`ballistics(..., bullet)`, the `*_BULLET` constants).
- Near misses from drop still hit bodies, thanks to the box (see Bullet traces). Bots (`LightweightCombatBot`) do their
  own traces, a line with no drop.

