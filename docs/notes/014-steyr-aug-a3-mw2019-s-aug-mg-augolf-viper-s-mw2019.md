## Steyr AUG A3 (MW2019's AUG, mg_augolf, Viper's MW2019 SMG pack 2802430252)
- The real Steyr AUG A3 (category AssaultRifle) in 5.56x45, through the Kastov pipeline from MW2019
  (`extracted/2802430252`, decompiled to `decompiled/augolf`). The user asked for the AUG with real figures. MW2019's
  AUG is a 9 mm gun until its 5.56 conversion goes in, so it's built as that rifle: the pack's 407 mm (16-inch) barrel
  and the AUG's own 30-round magazine, which reloads with its own clips (`Weapon.factory_reload` `_armag`:
  `reload_armag` and `reload_empty_armag`). Its figures are in `kastov_prefabs.gameplay_aug`:
  - 715 rpm (the middle of Steyr's 680-750), automatic and semi. The real gun's two-stage trigger (semi on the first
    stage, automatic pulled through) isn't modelled: it has HC1's fire-mode switch.
  - The M4's M855 round (damage 20, falloff and recoil pattern) at ~916 m/s from the 16-inch barrel, between the M4's
    905 from 14.5 inches and the M16A4's 945 from 20 (Steyr quotes 970 from its 508 mm barrel), G7 0.151. The sights
    sit 61.7 mm over the bore (the sight line through the flip-up sights on the top rail), zeroed at 300 m like the
    other M855 rifles.
  - 3.3 kg empty, about 3.8 kg loaded: SpeedPenalty 40, no WeightSlowdown, 0.25 s ADS. The recoil scale (1.81,4.53) is
    the M4's (2,5) scaled by free recoil (~1.69 against 1.86 m/s).
  - Reload times are when the left hand is back on the foregrip (the clips' grip-pose events): 1.83 s, and 2.97 s
    empty, after the charging handle.
  - Bots can be issued it: it's a Primary AssaultRifle, so it's in `WeaponPool` and shares the rifles' half.
- CoD's gun is 1.1 times the real one's size: its top rail's slots are 0.433 apart and the rail 0.918 wide, where a
  Picatinny rail's are 0.394 and 0.835 (the P90's and MP7's rails measure that), while its arms are the P90's size.
  `Weapon.model_scale` (1.1) shrinks the whole pose about the camera (the gun, the arms' targets and the meshes), so the
  gun is its real size and the sight picture stays CoD's.
- Its pistol grip is the stock's, so `tag_pistolgrip_attach` is an extra bone on the centreline, as for the P90 and
  MP7A1. A mesh path ending in `@material,material` keeps only the triangles in those materials, and `@!material,...`
  only the rest (`port_kastov.part_triangles`, after any `#bone` filter): the foregrip's mesh carries a second copy of
  it in the rail's material, whose UVs don't fit that texture, and the barrel's pieces have `_s` copies in materials
  that don't exist.
- Materials and sounds are from `Tools/aug_assets.py`: the AUG's own stock (the housing with the pistol grip, trigger
  guard and butt), upper (the top rail and the barrel's collar), sights, foregrip, barrel and magazine, and MW's flash
  hider and laser mount from Viper's MW attachment pack (Workshop 2459720887). The shots are the pack's 5.56 ones (its
  lua's `doCalConversionStats` swaps them in with the 5.56 magazine), levelled to the M16A4's: -1 dB, and -13 dB for
  the suppressed shot, whose peaks ran 9 dB over full scale. Reload foley plays at the viewmodel QC's event frames of
  the 5.56 reloads.
- It was ported with markings on: a CAUTION: Read Manual Before Use warning on the stock, a heart and an arrow under the
  ejection block, the rail's slot numbers (2-28), a serial (S/N 8004-090), CoD's made-up SOLOZERO OPTICS logo and faded
  lettering on the sights, and a SOLOZERO ATTACHMENTS plate on the magazine. `Tools/texture_markings/specs/aug.json`
  takes them off, checked on the textures before and after on 2026-09-28.
- Bodygroups (DefaultMask 85, read from the compiled models):
  - `muzzle_tip`: the flash hider, hidden under a muzzle device.
  - `iron_sights`: the flip-up sights on the top rail, which an optic takes off.
  - `laser_rail`: the laser's mount on the barrel's right side, shown only under a laser.
- Slots: Optic on the top rail (`tag_reflex`), Muzzle at the flash hider's rear face (`tag_tip`) and Laser at the back
  of the mount on the barrel's right side, ahead of the foregrip. 48 of the M4's MWII parts are made eligible (optics,
  muzzle devices, lasers and tracer rounds). No Underbarrel slot: the left hand holds the AUG's own folding foregrip.
- No parts of its own. Left out: the pack's 9 mm barrel and magazines, its long LMG barrel and drum, its rails and its
  three stocks.
- No `GripFit`: the idle left hand sinks 88 vertices into the foregrip, at most 0.50" deep (mean 0.20: the palm, the
  thumb's base and the index knuckle, counted by winding number). Fits that open the fingers took it to 58 vertices
  (0.41") but lifted the fingertips off the grip (0-3 of 490 tip vertices touching it, against 99), and plain shifts
  sank more vertices. None of it shows in the renders from the camera, at the hip or aiming.
- Aimed, it fires with the pack's `fire_2` (`Weapon.ads_fire`, see the pipeline notes): the hip clip rolls it 4.6
  degrees about the bore on the shot's first frame and rocks it +-2.6 for the next five, and `fire_2` rolls it 0.56 at
  most and kicks it 0.94 straight back.
- It has the look sway and hand IK (see the pipeline notes), re-ported on 2026-09-28. Offscreen, with
  `aim_yaw_inertia` held at 120 the gun turns 22 degrees at the hip and about a fifth of that aimed, then settles back
  to rest, and both hands stay within 0.002 of their IK targets.
- Checked in renders only (2026-09-28):
  - the iron sights (ads_in's last frame with the pack's aim, its lua's 3 forward: the front post centred in the rear
    notch), steady aimed fire, the reloads and the sprint;
  - the optics, muzzle devices and lasers on their slots, at the hip and from outside, and aimed, the four optics tried
    (a holographic sight, a magnified scope, a mini red dot and a reflex) centred on the aim point with its
    `OpticAimCorrection` `-0.206,0,-0.69`, which is derived with the Bizon's formula (offscreen, a magnified lens shows
    no picture);
  - the charm on the stock's left side above the magazine, clear of both hands;
  - the world model with parts, and both teams' models holding it (see Third-person left hand).
- None of it has been checked in-game yet.

