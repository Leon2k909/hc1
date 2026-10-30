## AK-74M (Escape from Tarkov's AK-74M, ARC9 EFT Assault Rifles 2962829818)
- The real Kalashnikov AK-74M (6P20, category AssaultRifle) in 5.45x39, the Russian army's standard rifle since 1991,
  as issued:
  - the 415 mm barrel with the 6P20 0-20 muzzle brake, the plain dust cover, the black polymer handguard, the
    side-folding polymer stock, the tangent rear sight and the 6L23 polymer magazine;
  - no top rail: an optic goes on a bracket clamped to the dovetail on the receiver's left side.
- The user asked for guns that look exactly like the real ones, not ones adapted for a game (2026-10-08), so it's
  Tarkov's model, from darsu_eft's ARC9 pack (the c_ak100 viewmodel, decompiled to `decompiled/ak15`, and its default
  attachments, to `decompiled/ak74m`). It's on the AK-105's CoD rig and clips with the AK-12's fit (see AK-12). Its
  figures are in `kastov_prefabs.gameplay_ak74m`, from Rosoboronexport's catalogue:
  - 600 rpm, automatic and semi. It starts on automatic.
  - 7N6 at 900 m/s from the 415 mm barrel, G7 0.157, like the AK-12's. The sights sit 52.9 mm over the bore (the eye's
    height over it at the ADS pose, on the line from the rear notch's shoulders to the front post's tip), zeroed at
    300 m like the AK-105's and AK-12's.
  - The M4's 5.56 damage (20) and falloff, as the AK-105's and AK-12's 5.45 have.
  - 3.4 kg without a magazine and ~3.95 kg with a loaded 6L23 30 (0.23 kg, and 30 rounds of 10.5 g): too little over
    the AKM's 3.75 kg for a WeightSlowdown. So SpeedPenalty 40 and 0.25 s ADS.
  - The recoil scale (1.45,3.62) is the M4's (2,5) scaled by free recoil (~1.35 against 1.86 m/s).
  - Reload times are the AK-105's clips', as for the AK-12: 2.3 s, and 2.6 s empty.
  - Bots can be issued it: it's a Primary AssaultRifle, so it's in `WeaponPool` and shares the rifles' half.
- `Tools/ak74m_rig.py` puts Tarkov's pieces on the AK-105's skeleton with `ak12_rig.py`'s tools, and writes them as
  SMDs (`decompiled/ak74m/rig`). Its docstring has every piece.
  - c_ak100 has slot bones c_ak12 lacks, so its own skeleton is posed (`weapon_bones`): a bone the shared `ak_anims`
    idle animates takes the idle, and any other keeps its reference offset from its posed parent. Its magazine slot
    and dust cover bone are within 0.3 of the AK-12's, so the AK-12's fit holds.
  - The pack's default handguard is the Vityaz's, whose material it doesn't ship. The AK-74M's own black polymer
    handguard is in the pack only as the stock pieces two aftermarket models keep, in the AK-74M's handguard material.
    So the lower comes from the UltiMAK M1-B gas tube's model, and the upper from the CNC Guns OV GP's. Only those
    triangles are taken (`HANDGUARD`). The lower's front tongue is pressed back to the barrel's ferrule (`FERRULE_Y`),
    where the Vityaz's lower ends.
  - The optic mount is Zenit's B-13 "Klassika" (the pack's `eft_mount_dovetail_b13`): a Picatinny rail over the dust
    cover, on an arm from the dovetail.
  - `muzzle` is an extra bone, 0.2 inside the brake's front.
  - The side-folder (`ak74m_stock`) and its release button on the receiver's rear (`ak74m_stock_hinge`) are SMDs of
    their own, so the AK-105's stocks can take the stock's place and the fixed ones can hide the button.
  - It draws the side-on icon `ui/weapons/guns/ak74m_01.png` from the model, as for the AK-12.
