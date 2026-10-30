## FN P90 (MW2019's P90, mg_papa90, Viper's MW2019 SMG pack 2802430252)
- The real FN P90 (category SMG) under its real name, through the Kastov pipeline from MW2019 (`extracted/2802430252`,
  decompiled to `decompiled/papa90`). The user asked for another real gun from the CoD packs. Its figures are in
  `kastov_prefabs.gameplay_p90`:
  - 900 rpm (the figure usually quoted; FN's sheet gives 850-1,100), automatic and semi, from the 50-round magazine
    lying along its top.
  - SS190 ball: a 2.0 g bullet at 715 m/s (FN's figure) from the 264 mm barrel. No BC is published for it, so G1 0.155
    is an estimate: the pointed 40 gr V-MAX's form factor at the SS190's sectional density. The sights sit 101 mm over
    the bore (the model's sight line, above the magazine and the top rail), zeroed at 100 m like the other SMGs.
  - Damage, falloff, range, effects, recoil pattern, view punch and move speed are the MP5's, as for the Vityaz. The
    recoil scale (0.29,1.73) is the Vityaz's (0.5,3) scaled by free recoil (~0.64 against ~1.1 m/s).
  - Reload times are when the left hand is back on the grip (the clips' grip-pose events, 2.53 and 2.93 s) and the
    last foley has played: 2.55 s, 3.05 s empty.
  - The real gun throws its cases down through a chute behind the grip (`tag_brass` faces down there), but
    `SpentCasing.Launch` ignores the port's rotation, so that isn't modelled.
- Materials and sounds are from `Tools/p90_assets.py`: the P90's own receiver, rails, barrel and flash hider, iron
  sights and magazine. The magazine's shell is see-through, like the real one's (its vmt's `$translucent`: the colour
  map's alpha is opacity, not a metal mask). A 5.7 mm shot is louder than a 9 mm SMG's and quieter than a 5.45 mm
  carbine's, so the shot is levelled between the Vityaz's and the Kastov-74u's, and the suppressed shot to the other
  SMGs' suppressed shots. Reload foley plays at the viewmodel QC's event frames.
- It was ported with markings on: the plate of CoD's made-up maker FORGE TAC with its address and RESTRICTED LAW
  ENFORCEMENT / GOVERNMENT USE ONLY, the selector's A 1 S, a handwritten 38, the serials (FT098324), cal 5.7x28, the
  sights' maker and part numbers and their R / UP, and the magazine's RESTRICTED line and 50 / 25 / 10 round counts.
  `Tools/texture_markings/specs/p90.json` takes them off, checked in before/after renders on 2026-09-28. The sights'
  arrows and scale lines stay.
- Bodygroups (DefaultMask 21 by the bit rule, not yet read from the compiled model):
  - `muzzle_tip`: the flash hider, hidden under a muzzle device.
  - `iron_sights`: the flip-up sights on the top rail, which an optic takes off.
- Slots: Optic at the back of the top rail (`tag_reflex`), Muzzle at the flash hider's rear face (`tag_tip`) and Laser
  on the right-side rail (`tag_laser_attach`). No Underbarrel slot: the left hand holds the frame's front, which has
  no rail. No parts of its own.
- The M4's MWII parts (optics, muzzle devices, lasers and tracer rounds) fit it through `kastov_prefabs.make_parts_eligible`,
  which adds the P90 to those shared `.gnsmth` files. The prefabs came from a run that left the shared parts alone, so
  on 2026-09-29 it was run on its own for the P90: 27 optics, 17 muzzle devices, 3 lasers and tracers
  (`dev_thumbnails p90` draws 47). Not yet looked at on the gun in a match.
- No `GripFit`. The charm hangs on the stock's left side behind the thumbhole, clear of both hands.
- Aimed, it fires with the addon's `fire_2` (`Weapon.ads_fire`, see the pipeline notes). The user saw it jitter left
  and right when it fired with the hip clip there (2026-09-28). That clip rolls the gun up to 2 degrees about the bore,
  pitches it 1.9 and drops it 0.6" in its first two frames, and at 900 rpm each shot restarts it two frames in (the
  graph and the QC's `snap` both restart it with no blend), so the sights rocked 15 times a second. `fire_2` rolls it
  under 0.2 degrees and pushes it 0.16" straight back. The hip clip is unchanged. The fix compiled, but it hasn't been
  checked in-game yet.
- Checked in renders only: the iron sights (ads_in's last frame with the addon's aim offset, `0,-4,0` in its lua: the
  front post's tip on the aim point, centred between the rear sight's shoulders). Its `OpticAimCorrection`
  `2.596,0,-0.445` is derived with the Bizon's formula, NOT checked in-game; its z is small because the irons stand
  high on the top rail. The parts on its slots and the charm haven't been seen on it. Apart from the user firing it
  (above), none of it has been checked in-game yet.

