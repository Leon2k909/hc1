## SIG Sauer M18 (MW2019's "M19", mg_p320, Viper's MW2019 pistol pack 2459723892)
- The real SIG Sauer M18 (category Pistol, in the Secondary slot), the US Army's compact P320 with the coyote grip module
  and slide, through the Kastov pipeline from MW2019 (`extracted/2459723892`, decompiled to `decompiled/p320`). The user
  asked for a real pistol from the CoD packs and left the pick to Claude (2026-09-29). Its figures are in
  `kastov_prefabs.gameplay_m18`:
  - Semi only, from a 17-round magazine. FireRate 450 is the shortest split between shots (0.13 s), as for the USP.
  - M1152 ball (115 gr FMJ) at ~375 m/s from the 3.9-inch barrel, G1 0.14. The sights sit 16 mm over the bore, zeroed
    at 25 m like the other pistols.
  - Damage and falloff are the MP5's 9 mm (BaseDamage 12; the USP's .45 is 15), with MaxRange cut to 0.815 by muzzle
    energy (524 J against the MP5's 643 J).
  - The rest of the handling is the USP's (`Gameplay.borrow`): the Pistol hold, the crosshair, SpeedPenalty 20, recoil
    with no pattern, view punch, casing and flash. It has no FovOffset shot kick (`Gameplay.remove` takes the M4's off).
    The recoil (1.86 up, ±1.3 sideways) is the USP's scaled by free recoil (~3.2 against ~3.5 m/s).
  - Reload times are when the gun is level again: 1.57 s, and 2.1 s empty, after the slide release.
  - `Prefabs.equip_fields` sets the .equip's Slot (Secondary) and the USP's armour penetration (ArmorReduction 0.775,
    HelmetReduction 0.4). `icon_width` 0.33 sizes its icon like the USP's.
  - Bots don't use it: their pool is primaries only.
- The pistol rig hangs the gun off `tag_pistol_offset`, which `Weapon.bone_renames` reads as `tag_sling`
  (`kastov_smd.BONE_RENAMES`), the bone the pipeline and the prefabs go by.
  - The rig has no muzzle, left-hand tag or pistol grip mount (the left hand cups the right), so `muzzle` and
    `tag_pistolgrip_attach` are extra bones.
  - `tag_pistolgrip_attach` is placed so the world model's grip sits where w_usp's does, for the third-person Pistol
    hold.
  - It has no `LeftHandIK` (`world_left_hand=None`, like the USP's and 1911's) and no charm (`charm=None`).
- Slide lock (`Weapon.slide_lock`: the QC's `empty_offset`, `a_delta_empty_additive_for_offset`). While the magazine is
  empty, the slide stays back, the barrel tilts out of battery and the magazine's top rounds are gone.
  - The port exports it as `empty_delta`.
  - It also exports `fire_empty` (and `fire_ads_empty`): the shot with the slide held from the frame the recoil takes it
    furthest back.
  - The graph adds the delta to idle, sprint, lowered and draw while `b_empty` holds, and the fire state picks the empty
    shot by `b_empty` (synced).
  - A slide lock can't go with `steady_fire`: the port asserts it.
- The slide and its sights are one piece from two models, a mesh path of `+`-joined SMDs (`port_kastov.part_triangles`).
  The attachment model has its sights as a bodygroup.
- Materials and sounds are from `Tools/p320_assets.py`: the pistol's own frame, slides, sights and magazines.
  - The pack plays its shot as a distance-variant sound, so only its near channel is used, levelled -6 dB: a touch over
    the Vityaz's 9 mm, as a short barrel is at the shooter.
  - Reload foley plays at the viewmodel QC's event frames.
- It was ported with markings on:
  - the label plate's QR code and MFR CORDEF / PNO / SER, the serials, and CA - USA;
  - CoD's made-up makers CORVUS DEFENSE and XRK on the grip, slides and magazines;
  - 9MM PARA and 9mm x 19, and the sights' CD / T38 marks;
  - the magazines' witness numbers, and the 21-round one's base plate label and headstamp.
  `Tools/texture_markings/specs/m18.json` takes them off (38 regions over 6 materials), checked in before/after views of
  the textures on 2026-09-29.
- Bodygroups (DefaultMask 145, read from the compiled models): `barrel` (the slides: coyote, black, vented, long) and
  `magazine` (17, 21, 32).
- Slots: Barrel (the slide, as a pistol's slide is in CoD), Magazine, and Ammunition (tracer rounds, made eligible).
  There's no optic, muzzle or laser slot (`slots=[]`): the barrel isn't threaded, the model's slide has no optic cut,
  and the M4's lasers are rifle lasers.
- Parts (`PARTS_M18`, `Assets/gunsmith/m18/`):
  - Black Slide: SIG's black Nitron slide.
  - 21 Round Mag: the Army's extended magazine, with the pack's xmag reloads (`reload_variants` `_xmag`): 1.57 s, and
    2.13 s empty.
  - Not offered: the vented and long slides (CoD's designs) and the 32-round magazine (SIG's longest holds 21).
- The sticker is on the slide's left side between its serrations. Its viewmodel point rides the slide's bone object,
  `j_slide` (`Prefabs.sticker_bone`, placed by `bind_position`), so it moves with the slide.
- Aimed, it fires with the pack's `fire_2` (`Weapon.ads_fire`). Both fire clips flip the muzzle up ~10 degrees as the
  slide cycles, back by frame 12. The hip one also swings it 4.3 degrees sideways, and the aimed one 1.6.
- The iron sights use the pack's own aim (its lua's 0.15 forward) at ads_in's last frame.
- v_m18.vmdl, w_m18.vmdl and v_m18.vanmgrph compiled on 2026-09-29 with no errors. Nothing else has been checked, in
  renders or in-game: the iron sights, the slide lock, the M4's sprint on a pistol, the reloads, the look sway, the
  sticker, and the world model in hand and holstered. Its gunsmith review note stays until they've been checked in a
  match.