- Materials and sounds are from `Tools/ak74m_assets.py`, run after `ak12_assets.py`:
  - Tarkov's sheets, built like the AK-12's (no metal, roughness from the phong exponent), from the Assault Rifles pack
    and EFT SHARED (Workshop 2917343547):
    - the receiver and barrel, the shared parts and bolt, the front sight block, the side rail, the dust cover, the
      brake, the rear sight and the magazine;
    - the stock and the pistol grip, whose `$color2` tints Tarkov's plum AK-74 grip to the AK-74M's black;
    - the handguard and the gas tube;
    - the B-13 in grey-black anodised aluminium.
  - The rounds in the magazine's lips are the AK-12's. The AK-105's magazines and the AK grips keep the AK-105's and
    Kastov-74u's materials.
  - The shot is Tarkov's AK-74M: four starts, each under the last round's tail, at the AK-12's level (the same 7N6 from
    the same barrel length).
    - Voiced at its own pitch (see The ported guns' sounds): the lows under 130 Hz eased 8 dB after 30 ms, Tarkov's
      tail eased 6 dB from 100 ms, 4 dB of presence for 25 ms (the recordings are darker than the AK-12's), the ground
      at 6.9 ms and the echoes at -33 dB.
    - Four takes, pitch 0.98-1.02.
  - The suppressed shot is Tarkov's four suppressed AK-74M takes under the AK-74's suppressed tail, 10 dB under the
    voiced open shot.
  - The reloads are the AK-12's events: the AK-105's clips, with Tarkov's AK-74 charging handle and polymer magazine
    foley, which is the 6L23's.
- It was ported with markings on, which `Tools/texture_markings/specs/ak74m.json` takes off (8 materials):
  - the selector's АВ and ОД (the dimple's ring and the track's line stay), acceptance stamps, and the serials with
    Izhmash's triangle;
  - the rear sight leaf's range numbers 1-10 and the battle setting's П, each copied from the plain leaf, with the
    scale's ticks kept;
  - the magazine's moulded number and Izhmash's triangle, the bolt's serial and a stamp, the stock's moulded label
    lettering and marks, and a number on the gas tube;
  - Zenit's markings on the B-13: ЗЕНИТКА™, its web address, ООО "ЗЕНИТ", Сделано в России and Б-13 "КЛАССИКА".
  Checked in close-ups of the textures on 2026-10-08, not on the model.
- Bodygroups (DefaultMask 553713749, read from the compiled `v_ak74m.vmdl_c` and `w_ak74m.vmdl_c` in the editor on
  2026-10-09; the two match):
  - `muzzle_tip` (the brake, hidden under a muzzle device);
  - `optic_rail` (the B-13, shown only under an optic);
  - `stock_hinge` (the folding stock's release button, hidden by the fixed stocks);
  - `stock` (10), `pistol_grip` (8) and `magazine` (5): the factory parts and the ones below.
  - The rear sight has no bodygroup: it stays under an optic, as on the real gun, where the B-13's rail ends behind it.
- Slots: Optic on the B-13's rail (-4.55 to 2.86) and Muzzle at the brake's rear face, then Stock (at
  `tag_stock_attach`, -5.716,0,3.649), Pistol Grip and Magazine.
  No Underbarrel or Laser slot: the polymer handguard has no rails. 45 of the M4's MWII parts are made eligible
  (optics, muzzle devices and tracer rounds).
- Parts (`PARTS_AK74M`, `Assets/gunsmith/ak74m/`), 20 in all. The user saw only a few and asked why the other AKs'
  parts weren't on it (2026-10-09). It takes what the real one takes:
  - The AK-105's stocks (9: it's the same AK-100 receiver), with recoil relative to the AK-74M's side-folder, as the
    AK-105's is. The AK-105's two copies of that side-folder aren't offered again. The Wooden, RPK Club-Foot and
    Thumbhole stocks are fixed, so they hide the release button. Strictly a fixed stock needs a fixed-stock rear
    trunnion, which a folding AK-74M doesn't have; they're offered as on the AK-105.
  - The AK-12 Pistol Grip, then the AK-platform grips (6), the AK-12's parts.
  - The AK-12 30 Round Mag (the 6L31, with a window; the factory reload), then the AK-105's 20, RPK-74 45 and
    four-column 60, with the AK-105's reloads and reload times (`reload_variants` `_smag`, `_xmag`, `_xmaglrg`).
  - Its own 6P34 Sb.15 side-folder, 6P1 Sb.8 grip and 6L23 30 are the factory parts, so the AK-12's AK-74M grip and
    30 aren't offered again.
  - `part_masses.py` has its stock at 0.45 kg, its grip at 0.08 and its magazine at 0.23, keyed by group
    (`stock/factory`, `pistol_grip/factory`: see Part weight), and the AK-12's grip at 0.09 and 30 at 0.215.
  - `hc1_ak74m_parts_check [filter] [view]` (`Editor/Hc1Ak74mGunsmithQa.cs`) fits every part on the world model
    offscreen, checks the masks and each part's bodygroups, and renders it to `output/ak74m-gunsmith/` (view 0 the
    stock and grip, 1 the whole gun, 2 the magazine). On 2026-10-09 all 21 passed, and in the renders every stock
    seats on the receiver's rear and every grip and magazine sits where it should. Not yet seen in first person or
    in a match.
- Hands: the left hand holds the handguard through the AK-105's grip pose (`a_delta_barhvyshort_additive_for_offset`).
  No `GripFit`, and the left hand's fit on the polymer handguard hasn't been measured.
- It plays the AK-105's fire clip, which doesn't move the gun, so it has no `ads_fire`.
- The iron sights use ads_in's last frame. The AK-105's aim left the rear notch 0.123 high, so `kastov_weapons.AK74M.aim`
  lowers the gun until the notch's centre is on the aim point and turns it 0.12 degrees down and 0.023 left onto the
  front post's tip (within 0.002 degrees). Measured from the meshes, not checked in a render or in-game.
- Its `OpticAimCorrection` `3.18,0,-1.371` is the 762's measured correction moved by how far the AK-74M's ADS pose puts
  the B-13's rail from the 762's slot: the AK-12's x, and 0.34 lower, since the B-13 holds an optic higher over the
  bore. NOT checked in-game: tune it with `dev_optic_correction`.
- It sprints with the M4's sprint and has the look sway and hand IK (see the pipeline notes).
- The charm hangs on the dovetail, just in front of the B-13's arm, its chain 0.27 clear of the clamp. The empty
  reload's left index finger comes within 0.2, as on the AK-105 and AK-12. The sticker is on the receiver's left side
  above the magazine well, between the dovetail and the rivets. Neither has been seen on it.
- Its third-person left hand (`6.9,2.7,2.27`, see Third-person left hand) hasn't been rendered.
- The editor compiled the materials and sounds on 2026-10-08, and the models, the animgraph, the prefabs, its parts and
  the shared parts on 2026-10-09, with no errors. Nothing has been checked in-game. Its gunsmith review note stays until all of it has been
  checked in a match.

