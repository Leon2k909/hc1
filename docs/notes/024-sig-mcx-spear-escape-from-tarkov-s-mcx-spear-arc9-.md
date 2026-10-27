## SIG MCX-SPEAR (Escape from Tarkov's MCX-SPEAR, ARC9 EFT Assault Rifles 2962829818)
- The real SIG Sauer MCX-SPEAR (category AssaultRifle) in 6.8x51 (.277 Fury), the rifle the US Army adopted as the M7.
  It's built as the M7 and SIG's own SPEAR come, in coyote tan:
  - the 330 mm (13-inch) barrel with the Clutch-LOK QD flash hider, the adjustable gas piston, the M-LOK handguard with
    its full-length top rail, SIG's flip-up sights and the side charging handle;
  - SIG's locking hinge and low-profile tube with a Magpul MOE SL-K stock, SIG's reduced-angle pistol grip, and
    Lancer's L7 AWM 20-round magazine.
- The user asked for guns that look exactly like the real ones, not ones adapted for a game (2026-10-08), so it's
  Tarkov's model, from darsu_eft's ARC9 pack (the c_spear viewmodel, decompiled to `decompiled/spear`, and its default
  attachments, to `decompiled/spear_atts`). It's on the MCX Virtus's CoD rig and clips (MW2019's M13, see SIG MCX
  Virtus): both are SIG's short-stroke piston MCX family on AR-15-pattern lowers. Its figures are in
  `kastov_prefabs.gameplay_spear`:
  - 850 rpm, automatic and semi, from a 20-round magazine. It starts on automatic.
  - 135 gr ball at ~915 m/s from the 13-inch barrel, G1 0.488. The sights sit 85 mm over the bore (the line through the
    rear aperture's centre and the front post's tip), zeroed at 300 m like the other rifles.
  - BaseDamage 44, the M4's 20 scaled by muzzle energy (3,663 J against M855's 1,646), so in hardcore a body hit at full
    damage always kills, as with the FAL's M80. Falloff, range, recoil pattern, view punch, casing and flash are the
    M4's.
  - 3.8 kg (8.38 lb) without a magazine, ~4.35 kg with a loaded Lancer 20 (0.17 kg, and 20 rounds of ~19.4 g): 0.6 kg
    over the AKM, so SpeedPenalty 40, WeightSlowdown 0.006 and 0.26 s ADS, by the RPK's scaling. `part_masses.GUN_KG`
    has it at 4.35.
  - The recoil scale (3.28,8.2) is the M4's (2,5) scaled by free recoil: a 6.8x51 round (8.75 g at 915 m/s, ~3.3 g of
    powder) kicks it back at ~3.05 m/s, against the M4's 1.86.
  - A suppressor doesn't change its rate (`SuppressorFireRateScale` 1): its adjustable gas valve has a suppressed
    setting, and the M7 is issued with a suppressor.
  - Reload times are the MCX's clips': the gun is level again at 2.33 s, and 2.6 s after the empty reload's bolt
    release.
  - Bots can be issued it: it's a Primary AssaultRifle, so it's in `WeaponPool` and shares the rifles' half.
- `Tools/spear_rig.py` puts Tarkov's pieces on the MCX's skeleton with `ak12_rig.py`'s tools (its `Rig` now takes another
  gun's receiver, idle clip, fit, bone map and dropped materials), and writes them as SMDs (`decompiled/spear/rig`). Its
  docstring has every piece.
  - Its SHIFT puts the SPEAR's trigger pivot on the MCX's `j_trigger`. Both have AR-15-pattern fire controls and
    magazine wells, so the bolt, trigger, selector, bolt release, magazine release, charging handle and magazine ride
    the MCX's bones (`BONES`, checked against what the MCX's clips move). The bore sits 0.32 under the MCX's.
  - The pack's spear_atts models are in studiomdl's pre-rotation space, so each is turned 90 degrees (`TURN`) first.
  - SIG's flip-up sights come from EFT SHARED (Workshop 2917343547): the pack's own build leaves them off for its
    scope. The pack's suppressor, scope and mount are left out.
  - The grip is part of the receiver (`vm_meshes`): SIG's reduced-angle grip is the only one offered. `muzzle` is an
    extra bone 0.2 inside the flash hider's front, and `tag_pistolgrip_attach` is the MCX's.
  - It draws the side-on icon `ui/weapons/guns/spear_01.png` from the model, as for the AK-12.
