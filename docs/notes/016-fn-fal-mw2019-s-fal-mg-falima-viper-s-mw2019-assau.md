## FN FAL (MW2019's FAL, mg_falima, Viper's MW2019 Assault Rifles pack 2528829149)
- The real FN FAL 50.00 (category AssaultRifle) in 7.62x51, through the Kastov pipeline from MW2019
  (`extracted/2528829149`, decompiled to `decompiled/falima`). The user asked for another real gun from the packs, and
  for the UI to say it still needs checking (the review note, see Gunsmith). The model is the real gun's size: 42.9 in
  from the butt to the muzzle, the real 50.00's 1,090 mm. Its figures are in `kastov_prefabs.gameplay_fal`:
  - 675 rpm (the middle of FN's 650-700), semi and automatic, starting on semi as armies fired it, from a 20-round
    magazine.
  - M80 ball at 840 m/s from the 533 mm (21-inch) barrel, G7 0.200 like the SCAR-H's. The sights sit 48.6 mm over the
    bore (the sight line through the rear aperture and the front post's tip), zeroed at 200 m: the rear sight's lowest
    setting, the battle zero.
  - BaseDamage 41, the M4's 20 scaled by muzzle energy (3,362 J against M855's 1,646), so in hardcore a body hit at full
    damage always kills. Falloff, recoil pattern and view punch are the M4's, as the SCAR-H's are, and the muzzle flash
    is the SCAR-H's.
  - About 5.0 kg loaded (4.25 kg empty), 1.25 kg over the AKM: SpeedPenalty 40, WeightSlowdown 0.0125 and 0.27 s ADS, by
    the RPK's scaling. The recoil scale (2.66,6.66) is the M4's (2,5) scaled by free recoil (~2.48 against 1.86 m/s).
  - Reload times are when the gun is level again: 2.67 s, and 3.4 s empty, after the charging handle.
  - Bots can be issued it: it's a Primary AssaultRifle, so it's in `WeaponPool` and shares the rifles' half. It has
    automatic, so they fire their usual 3-7 round strings with it.
- Like the P90's, its rig has no pistol grip part (the grip is the receiver's), so `tag_pistolgrip_attach` is an extra
  bone on the centreline.
- Materials and sounds are from `Tools/fal_assets.py`: the FAL's own receiver (with the carrying handle, pistol grip and
  optic rail), rear sight, handguard, barrel and flash hider, magazine and stock, the parts' own (the Para stock, the
  18-inch barrel and the 30-round magazine), and MW's laser mount and the 18-inch barrel's short flash hider from
  Viper's MW attachment pack (Workshop 2459720887). The 30-round magazine's reload foley plays at its own clips' frames. The shot is the pack's six dry recordings, levelled to one loudness (+8 dB), so
  every shot sounds a little different: 0.7-1 dB over the 5.56 rifles' (the M16A4's, AUG's and AK-105's), as a .308 is
  at the shooter, and under the SCAR-H's. The suppressed shot is the pack's six suppressed recordings at -12 dB, about
  as far over the 5.56 rifles' suppressed shots. Reload foley plays at the viewmodel QC's event frames.
- It was ported with markings on: serials (6822), proof marks, rack numbers, the selector's S and F, and the rear
  sight's range numbers and stamps, and on the Para stock a proof mark and a serial (SN-750404).
  `Tools/texture_markings/specs/fal.json` takes them off (23 regions over 5 materials).
- Bodygroups (DefaultMask 174761, read from the compiled models):
  - `muzzle_tip`: the flash hider, then the 18-inch Barrel's short one, then none (under a muzzle device, which the
    Muzzle slot's `FittedBodygroups` sets to 2).
  - `optic_rail`: the rail an optic brings onto the top cover, shown only under an optic.
  - `laser_rail`: the laser's mount on the handguard's right side, shown only under a laser.
  - `iron_sights` and `sight_folded`: the rear sight raised, and folded down under an optic.
  - `stock`, `barrel` and `magazine`: the factory parts and the ones below.
- Slots: Optic on the top cover's rail (`tag_reflex`), Muzzle at the flash hider's rear face (`tag_tip`) and Laser at
  the back of the mount on the handguard's right side (`tag_laser_attach` is its front), then Stock, Barrel and
  Magazine. 48 of the M4's MWII parts are made eligible (optics, muzzle devices, lasers and tracer rounds). No
  Underbarrel slot: the left hand holds the handguard, whose short bottom rail its fingers wrap.
