## Bullet traces (`Shootable.DoTraceBullet`)
- A bullet is a line through the world: walls, floors and props stop it only where its line meets them. Bodies
  (players' and bots' hitboxes, zombies' capsules: `IsBody`) are found with a box of `max(BulletSize*1.75, 14)` units
  (±7 in; the M700's is ±28 in), so near misses still hit them. The box counts only where it touches a body in the open:
  `InTheOpen` needs a clear line from the bullet's path (a box trace's `EndPosition`) to the point of contact
  (`HitPosition`), so a body hidden behind a corner the line passes isn't hit.
- The whole trace used to be that box. It clipped wall edges up to 7 units off the line (the M700 28), so a shot aimed
  just past a corner you stood close to hit the corner, with the impact effects in your face (the user's report). World
  impacts also sat at the box's centre, ~7 units off the surface; they're on the surface now.
- Checked in-game 2026-09-27 on Flatgrass: with the sights 3 units past a brick wall's edge, the old box hit the wall
  5 units away, and a real shot now lands 523 units away. Bots' near misses hit the same hitboxes as before. Not
  checked: a close shot straight into a wall, wallbangs, zombies and the M700.
- Blood and flesh impacts go on the body (2026-10-12, the user: blood on bots "looks like its next to the npc").
  - A near miss's impact went at the box's centre on the line (`EndPosition`), up to 7 units beside the body. Now
    `SceneTraceExtensions.ThroughBody` moves it to where the box touched the body (`HitPosition`).
  - Zombies are hit by their capsule (16 round their middle, well clear of the arms, legs and chest), so their impacts
    were in the air. Code-built zombies now have `ModelHitboxes` on the driver (`SpawnZombie`): a hit on the capsule
    takes the hitbox the line meets, else the nearest within a 32-unit box. The capsule still decides whether it's a
    hit, and only traces that ask for hitboxes see them.
  - A bot's blood moved any point over 32 from its chest to the chest, so leg and foot hits bled from the chest. Only
    a point outside its body (24 round it, from its feet to 80 up) moves now.
  - Compiled offline with dotnet, not yet seen in-game.

