# Zombies power-up drops v2

Created 2026-10-30 as a trial. **Not installed, and parked:** these drops don't appear in a match today, because
`ZombiesRoundSystem.DropPowerUps` defaults to false and nothing sets it. I picked them without checking that, which was a mistake:
the brief was a model players actually see. They had one art pass and are kept in case the drops come back.

## What they are

- **One-Hit Kills** (`powerup_one_hit`): a strapped bundle of seven oversized red-tipped armour-piercing rounds on a steel base.
  Triangles 9,180 / 4,360 / 1,544. A skull would be the obvious sign, and it's a Call of Duty one, so it's not used.
- **Clean Sweep** (`powerup_clean_sweep`): a hand-plunger blasting machine in chipped safety orange, with terminals, a spool of
  firing wire and a red flip cover. Triangles 6,176 / 2,128 / 816.

Each fits the old 15-inch cube about the same origin. One 1024 atlas each, about 23 and 27 px/in. No physics, as before. Lettering is
generic, with no brand, real or game.

## To install, if the drops come back

Set `DropPowerUps` on, and in `ZombiesPowerUp.Spawn` load `models/zombies/powerups_v2/powerup_one_hit.vmdl` and
`powerup_clean_sweep.vmdl` for those two types, dropping their `Tint` and their 0.3 scale. Check the light's radius after that, since it's
on the same object. Run `verify_powerups.py <root> installed`.

## Pipeline

`run.ps1` runs `powerups.py` (build, bake, export) in the background at idle priority, then `paint_powerups.py <work> <materials> <variant>`
paints, `verify_powerups.py <root>` checks the files and `render_powerups.py` renders. Rerunning the build can change the unwrap, so bake and
paint after it.

## Checked and not checked

Checked from the files: LOD 0 of both has 0 pieces inside out, normals, UVs, both inside the old cube, every file named exists, the code doesn't
load them. **Not seen in s&box**, and not compared in a matched sheet, since they were parked after the first look.
