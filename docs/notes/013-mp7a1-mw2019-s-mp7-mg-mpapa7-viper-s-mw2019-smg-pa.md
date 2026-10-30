## MP7A1 (MW2019's MP7, mg_mpapa7, Viper's MW2019 SMG pack 2802430252)
- The real H&K MP7A1 (category SMG), through the Kastov pipeline from MW2019 (`extracted/2802430252`, decompiled to
  `decompiled/mpapa7`). The user asked for another real gun from the CoD packs. Its figures are in
  `kastov_prefabs.gameplay_mp7`:
  - 950 rpm (H&K's figure), automatic and semi, from the 40-round magazine in the pistol grip.
  - DM11 ball: a 2.0 g bullet at 720 m/s from the 180 mm barrel, G1 0.145. The sights sit 73.5 mm over the bore (the
    sight line through the flip-up rear sight), zeroed at 100 m like the 9 mm SMGs: the MP7's own zero wasn't found.
  - Damage, falloff, range, effects, recoil pattern, view punch and move speed are the MP5's, as for the Vityaz. The
    recoil scale (0.38,2.3) is the Vityaz's (0.5,3) scaled by free recoil (~0.85 against ~1.1 m/s). DM11's powder
    charge in that sum (~0.4 g) is a guess from the case's capacity.
  - Reload times are when the gun is level again: 2.1 s, 2.17 s empty.
  - Bots can be issued it: it's a Primary SMG, so it's in `WeaponPool` and shares the SMGs' three in ten.
- Materials and sounds are from `Tools/mp7_assets.py`: the MP7's own receiver, barrel, sights, magazine and stock, and
  MW's flash hider and laser mount from Viper's MW attachment pack (Workshop 2459720887). The shot is levelled to the
  P90's (-2 dB). The suppressed shot is a mono 20 ms burst that the limiter holds down: at +4 dB it matches the other
  suppressed guns over 20 ms (-10.4 dB) but is quieter over 100 ms (-15.9 against their -12.1 to -14.8). Reload foley
  plays at the viewmodel QC's event frames.
- It was ported with markings on: the receiver's RESTRICTED MILITARY / GOVERNMENT / LAW ENFORCEMENT USE ONLY labels
  (their plates stay), the selector's semi, AUTO and E, MADE IN USA, 4.6x30mm, the serials, the FSS logos and the FSS
  badge on the grip, the sight's .50 MOA and 56-LP LOW PROFILE / PIN, the stock's part number and FSS logos, and the
  magazine's 30, 4.6x30mm, mould date wheel and the lettering round its feed lips.
  `Tools/texture_markings/specs/mp7.json` takes them off (162 regions over 4 materials), checked in before/after views
  of the textures on 2026-09-28, not yet on the model. The flash hider and the laser mount had none.
- Bodygroups (DefaultMask 85, read from the compiled models):
  - `muzzle_tip`: the flash hider, hidden under a muzzle device.
  - `laser_rail`: the ring mount a laser brings to the top rail's right side, shown only under a laser.
  - `iron_sights`: the raised flip-up sights, which an optic takes off.
- Slots: Optic at the back of the top rail (`tag_reflex`), Muzzle at the flash hider's rear face and Laser at the ring
  mount's back, above the left hand's fingers, which wrap the receiver's own right-side rail. 48 of the M4's MWII
  parts are made eligible (optics, muzzle devices, lasers and tracer rounds).
- No Underbarrel slot: the left hand holds the receiver's front, where a grip would go. CoD's rail there
  (`attachment_vm_sm_mpapa7_ub_rail`) is left out, and so are the pack's grips, the folding foregrip like the real
  gun's included: they move the left hand (`grip_vert_offset`), which a part can't do.
- No parts of its own. Also left out: MW2019's 50- and 60-round magazines (the real gun's go up to 40), its barrels,
  the XRK stock and the Piercer receiver.
- No `GripFit`: the idle left hand sinks 57 vertices, at most 0.10", like the verified 762's.
- Aimed, it fires with the pack's `fire_2` (`Weapon.ads_fire`, see the pipeline notes): the hip clip rolls it 2.3
  degrees about the bore every shot, and `fire_2` only kicks it 0.7" straight back. Compiled, not checked in-game.
- Checked in renders only: the iron sights (ads_in's last frame with the addon's own aim, its lua's 3 forward), the
  optics, muzzle devices and lasers on their slots (from the camera, at the hip and aiming, the lasers sit right of
  the rear sight, below the sight line), and the charm's anchor on the receiver's left side at its rear, clear of both
  hands. Its `OpticAimCorrection`
  `1.375,0,-0.462` is derived with the Bizon's formula, NOT checked in-game. None of it has been checked in-game yet.

