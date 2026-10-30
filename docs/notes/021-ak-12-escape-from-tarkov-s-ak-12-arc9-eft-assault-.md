## AK-12 (Escape from Tarkov's AK-12, ARC9 EFT Assault Rifles 2962829818)
- The real Kalashnikov AK-12 (6P70, category AssaultRifle) in 5.45x39, the 2018-2022 production rifle. It's the third
  of the user's list, after the L85A2 and the HK416 (see L85A2). The model is Tarkov's, from darsu_eft's ARC9 pack
  (`extracted/2962829818`, decompiled to `decompiled/ak12`), on the AK-105's CoD rig and clips. Its figures are in
  `kastov_prefabs.gameplay_ak12`, from Rosoboronexport's catalogue:
  - 700 rpm, with the 2018-2022 rifles' selector: automatic, a two-round burst and semi (the 2023 model dropped the
    burst). It starts on automatic. The burst is the M16A4's (`BurstAmount` 2, `BurstEndDelay` 0): a pull fires both
    rounds, and letting go doesn't cut it short. It has automatic, so bots fire their usual strings with it.
  - 7N6 at 900 m/s from the 415 mm barrel, as from the AK-74M's, G7 0.157. The sights sit 55.3 mm over the bore (the
    eye's height over it at the ADS pose, through the diopter's aperture), zeroed at 300 m like the AK-105.
  - The M4's 5.56 damage (20) and falloff, as the AK-105's 5.45 has.
  - 3.5 kg without a magazine, ~4.0 kg with a loaded 30: the M16A4's weight, too little over the AKM's 3.75 kg for a
    WeightSlowdown. So SpeedPenalty 40 and 0.25 s ADS. The recoil scale (1.43,3.58) is the M4's (2,5) scaled by free
    recoil (~1.33 against 1.86 m/s).
  - Reload times are the AK-105's clips': the gun is level again at 2.3 s, and 2.6 s after the empty reload's bolt pull.
  - Bots can be issued it: it's a Primary AssaultRifle, so it's in `WeaponPool` and shares the rifles' half.
- `Tools/ak12_rig.py` puts Tarkov's pieces on the AK-105's skeleton as ARC9 draws them, and writes them as SMDs
  (`decompiled/ak12/rig`):
  - the receiver with the 415 mm barrel, the gas block's front sight, the railed dust cover and handguard and the
    folding, telescoping stock, then the muzzle brake (`muzzle_tip`), the diopter rear sight (`iron_sights`), the grip
    and the windowed magazine;
  - the bolt carrier on `j_boltcarrier`, the trigger on `j_trigger`, the selector on `j_fireselect`, the mag catch on
    `j_magrelease` and the magazine with its top rounds on `j_mag1` / `j_mag2`. The real gun's magazine well, trigger
    group, selector and catch are the AK-74M's, so they fit the AK-105's to within 0.08.
  - `muzzle` is an extra bone, 0.2 inside the brake's front.
  - The pack's icon is a three-quarter render, so the script draws the side-on `ui/weapons/guns/ak12_01.png` from the
    model.
- Materials and sounds are from `Tools/ak12_assets.py`:
  - Tarkov's sheets are Source VertexLitGeneric (colour, normal, phong exponent), built like the HK416's Tarkov parts:
    no metal, roughness from the exponent.
  - The magazine's window points at a glass texture the pack doesn't ship, so it's a flat smoked translucent polymer.
    The rounds seen through it are a stack drawn on an alpha-tested card, greened towards Russian lacquered steel cases
    like the loose rounds.
  - The AK-105's magazines and the AK grips, which it takes as parts, keep the AK-105's and 74u's materials.
  - The shot: Tarkov plays one shot as one of four 81 ms starts (`_loop1-4`) under the last round's tail (`_loopt`),
    so each take is the two mixed, levelled to the AK-105's (the same 7N6). Voiced (see The ported guns' sounds) at its
    own pitch, with the lows under 130 Hz eased 8 dB after 30 ms, Tarkov's tail eased 14 dB from 80 ms (it was 23 dB
    under the blast at 0.4 s, where the voiced rifles' are 33), 3 dB of presence for 25 ms, the ground at 6.9 ms (the
    muzzle ~0.73 m ahead of the ear) and the echoes at -33 dB. Four takes, pitch 0.98-1.02.
  - The suppressed shot is Tarkov's three suppressed takes, built the same way, 10 dB under the voiced open shot.
  - Reload foley: the AK-105's moves, and Tarkov's AK-74 recordings for the AK-12's own parts. The charging handle goes
    back and home, and the mag catch, the magazine coming out and going in (split into the front lug catching and the
    catch locking) each sound on the frame the AK-105's clip moves that part. Voiced as one set, so the magazine's clicks
    stay ~9 dB under the bolt.