- Materials and sounds are from `Tools/spear_assets.py`, run after `spear_rig.py` and `mcx_assets.py`:
  - Tarkov's sheets, built like the AK-12's (no metal, roughness from the phong exponent), in the pack's coyote tan:
    the lower, the upper and its details, the internals, barrel, gas piston, charging handle, handguard and flash
    hider, the stock's hinge, tube and MOE SL-K, the grip, both magazines and the 6.8x51 rounds, and SIG's sights from
    EFT SHARED.
  - The shot is Tarkov's MCX-SPEAR: four close starts, each under the last round's tail. Mixed and limited, they were
    -7.0 to -7.4 dB (K-weighted, loudest 100 ms), under the M16A4's -5.4. 6.8x51 runs at ~80,000 psi against 5.56's and
    7.62x39's 52-55,000, from a 13-inch barrel, so each take is lifted through the voicing's soft clipper to -4.8 dB.
    - Voiced at its own pitch (see The ported guns' sounds): the lows under 130 Hz eased 8 dB after 30 ms, Tarkov's
      tail eased 16 dB from 80 ms (it was 15 dB under the blast at 0.2 s and 21 at 0.4 s, 12 dB over the voiced
      rifles'), 4 dB of presence for 25 ms (the recordings are dark), the ground at 7.1 ms (the muzzle ~0.65 m ahead
      of the ear, stock extended) and the echoes at -33 dB.
    - Four takes, pitch 0.98-1.02.
  - The suppressed shot is Tarkov's four suppressed takes under their own tail, 10 dB under the voiced open shot.
  - The draw, holster and reloads are the MCX's events, voiced already: it plays the MCX's clips.
- It was ported with markings on, which `Tools/texture_markings/specs/spear.json` takes off (53 regions over 15
  materials):
  - SIG's logos (on the lower, the sights' discs, the grip and the internals), SIG SAUER INC / NEWINGTON / NH USA, the
    serial, the model's name and MULTI-CALIBER, and a torque figure;
  - Lancer's L7-AWM, its maker's block and CAGE code, the calibre (7.62 X 51), the round counts, mould numbers and a
    date wheel on both magazines (the boxed counts and the calibre's recessed plate stay);
  - the gas valve's ADVERSE and NORMAL (their arrows stay);
  - Magpul's MOE SL-K name and logos, and the stock label's part number and web address (the label's edges stay);
  - the rounds' headstamp, the flash hider's 6.8 and its thread (5/8-24), and faint stamps on the gas block, barrel and
    hinge.
  `clean.py --check` finds every map as cleaned. Not checked on the model.
- Bodygroups (DefaultMask 341 by the bit rule, not yet read from the compiled models):
  - `muzzle_tip`: the flash hider, hidden under a muzzle device.
  - `iron_sights` and `sight_folded`: the flip-up sights raised, and folded down under an optic.
  - `magazine`: the factory 20 and the 25 below.
- Slots:
  - Optic on the upper's top rail (`tag_reflex`, -2.71,0,6.696; an optic folds the sights).
  - Muzzle at the flash hider's rear face (15.337,0,4.82).
  - Underbarrel on the handguard's flat bottom, which runs 5.75 to 14.5. Its origin is at 12.4, so the M4's vertical
    grips end 0.1 inside the handguard's front, clear of the index finger.
  - Laser on the handguard's right side at the bore's height (9.5,-0.926,4.82), ahead of the fingertips.
  - Then Magazine. 56 of the M4's MWII parts are made eligible (optics, muzzle devices, grips, lasers and tracer
    rounds).
- Its own part (`Prefabs.parts`, `Assets/gunsmith/spear/magazines/`): Lancer's L7 AWM 25, the longer of the two
  magazines SIG ships the SPEAR with in the US. It uses the factory reload: it's only an inch longer. `part_masses.py`
  has the factory 20 at 0.17 kg and the 25 at 0.19.
- The rig's `tag_brass` is the MCX's, 0.5 behind the middle of the SPEAR's longer ejection port and inside the
  receiver, so `Weapon.moved_bones` puts it at the port's middle (the port runs x 4.7 to 8.0).
- The left hand has the MCX's `GripFit` with the fingers 3% open (`kastov_weapons.SPEAR.left_grip`: shift
  `0,-0.05,0.15`, fingers 0.03, thumb 0.2).
  - The handguard is wider than the MCX's, and with the MCX's fit alone the pinky's tip came within 0.05-0.07 of it.
  - Now the nearest joint, the pinky's middle, is 0.148 off at the hip and aiming, the middle fingertip 0.25-0.27 and
    the palm 0.49. The verified 762's nearest fingertip is 0.118.
  - Measured from the bones with `Tools/grip_fit/measure.js`, not seen in a render.
- Aimed, it fires with the MCX's `fire_2` (`Weapon.ads_fire`, see the pipeline notes): the hip clip rolls the gun up to
  2.5 degrees about the bore every shot, and `fire_2` only kicks it back.
- The iron sights use ads_in's last frame. With the MCX's aim the rear aperture's centre sat 0.371 above the camera
  (the SPEAR's sights stand higher over its bore), so `kastov_weapons.SPEAR.aim` lowers the gun onto the line through
  the aperture's centre and the post's tip and turns it onto it (within 0.001 degrees). Measured from the meshes, not
  checked in a render or in-game.
- Its `OpticAimCorrection` `3.118,0,0.052` is the 762's measured correction moved by how far the SPEAR's ADS pose puts
  its optic slot from the 762's, like the MCX's. NOT checked in-game: tune it with `dev_optic_correction`.
- It sprints with the M4's sprint and has the look sway and hand IK (see the pipeline notes).
- The charm hangs where the MCX's does, on the stock's hinge block by the QD sling sockets. It plays the MCX's clips, so
  the hands keep the MCX's 1.07" or more from it. The sticker is on the magazine well's left side. Neither has been
  seen on it.
- Its third-person left hand (`4.2,2.574,2.702`, see Third-person left hand) hasn't been rendered.
- Made on 2026-10-09 with the editor closed: only its sounds are compiled. The models, the animgraph, the materials,
  the prefabs, the .equip, its part and the 56 shared parts aren't.
  - If the first-person gun is invisible or keeps old clips, register its DMX and recompile `v_spear.vmdl` and
    `v_spear.vanmgrph` (see the pipeline notes).
  - If the gunsmith doesn't offer the shared parts, `recompile_asset` them.
  - Nothing has been checked in-game. Its gunsmith review note stays until all of it has been checked in a match.

