## Colt M16A2 (Escape from Tarkov's M16A2, ARC9 EFT Assault Rifles 2962829818)
- The real Colt M16A2 (category AssaultRifle) in 5.56x45, the US service rifle the Marine Corps adopted in 1983 and the
  Army in 1986, before the flat-top M16A4. It's built as issued, in black and dark grey:
  - the A2 upper with its fixed carry handle and adjustable rear sight, the 20-inch (508 mm) barrel with the front sight
    base on its gas block and the A2 birdcage flash hider, and the round ribbed A2 handguard;
  - the A2 fixed stock and pistol grip, the burst trigger group, the early charging handle and Colt's 30-round
    aluminium magazine.
- The user asked for guns that look exactly like the real ones, not ones adapted for a game (2026-10-08), so it's
  Tarkov's model, from darsu_eft's ARC9 pack (the c_m16 viewmodel, decompiled to `decompiled/m16a2`, and its default
  attachments, to `decompiled/m16a2_atts`). It's on the M16A4's CoD rig and clips (MWII's M16, see M16A4): the same Colt
  rifle on the same lower. Its figures are in `kastov_prefabs.gameplay_m16a2`:
  - Semi-automatic and three-round burst, no automatic, at 800 rpm cyclic (the middle of the 700-900 quoted), from a
    30-round magazine. It starts on semi. The burst is the M16A4's (`BurstAmount` 3, `BurstEndDelay` 0); the real
    burst cam doesn't reset when the trigger is let go, which isn't modelled.
  - M855 at 945 m/s from the 20-inch barrel, G7 0.151, as the M16A4's. The sights sit 67.1 mm over the bore (the line
    through the carry handle's rear aperture and the front post's tip), zeroed at 300 m: the rear sight's 300 m
    setting, the A2's battle zero (FM 3-22.9).
  - The M4's M855 damage (20), falloff curve and recoil pattern.
  - 3.53 kg (7.78 lb) empty and 3.99 kg with a loaded 30 (TM 9-1005-319-10), what the M16A4 weighs: SpeedPenalty 40, no
    WeightSlowdown and 0.25 s ADS. `part_masses.GUN_KG` has it at 3.99. The recoil scale (1.78,4.44) is the M16A4's:
    the same round from the same barrel kicks it back at ~1.65 m/s, against the loaded M4's 1.86.
  - Reload times are the M16A4's clips': the gun is level again at 2.3 s, and 2.4 s after the empty reload's bolt
    release.
  - Bots can be issued it: it's a Primary AssaultRifle, so it's in `WeaponPool` and shares the rifles' half. With no
    automatic, bots fire at most `BurstAmount` rounds a pull with it, as with the M16A4.
- `Tools/m16a2_rig.py` puts Tarkov's pieces on the M16A4's skeleton with `ak12_rig.py`'s tools, and writes them as SMDs
  (`decompiled/m16a2/rig`). Its docstring has every piece.
  - Its SHIFT puts the M16A2's trigger pivot (`weapon_trigger`) on the M16A4's `j_trigger`. Both are Colt's M16 on the
    same lower, so the fire control group, the magazine well and the bore sit where the M16A4's do. The bolt, trigger,
    selector, magazine release, bolt catch, charging handle, stock and magazine ride the M16A4's bones (`BONES`,
    checked against what the M16A4's clips move).
  - The pack's m16a2_atts models are in studiomdl's pre-rotation space, so each is turned 90 degrees (`TURN`) first,
    except the handguard's two halves (`UNTURNED`): they carry the left arm's bones for ARC9's hand IK, and their slot
    turns them itself.
  - The A2 buffer tube and pistol grip come from EFT SHARED (Workshop 2917343547). The rounds' card for see-through
    magazines (`556fakebullets`) is dropped: in the steel-walled USGI magazine it's never seen.
  - The carry handle and the front sight base are part of the receiver (`vm_meshes`), as on the real gun. `muzzle` is an
    extra bone 0.2 inside the flash hider's front.
  - It draws the side-on icon `ui/weapons/guns/m16a2_01.png` from the model, as for the AK-12.