- Its own parts (`Prefabs.parts` in its `kastov_prefabs` entry, `Assets/gunsmith/fal/`), from the pack. The user asked
  for more than its four slots (2026-09-28):
  - Para Folding Stock: the FAL Para's tubular folding stock, with a thin buttplate. 5% more recoil.
  - 18-inch Barrel: the 50.62's 458 mm barrel with its short flash hider. M80 leaves it at ~817 m/s against 840, 0.946
    of the energy, so damage falls off 5% earlier. A muzzle device mounts 2.1 further back (`muzzle_shift`), and with
    none the shots leave the short hider's end, 5.9 behind the factory one's (`tip_shift`, see the pipeline notes).
  - 30 Round Mag: the heavy-barrel squad rifle's (the FALO's), with the pack's xmag reloads (`reload_variants`
    `_xmag`). The gun is level again at 2.67 s, and 3.57 s empty. Mid-reload the new magazine is in the left hand while
    the old one is still angled in the magwell: the factory reload does the same, so it's the pack's clips.
  - Left out:
    - The pack's long barrel: ~575 mm, which no service FAL had (533, the L1A1's 554, 458 and 436).
    - Its loose muzzle piece, which the pack never fits, and its 24-round magazine, which no real FAL had.
    - The stockless receiver, MW's own stocks (CoD designs), and the FAL's grips: they move the left hand, and there's
      no Underbarrel slot.
  - `hc1_fal_parts_check [world] [variant] [pose] [cycle] [view]` (`Editor/Hc1FalGunsmithQa.cs`) checks them
    offscreen and renders them to `output/fal-gunsmith/`:
    - the masks;
    - each part's values and effects;
    - `muzzle_tip` and the discharge shift for each barrel, with and without a suppressor.
- No `GripFit`: the idle left hand has 121 vertices inside the handguard, at most 0.09" deep (the verified 762's 52 go
  0.10"), and 124 (0.08") aimed. The right hand's thumb base sinks up to 0.54" into the pistol grip (223 vertices; the
  762's go 0.37"), but at the default 85-degree view only 8 of them are on screen at the hip and 5 aimed, inside the gun
  at the screen's bottom edge.
- Aimed, it fires with the pack's `fire_2` (`Weapon.ads_fire`, see the pipeline notes): the hip clip rolls the gun up to
  3 degrees about the bore and swings it 1" forward every shot, and `fire_2` rolls it 0.25 at most and kicks it 0.6"
  straight back.
- The charm hangs on the stock's left side, near its front (`Prefabs.charm`), not on the receiver like the Kastovs'.
  The empty reload's left hand racks the charging handle (on the receiver's left, where the AK's is on the right) along
  the whole receiver, and its thumb went through a charm there, while above the trigger guard the disk rested on the
  right thumb. On the stock every hand joint stays over 2" from its bounds through both reloads, the sprint and aiming
  (the 762's left thumb comes within 0.49" of its charm's). It's out of view at the hip and aimed.
- Its `OpticAimCorrection` `2.402,0,-1.066` is derived with the Bizon's formula, NOT checked in-game. Offscreen, a
  holographic sight's and a mini red dot's dots land where they do on the 762 with its in-game-measured correction
  (0.371 against 0.372 degrees under the screen's centre, and 0.189 against 0.190).
- It has the look sway and hand IK (see the pipeline notes).
- The first compile of `v_fal.vmdl` left no compiled file, so the editor loaded an error model and the first-person gun
  was invisible until the vmdl and vanmgrph were recompiled (see the pipeline notes).
- Checked offscreen on 2026-09-28, in renders and measurements of the compiled models:
  - the iron sights (ads_in's last frame, with no aim offset: the pack's lua has none): the front post centred in the
    rear aperture;
  - aimed fire: 0.54" straight back and 0.28 degrees of pitch;
  - both reloads within 4 degrees and 0.6" of rest at their reload times, and at rest 1 s later;
  - the M4's sprint, with the left hand on its grip;
  - a hard flick: 12.83 degrees at the hip and 2.57 aimed, the hands within 0.009" of their grips, back at rest 2 s
    later;
  - the parts on their slots at the hip, aimed and from outside (a magnified lens shows no picture offscreen);
  - the charm on the viewmodel and the world model;
  - both teams' models holding it (see Third-person left hand);
  - its own three parts (`hc1_fal_parts_check`): on the world model, a suppressor seated on the 18-inch Barrel, the
    charm's hook on the Para stock's upper tube, and the 30 Round Mag's reloads in first person.
- Its gunsmith review note stays until all of it has been checked in a match: the iron sights and the optics' aim,
  recoil, reload timing and sounds (the 30 Round Mag's too), the look sway and sprint, the left hand in first and third
  person, and the 18-inch Barrel's muzzle flash and devices. None of it has been checked in-game yet.

