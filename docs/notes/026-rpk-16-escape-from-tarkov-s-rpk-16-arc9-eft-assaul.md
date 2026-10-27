## RPK-16 (Escape from Tarkov's RPK-16, ARC9 EFT Assault Rifles 2962829818)
- The real Kalashnikov RPK-16 (category LMG) in 5.45x39: Kalashnikov's light machine gun of 2016 on the AK-12's
  receiver, which went to the Russian army's trials in 2018-2019. It's built as it went there:
  - the long barrel (580 mm on the real gun; the pack's model measures ~550) with its muzzle brake, the railed dust
    cover and handguard, and the tangent rear sight clamped to the dust cover's rail;
  - the AK-12's telescoping stock on the RPK-16's own folding tube, the AK-12's pistol grip and the 95-round drum.
- The user asked for guns that look exactly like the real ones, not ones adapted for a game (2026-10-08), so it's
  Tarkov's model, from darsu_eft's ARC9 pack (the c_rpk16 viewmodel, decompiled to `decompiled/rpk16`, and its default
  attachments, to `decompiled/rpk16_atts`). It's on the RPK's CoD rig and clips (MWII's mg_iw9_rkilo, see RPK): an
  RPK's receiver bones sit where the AK-105's do, so the AK-12's fit holds on it. Its figures are in
  `kastov_prefabs.gameplay_rpk16`:
  - 700 rpm, automatic and semi, from the 95-round drum. It starts on automatic.
  - 7N6 at ~950 m/s from the long barrel, between the AK-74M's 900 from 415 mm and the RPK-74's 960 from 590 mm, G7
    0.157. The sights sit 60.3 mm over the bore (the line through the rear sight's aperture and the front post's tip),
    zeroed at 300 m like the AK-12's.
  - The M4's 5.56 damage (20) and falloff, as the AK-12's 5.45 has.
  - 4.5 kg without a magazine (Kalashnikov's figure) and ~6.4 kg with the loaded drum: ~1.9 kg for the drum and its 95
    rounds is an estimate, since no weight is published for it. By the RPK's scaling against the AKM's 3.75 kg that's
    SpeedPenalty 40, WeightSlowdown 0.027 and 0.29 s ADS (`Weapon.ads_time`). `part_masses.GUN_KG` has it at 6.4.
  - The recoil scale (0.94,2.36) is the M4's (2,5) scaled by free recoil: a 7N6 round kicks the loaded gun back at
    ~0.88 m/s, against the loaded M4's 1.86.
  - The RPK's `BarrelHeat`, with 1.4 C a round (a 7N6 round's 1.45 g of powder, where the RPK's PS gives ~1.5). The
    real gun's quick-change barrel isn't modelled.
  - Reload times are the RPK's drum clips': the drum is seated and the gun level at 4.25 s, and 5.05 s after the empty
    reload's bolt pull.
  - Bots can be issued it: it's a Primary LMG, so it's in `WeaponPool` and shares the LMGs' fifth with the RPK. They
    fire it as the RPK's gunner does (`_isMachineGunner`, by category), and LMGs weight them to the Anchor style.
- `Tools/rpk16_rig.py` puts Tarkov's pieces on the RPK's skeleton with `ak12_rig.py`'s tools, and writes them as SMDs
  (`decompiled/rpk16/rig`). Its docstring has every piece.
  - c_rpk16 plays the same ak_anims as c_ak12 and c_ak100, so the AK-12's idle poses it. Its own skeleton is posed as
    the AK-74M's is (`weapon_bones`), which also puts the bolt, selector, trigger and mag catch (left far in front of
    the muzzle by the reference pose) back in the receiver.
  - The pack's default barrel (370 mm) is no real RPK-16's, so it's the pack's long one (`550.smd`). The real short
    barrel is 415 mm.
  - The stock, grip and drum are meshes of their own, so parts take their places, and so are the brake (`muzzle_tip`)
    and the rear sight with its base (`iron_sights`).
  - `muzzle` is an extra bone 0.2 inside the brake's front. It draws the side-on icon `ui/weapons/guns/rpk16_01.png`
    from the model, as for the AK-12.
- Materials and sounds are from `Tools/rpk16_assets.py`, run after `ak74m_assets.py` and `rpk_assets.py`:
  - Tarkov's sheets, built like the AK-12's (no metal, roughness from the phong exponent): the receiver, the long
    barrel, the dust cover, the handguard and its side rails, the rear sight, the brake, the stock tube and the drum.
    The AK-12's stock and grip and the 5.45 rounds keep the AK-12's materials, and the parts keep theirs.
  - The shot is Tarkov's RPK-16: four close starts, each under the last round's tail, mixed at 0 dB. Limited, they're
    -6.2 to -7.1 dB (K-weighted, loudest 100 ms), where the AK-12's are (-6.2 to -6.9): the same 7N6, whose longer
    barrel puts the muzzle further from the ear.
    - Voiced at its own pitch (see The ported guns' sounds): the lows under 130 Hz eased 8 dB after 30 ms, Tarkov's
      tail eased 14 dB from 80 ms (it was 21-22 dB under the blast at 0.2 s and 27-28 at 0.4), 4 dB of presence for
      25 ms (the recordings are dark, 60 Hz their loudest band), the ground at 6.6 ms (the muzzle ~0.87 m ahead of the
      ear, as the FAL's) and the echoes at -31.5 dB.
    - Four takes, pitch 0.98-1.02.
  - The suppressed shot is Tarkov's four suppressed takes under their own tail, 10 dB under the voiced open shot.
  - The draw, holster and reloads are the RPK's events, voiced already: it plays the RPK's clips.
- It was ported with markings on, which `Tools/texture_markings/specs/rpk16.json` takes off (14 regions over 3
  materials):
  - the selector's АВ and ОД (the track's line and the dimple stay), a stamped 183 and the serial on the receiver;
  - a mirrored scrawl inside the dust cover (ЧЕ ТУТ ИЩЕШЬ?, "what are you looking for here?");
  - the rear sight leaf's range numbers 1-8 and the battle setting's П, each copied from the plain leaf, with the
    scale's ticks and line kept.
  `clean.py --check` finds every map as cleaned. Not checked on the model.
- Bodygroups (DefaultMask 135189 by the bit rule, not yet read from the compiled models): `muzzle_tip` (the brake,
  hidden under a muzzle device), `iron_sights` (the rear sight, which an optic takes off: on the real gun both clamp
  to the same rail), `pistol_grip` (8) and `magazine` (5).
- Slots: Optic on the dust cover's rail (-2.2,0,6.111), Muzzle at the brake's rear face (25.247,0,4.351) and Laser at
  the back of the handguard's right side rail (10.97 to 13.1), then Pistol Grip and Magazine. 48 of the M4's MWII
  parts are made eligible (optics, muzzle devices, lasers and tracer rounds).
  - No Underbarrel slot: the left hand's fingers wrap the bottom rail up to x 11.0, and the rail ends at 13.18. That
    leaves 2.18, where the M4's vertical grips need 2.26 (the L85A2's and HK416's case).
- Parts (`PARTS_RPK16`, `Assets/gunsmith/rpk16/`), 11 in all: it takes any AK grip and any AK-74 magazine, as the
  real one does.
  - The AK-74M Pistol Grip and the AK-platform grips (7), the AK-12's parts. Its own AK-12 grip is the factory one.
  - The AK-74M's 6L23 30 and the AK-12's windowed 30, with the RPK's AKM 30 reloads (`reload_variants` `_mag`), level
    again at 2.2 s and 2.6 s empty; the RPK-74 45 and the four-column 60, with the RPK 40's (`_xmag`), 2.3 and 2.8 s.
  - `part_masses.py` has the drum at 0.9 kg (no figure is published: taken as the RPK's 75-round drum's), the 30s at
    0.23 and 0.215, and its grip at 0.09.
- The left hand holds the handguard with the RPK's `GripFit` (`kastov_weapons.RPK16.left_grip`: shift `0,0.38,-0.1`,
  fingers 0.25, thumb 0.1). Measured from the bones with `Tools/grip_fit/measure.js`, not in a render: the nearest
  joint, the pinky's middle, is 0.131 off the handguard at the hip and 0.135 aimed, the index fingertip 0.242 and the
  palm 0.85-1.2. The verified 762's nearest fingertip is 0.118, the RPK's nearest joint 0.189.
- It plays the RPK's fire clip, which doesn't move the gun, so it has no `ads_fire`.
- The iron sights use ads_in's last frame. The RPK's aim left the rear sight's aperture 0.26 over the eye, so
  `kastov_weapons.RPK16.aim` lowers the gun onto the line through the aperture's centre and the hooded front post's tip
  and turns it onto it. Checked in a flat-shaded render of the meshes (the post's tip centred in the aperture, on the
  aim point), not in-game.
- Its `OpticAimCorrection` `3.328,0,-0.971` is the 762's measured correction moved by how far the RPK-16's ADS pose puts
  its optic slot from the 762's, like the AK-12's. NOT checked in-game: tune it with `dev_optic_correction`.
- It sprints with the M4's sprint and has the look sway and hand IK (see the pipeline notes).
- The charm hangs on the folding stock tube's left side behind the receiver: the AKs' spot above the magazine well is
  over the drum, where the empty drum reload's left index finger came within 0.28 of it. Every hand joint stays 1.03"
  or more from it through every clip. The sticker is on the receiver's left side above the drum. Neither has been seen
  on it.
- Its third-person left hand (`6.9,2.5,2.03`, where the first-person hand holds the handguard, by the rules in
  Third-person left hand) hasn't been rendered.
- The editor compiled the models, the animgraph, the materials, sounds, prefabs, the .equip, its parts and the 48
  shared parts on 2026-10-10 with no errors. Nothing has been checked in-game. Its gunsmith review note stays until all
  of it has been checked in a match.

