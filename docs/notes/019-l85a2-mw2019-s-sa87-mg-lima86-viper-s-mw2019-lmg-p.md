## L85A2 (MW2019's "SA87", mg_lima86, Viper's MW2019 LMG pack 2960120610)
- The real L85A2 (category AssaultRifle), the British SA80 service rifle, through the Kastov pipeline from MW2019
  (`extracted/2960120610`, decompiled to `decompiled/lima86`). MW2019's SA87 is the L86A2 light support weapon. Built
  with the pack's short barrel, it's the L85A2 rifle, which is what's built. The user asked whether the game had the
  AK-12, HK416, G95, SA80 and AK-15 (2026-10-08), then for the best Workshop models of them, one gun at a time, leaving
  out the G95, whose only model is poor. The SA80 is the first. Its figures are in `kastov_prefabs.gameplay_l85a2`:
  - 690 rpm (the middle of the 610-775 quoted), automatic and semi, from a 30-round magazine.
  - SS109 (L2A2) ball, which is M855: the M4's damage (20), falloff curve and recoil pattern. It leaves the 518 mm
    (20.4-inch) barrel at ~940 m/s, the M16A4's figure from about the same length (G7 0.151). The sights sit 100 mm over
    the bore (the line through the carrying handle's aperture and the front post's tip), zeroed at 300 m like the other
    5.56 rifles.
  - 3.82 kg empty and ~4.7 kg loaded with the iron sights' carrying handle: SpeedPenalty 40, WeightSlowdown 0.0095 and
    0.26 s ADS, by the RPK's scaling. The recoil scale (1.5,3.76) is the M4's (2,5) scaled by free recoil (~1.40
    against 1.86 m/s).
  - A suppressor speeds it up as on the other rifles: its gas regulator has no setting for one (normal, adverse, and
    off for rifle grenades).
  - Reload times are when the gun is level again: 3.53 s, and 4.0 s empty, after the cocking handle. A bullpup's
    magazine is behind the grip, so its reloads are slow.
  - Bots can be issued it: it's a Primary AssaultRifle, so it's in `WeaponPool` and shares the rifles' half.
  - `part_masses.GUN_KG` has it at 4.7.
- Materials and sounds are from `Tools/l85a2_assets.py`:
  - The pack's own receiver (the body, and the front end with its rails), butt plate, carrying handle with its sights,
    short barrel and 30-round magazine. The flash hider and the laser's mount are MW's, from Viper's MW attachment pack
    (Workshop 2459720887).
  - The shot is the pack's one close recording, levelled to the M16A4's: the same round from a barrel of about the same
    length. The suppressed shot is its one suppressed recording. Reload foley plays at the viewmodel QC's event frames.
  - All three are voiced like the other ported guns' (see The ported guns' sounds). The shot keeps its pitch (MW2019's
    5.56, like the AUG's), and its lows under 130 Hz are eased 6 dB after 30 ms, with 3 dB of presence for 25 ms. The
    ground comes 7.1 ms after the direct sound, the muzzle ~0.64 m ahead of the ear. The one recording makes four takes
    with their own echoes, pitch spread 0.97-1.03.
- It was ported with markings on, which `Tools/texture_markings/specs/l85a2.json` takes off (37 regions over 4
  materials):
  - the body's part stamps (L/M, 29630/LM), the selector's R and A, a stock number (1005-88-230-8062), and the rifle's
    name and serials (L1 A834872) on the receiver and the magazine housing;
  - a number in marker (Z-37), another number (3067) and small stamps (8R, R21);
  - the handguard's rail slot numbers (R16, R7, B5, B9);
  - the sights' part number (20846/B) and stamps (R1, 02);
  - a number painted by hand on the magazine, and a smudged mark.
  The magazine's blank follower stays. Checked in before/after close-ups of the textures on 2026-10-08, not yet on the
  model.
- Bodygroups (DefaultMask 85, read from the compiled models):
  - `muzzle_tip`: the flash hider, hidden under a muzzle device.
  - `iron_sights`: the carrying handle with its rear aperture, and the foresight on its bracket. An optic takes both
    off, as on the real gun, where the handle and a sight clamp to the same rail.
  - `laser_rail`: the laser's mount on the handguard's right side, shown only under a laser.
- Slots: Optic on the receiver's top rail (`tag_reflex`), Muzzle at the flash hider's rear face (`tag_tip`) and Laser
  at the back of the mount on the handguard's right side. 48 of the M4's MWII parts are made eligible (optics, muzzle
  devices, lasers and tracer rounds).
  - No Underbarrel slot: the left hand's fingers wrap the bottom rail up to x 15.6 in the viewmodel, and the rail ends
    at 18.0. That leaves 2.1, where the M4's vertical grips need 2.26 (the FAL's case).
  - No parts of its own. Left out: the pack's long and mid barrels (the L86A2's), its bipod, its 60-round magazines and
    CoD's stocks.
- The rig's `tag_brass` was in the handguard, 3 under the bore, so `Weapon.moved_bones` puts it at the real ejection
  port: behind the cocking handle's slot, under its hinged cover.
- The left hand has a `GripFit` (`kastov_weapons.L85A2.left_grip`: shift `0,0.55,-0.55`, fingers 0.4, thumb 0.1). Where
  CoD's hand sits on the handguard, HC1's palm heel and thumb sank 0.39" into its left side and the fingers into the
  bottom rail: 417 vertices. With the fit it's 24 at the hip and 26 aimed, at most 0.10" deep (the verified 762's 54 and
  49 go 0.10"). The fingers still wrap the rail's underside.
- Aimed, it fires with the pack's `fire_2` (`Weapon.ads_fire`, see the pipeline notes): the hip clip rolls the gun 2.5
  degrees about the bore and yaws it 1.2 every shot, and `fire_2` only kicks it 0.24" straight back.
- The iron sights use the addon's own aim (its lua's 1 forward) at ads_in's last frame. Measured from the meshes there, the
  rear aperture's centre and the front post's tip are level with the eye, 3.944 (100 mm) over the bore. Not checked in
  a render or in-game.
- Its `OpticAimCorrection` `-0.004,0,1.047` is derived with the Bizon's formula, NOT checked in-game. Its z is high (the
  Kastovs' are about -1.2), because the carrying handle holds the sight line 2.47 over the rail's `tag_reflex`, as the
  M16A4's does.
- It sprints with the M4's sprint and has the look sway and hand IK (see the pipeline notes).
- The charm hangs on the receiver's left side behind the magazine well. Every hand joint stays 1.9" or more from it
  through every clip (the empty reload's left thumb is nearest); above the magazine well that thumb came within 0.2".
  The sticker is on the upper receiver's left side under the carrying handle.
- Its third-person left hand (`-0.62,1.76,1.33`, see Third-person left hand) hasn't been rendered.
- The models, the animgraph, the materials, sounds and prefabs compiled in the editor on 2026-10-08 with no errors.
  Nothing has been checked in-game. Its gunsmith review note stays until all of it has been checked in a match.