- It was ported with markings on, which `Tools/texture_markings/specs/ak12.json` takes off (8 materials):
  - the receiver's selector markings (АВ, 2, ОД; the track's line and detents stay), the index and calibre (6П70,
    5.45x39), a serial and small stamps;
  - the magazine's round counts (10 to 30, on both sides) and its moulded maker's mark;
  - a mould number on the grip, the stock tube's position numbers 1-4 (the holes stay), the calibre on the rear sight's
    base, the bolt's acceptance stamps and serial, and the rounds' headstamps;
  - the rear sight leaf's range numbers 1-8 and the battle setting's П, each copied from the plain leaf above them. The
    scale's ticks and the leaf's groove rims are `keep` regions, out of the patches' borders. The 1 and 5 patches are a
    little smoother than the leaf round them.
  Checked in the tool's previews of each patch on 2026-10-08, not on the model.
- Bodygroups (DefaultMask 135189 by the bit rule, not yet read from the compiled models): `muzzle_tip` (the brake,
  hidden under a muzzle device), `iron_sights` (the diopter, which an optic takes off: on the real gun it slides off
  the same rail), `pistol_grip` and `magazine` (the factory parts and the ones below).
- Slots: Optic on the dust cover's rail (-4.5 to 4.0), Muzzle at the brake's rear face, Underbarrel on the handguard's
  bottom rail (6.5 to 10.5) and Laser on the handguard's right side, then Pistol Grip and Magazine. 56 of the M4's MWII
  parts are made eligible (optics, muzzle devices, grips, lasers and tracer rounds). A fitted foregrip hasn't been seen
  beside the left hand.
- Parts (`PARTS_AK12`, `Assets/gunsmith/ak12/`), 11 in all: it takes any AK-74 magazine and AK grip, as the real one
  does.
  - AK-74M Pistol Grip, then the AK-105's AK-platform grips.
  - AK-74M 30 Round Mag (no window), then the AK-105's 20, RPK-74 45 and four-column 60, with the AK-105's reloads and
    reload times (`reload_variants` `_smag`, `_xmag`, `_xmaglrg`).
  - No stocks or barrels. `part_masses.py` has its own magazine at 0.215 kg and its own grip at 0.09.
- Hands: the left hand holds the handguard through the AK-105's grip pose (`a_delta_barhvyshort_additive_for_offset`).
  No `GripFit`:
  - the idle left hand has 57 vertices inside the gun, at most 0.14" deep, about what the AK-105's does;
  - the right hand's are on the grip, below the view at the hip and aiming. The empty reload's bolt pull puts 25 into
    the receiver on screen, at most 0.09" deep (the AK-105's 0.08").
- It plays the AK-105's fire clip, which doesn't move the gun, so it has no `ads_fire`.
- The iron sights use ads_in's last frame. The AK-105's aim left the diopter 0.23 high, so `kastov_weapons.AK12.aim`
  lowers the gun until the aperture's centre is on the aim point and pitches it 0.095 degrees up onto the post's tip
  (within 0.001 and 0.005 degrees). Checked in a render (the post centred in the aperture), not in-game.
- Its `OpticAimCorrection` `3.18,0,-1.032` is the 762's measured correction moved by how far the AK-12's ADS pose puts
  its optic slot from the 762's, like the 74u's. NOT checked in-game: tune it with `dev_optic_correction`.
- It sprints with the M4's sprint and has the look sway and hand IK (see the pipeline notes).
- The sticker is on the receiver's left side above the magazine well. Neither it nor the charm has been seen on it.
- Its third-person left hand (`6.9,2.55,2.23`, see Third-person left hand) hasn't been rendered.
- Made on 2026-10-08 with the editor's bridge down. The editor compiled the prefabs, the .equip and the sounds, but not
  yet the models, the animgraph, the materials or the parts. If the first-person gun is invisible or keeps old clips,
  register its DMX and recompile `v_ak12.vmdl` and `v_ak12.vanmgrph` (see the pipeline notes), and `recompile_asset`
  the shared parts if the gunsmith doesn't offer them. Nothing has been checked in-game. Its gunsmith review note stays
  until all of it has been checked in a match.

