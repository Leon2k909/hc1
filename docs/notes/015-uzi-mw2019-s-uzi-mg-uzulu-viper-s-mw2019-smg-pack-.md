## Uzi (MW2019's Uzi, mg_uzulu, Viper's MW2019 SMG pack 2802430252)
- The real IMI Uzi (category SMG), through the Kastov pipeline from MW2019 (`extracted/2802430252`, decompiled to
  `decompiled/uzulu`). The user asked for it with real figures, like the other guns. The model is the real gun's size:
  435 mm from the receiver's back to the muzzle, where the real gun's is 445 without a stock. Its figures are in
  `kastov_prefabs.gameplay_uzi`:
  - 600 rpm cyclic from the open bolt, automatic and semi, from the 32-round magazine in the pistol grip.
  - 9x19 ball at 400 m/s from the 260 mm barrel, modelled as 124 gr ball (G1 0.145) like the Vityaz's. The sights sit
    47 mm over the bore (the model's sight line from the rear aperture to the front post's tip, 309 mm apart like the
    real gun's), zeroed at 100 m: the flip rear sight's 100 m aperture.
  - Damage, falloff, range, effects, recoil pattern and view punch are the MP5's, as for the Vityaz. The recoil scale
    (0.38,2.26) is the Vityaz's (0.5,3) scaled by free recoil (~0.83 against ~1.1 m/s).
  - It's heavy for its size: 3.5-3.7 kg empty with the metal stock (sources differ), ~4.2 kg loaded, more than the M4.
    So it moves like the rifles (SpeedPenalty 40, not the MP5's) and aims in their 0.25 s. It's too little over the
    AKM's 3.75 kg for a WeightSlowdown.
  - Reload times are when the gun is level again: 2.53 s, and 3.23 s empty (after the cocking knob pull). The clips'
    grip-pose events come earlier, at 2.3 and 2.97 s, with the gun still tilted 12 and 27 degrees.
  - Bots can be issued it: it's a Primary SMG, so it's in `WeaponPool` and shares the SMGs' three in ten.
- The viewmodel's receiver model has every piece twice, the second copy in an `_s` material, so its `vm_meshes` path
  leaves those out (`@!material,material`, `port_kastov.part_triangles`).
- Materials and sounds are from `Tools/uzi_assets.py`: the Uzi's own receiver, barrel, sights, top rail, magazines and
  stocks, and MW's laser mount from Viper's MW attachment pack (Workshop 2459720887). The shot is levelled to the
  Vityaz's (-5 dB). The suppressed shot peaks 7 dB over full scale, which the limiter holds down: at +2 dB it matches
  the Vityaz's over 20 ms (-8.9 against -8.8 dB) and is a little quieter over 100 ms (-13.5 against -12.9). Reload
  foley plays at the viewmodel QC's event frames.
- It was ported with markings on: CoD's made-up maker CRONEN IND. with MODEL A and 9 mm PARA (on the receiver and the
  barrel), the serials and engraved letters, the selector's A / F / S, the rear sight's range numbers, CORVUS DEFENSE
  and an SMG serial on the top rail, the made-up XRK logo on the 40- and 50-round magazines, and a rack number carved
  into the wooden stock. `Tools/texture_markings/specs/uzi.json` takes them off (20 regions over 8 materials), checked
  in before/after renders on 2026-09-28. The selector's three position lines stay.
- Bodygroups (DefaultMask 1173, read from the compiled models):
  - `optic_rail`: the claw mount an optic brings onto the top cover, shown only under an optic.
  - `laser_rail`: the ring mount a laser brings to the receiver's front, on its right side, shown only under a laser.
  - `stock` and `magazine`: the factory parts and the ones below.
  - The iron sights have no bodygroup and stay under an optic, which the claw mount holds above them.
- Slots: Optic at the back of the claw mount (`tag_reflex`), Muzzle at the barrel's front face and Laser at the back
  of the ring mount (`tag_laser_attach` is its front). 48 of the M4's MWII parts are made eligible (optics, muzzle
  devices, lasers and tracer rounds). No Underbarrel slot: the left hand holds the lower receiver's front, and the
  pack's grips move it (a part can't).
- Parts (`PARTS_UZI`, `Assets/gunsmith/uzi/`), with recoil relative to the factory folding metal stock, extended:
  - The Folded Stock: folded under the receiver, 40% more recoil.
  - The Wooden Stock: the early fixed wooden stock, with the 74u's Wooden Stock part's name, text and 0.9 recoil.
  - The 40- and 50-round magazines. They reload with the pack's xmag clips (`reload_variants` `_xmag`), which level
    the gun at the same times as the factory 32's.
  - Left out: CoD's barrels, its suppressed barrel and calibre conversion, and the MW grips and stocks.
- The fire clip is `Weapon.steady_fire` (8 frames), as for the M16A4. The pack's clip rolls the gun up to 1.5 degrees
  about the bore and pitches it 0.9 in its first three frames, and at 600 rpm every shot starts it again. Its aimed
  clip (`fire_2`) still rolls it 0.95, so the Uzi doesn't take `ads_fire`. In the exported clip the camera, the gun and
  both wrists hold still; only the bolt (seen through the ejection port), the trigger finger and the thumb move. The
  cocking knob on the top cover stays put, as on the real gun.
- `Weapon.left_grip` is a `GripFit` (shift `0,0.25,-0.1`, fingers 0.1). Where CoD's hand sits on the lower receiver's
  front, HC1's thumb base sank 0.34" into its left side, the palm into its bottom and the fingertips into its right
  side: 154 vertices. With the fit it's 60, at most 0.10" deep (the verified 762's 52 go 0.10").
- Its `OpticAimCorrection` `0.241,0,-1.747` is derived with the Bizon's formula, NOT checked in-game. Its z is lower
  than the Kastovs' (about -1.2): at the ADS pose the claw mount holds an optic's base 0.32 over the iron sight line,
  where the 762's rail is 0.22 under its own.
- It sways like the other ported guns (see the pipeline notes). Checked offscreen the same way on 2026-09-28: a hard
  flick turns it 12.79 degrees at the hip and 2.56 aimed, with both hands within 0.010" of their grips.
- Checked in renders only:
  - The iron sights (ads_in's last frame with the pack's own aim, its lua's 3 forward).
  - Six optics on the claw mount, from the side and through them aiming: the fixed rear sight stays at least 0.29
    under each, and their windows are clear of it.
- Magnified optics at the hip (2026-10-05): the claw mount holds every optic higher than the rifles' rails, so at the
  hip its eyepiece is 0.2-0.8" above eye level (from idle.dmx's first frame: the 6x Precision Scope's 5.95" ahead, 2.48"
  right and 0.51" up; the Kastov 762's 0.19" below). The 6x scopes fill the top right of the screen there. The user
  saw it ("looks weird on the uzi"), was offered taking them off the Uzi or holding it lower at the hip with a
  magnified optic, and chose to leave it as it is.
- Not seen on it yet: the muzzle devices and lasers on their slots, the charm (at the back of the receiver's left
  side) and the third-person hand. None of it has been checked in-game yet.