- Materials and sounds are from `Tools/m16a2_assets.py`, run after `m16a2_rig.py` and `m16_assets.py`:
  - Tarkov's sheets, built like the AK-12's (no metal, roughness from the phong exponent): the lower, internals, bolt
    carrier, upper, handguard and its retainer and slip rings, stock, barrel, charging handle, front sight base, gas
    tube, end plate, flash hider and magazine, and the buffer tube, pistol grip and 5.56x45 rounds from EFT SHARED.
  - The shot is Tarkov's M4A1, the pack's only Colt 5.56 recordings (its M16A1 and M16A2 play them too): four outdoor
    close single shots, each with its echo in it. They were made at -7.2 to -8.2 dB (K-weighted, loudest 100 ms), so
    each is lifted through the voicing's soft clipper to the M16A4's -5.4 dB: the same round from the same barrel.
    - Voiced (see The ported guns' sounds): 2% higher, as the M16A4's (a carbine's recording for a 20-inch barrel); the
      lows under 130 Hz eased 8 dB after 30 ms; the recordings' baked-in tail eased 22 dB from 80 ms (it was 13 dB under
      the blast at 0.2 s and 11 at 0.4, the loudest of any rip); 2 dB of presence for 25 ms; the ground at 6.8 ms (the
      muzzle ~0.75 m ahead of the ear, as the M16A4's) and the echoes at -33 dB.
    - Four takes, pitch 0.98-1.02.
  - The suppressed shot is Tarkov's four suppressed M4A1 takes under their own tail, 10 dB under the voiced open shot.
  - The draw, holster and reloads are the M16A4's events, voiced already: it plays the M16A4's clips.
- It was ported with markings on, which `Tools/texture_markings/specs/m16a2.json` takes off (52 regions over 9
  materials):
  - Colt's names and address (COLT'S FIREARMS DIVISION, COLT INDUSTRIES, HARTFORD CONN, U.S.A.), its two logos, the
    serial, CAL. 5.56 MM and M16 A2 on the lower, and the selector's SAFE, SEMI and BURST (an engraved circle stays);
  - on the upper, the rear sight's 0-2, the elevation drum's DN and UP, the range scale's 4-7 (its ticks stay), the
    windage knob's R (its arrow stays), a copyright mark and acceptance stamps;
  - Colt's logo, name and address and CAL. 5.56 MM on the magazine, and DO NOT REMOVE on the handguard (four times);
  - the barrel's C MP CHROME BORE, the front sight's UP (its arrow stays), the bolt's and internals' acceptance stamps
    (their stamped rings stay), and the rounds' PPU 11 and 5.56x45 headstamps.
  Checked in close-ups of the textures on 2026-10-09 (`clean.py --check` finds every map as cleaned), not on the model.
- Bodygroups (DefaultMask 5 by the bit rule, not yet read from the compiled models): `muzzle_tip`, the A2 birdcage,
  hidden under a muzzle device.
- Slots: Muzzle only, at the birdcage's rear face (22.355,0,4.609). 18 of the M4's MWII parts are made eligible (the
  muzzle devices and tracer rounds).
  - No Optic slot: the carry handle is part of the upper, as on the real A2, which took a scope only on a carry-handle
    mount. Its `OpticAimCorrection` is the M16A4's `1.613,0,0.079`, only so the field is set.
  - No Underbarrel or Laser slot: the round handguard has no rails. No parts of its own: the A2 took the USGI 20 and
    30, and the 20 isn't in the pack.
- The rig's `tag_brass` is the M16A4's, 0.43 over the M16A2's ejection port and inside its upper (its bore sits 0.34
  lower on the rig), so `Weapon.moved_bones` puts it in the port (5.85,0.081,0.5; the port runs x 4.3 to 7.4).
- The left hand holds the round handguard through the M16A4's grip pose (`a_delta_grip_barmidhvy_additive_for_offset`).
  No `GripFit`: the pinky's knuckle lies over one of the handguard's vent holes, its bone 0.01 inside the hole's rear
  edge (the M16A4's pinky is 0.03-0.04 off). Every shift tried (0.08 each way, the fingers 8-20% open) left it as deep
  or deeper.
- The fire clip is the M16A4's `steady_fire` (15 frames): only the bolt, trigger and trigger finger move, so it has no
  `ads_fire`.
- The iron sights use ads_in's last frame. With the M16A4's aim the rear aperture's centre and the front post's tip sat
  0.44 under the camera (its bore sits lower on the rig, and the A2's carry handle is lower than the A4's), so
  `kastov_weapons.M16A2.aim` raises the gun onto the line through them and turns it onto it. Measured from the meshes,
  not checked in a render or in-game.
- It sprints with the M4's sprint and has the look sway and hand IK (see the pipeline notes).
- The charm hangs where the M16A4's does, on the lower's left side above the magazine well, and the sticker is on the
  magazine well's flat left side. Neither has been seen on it.
- Its third-person left hand (`5.7,2.23,2.21`, where the first-person hand holds the handguard, by the rules in
  Third-person left hand) hasn't been rendered.
- The editor compiled the models, the animgraph, the materials, sounds, prefabs, the .equip and the 18 shared parts on
  2026-10-09 with no errors. The markings were cleaned after that, with the editor closed: if the textures still show
  Colt's markings, `recompile_asset` its vmats. Nothing has been checked in-game. Its gunsmith review note stays until
  all of it has been checked in a match.

