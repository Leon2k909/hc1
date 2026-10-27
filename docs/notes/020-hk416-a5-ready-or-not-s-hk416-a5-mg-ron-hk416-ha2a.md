## HK416 A5 (Ready or Not's HK416 A5, mg_ron_hk416, Ha2ard's pack 3385630838)
- The real Heckler & Koch HK416 A5 (category AssaultRifle) in 5.56x45, with the 11-inch barrel and HK's tan M-LOK
  handguard, through the Kastov pipeline (`extracted/3385630838`, decompiled to `decompiled/hk416`). The pack ("[MW
  Unofficial] RON HK416 A5") is Ready or Not's model on the MW base, with Escape from Tarkov's HK stocks and its HK and
  Magpul magazines as attachments. It's the second of the user's list after the L85A2 (see L85A2). Its figures are in
  `kastov_prefabs.gameplay_hk416`:
  - 850 rpm (the middle of the 700-900 usually quoted for the short HK416s), automatic and semi, from a 30-round
    magazine.
  - M855 at ~826 m/s from the 279 mm (11-inch) barrel, between the 10.3-inch's ~790 and the MCX's 837 from 11.5 inches,
    G7 0.151. The sights sit 72.5 mm over the bore (the eye's height at the ADS pose, through the flip-up rear sight's
    aperture), zeroed at 300 m like the other M855 rifles.
  - The M4's M855 damage (20), falloff curve and recoil pattern, with MaxRange cut to 0.833 of the M4's by muzzle energy,
    as for the MCX.
  - 3.13 kg (HK USA's 6.9 lb) without a magazine, ~3.75 kg loaded with HK's steel magazine: what the M4 weighs, so
    SpeedPenalty 40, no WeightSlowdown and 0.25 s ADS. The recoil scale (1.66,4.14) is the M4's (2,5) scaled by free
    recoil (~1.54 against 1.86 m/s).
  - A suppressor doesn't change its rate (`SuppressorFireRateScale` 1): the A5's gas regulator has two positions, N for
    normal fire and S for a suppressor.
  - Reload times are when the gun is level again: 2.33 s, and 2.73 s empty, after the bolt release.
  - Bots can be issued it: it's a Primary AssaultRifle, so it's in `WeaponPool` and shares the rifles' half.
- The model is close to the real gun's size: 29.3 in from the butt to the muzzle with the stock collapsed, where HK USA
  gives 27.9 in for the 11-inch A5. Its top rail is 0.814 wide (a Picatinny rail's 0.835), so it isn't scaled.
- Its rig is RoN's, not CoD's (`part_mounts` and `icon_rows` are new for it):
  - Its pieces (the receiver, handguard, pistol grip, charging handle, bolt carrier and the reloads' loose round) are
    the viewmodel's own meshes (`vm_meshes`), and its barrel and magazines are bone-merged models.
  - Its Tarkov stocks are VElements, placed on a rig bone (`Weapon.part_mounts`: `tag_stock_attach`, 1.6 forward and
    0.07 down, from the pack's lua), not where their vertices sit.
  - `Prefabs.icon_rows` crops the pack's icon to the gun's rows (60-255) before the white silhouette is drawn.
  - `muzzle` and `tag_pistolgrip_attach` are extra bones, as for the P90.
- Materials and sounds are from `Tools/hk416_assets.py`:
  - RoN's receiver (with every gun part and the stock) and steel magazine (with the rounds), partly metal. Tarkov's HK
    polymer magazine, E1 and Slim Line stocks and the M-LOK rail sections are polymer. Magpul's PMAGs are Source-style
    sheets; the PMAG 30's window is see-through, though its vmt says otherwise. The laser's mount is MW's.
  - The shot is Tarkov's two close HK416 recordings and the suppressed shot its suppressed one, levelled to the MCX's:
    the same round from a barrel of about the same length.
  - Reload foley plays at the QC's event-5004 frames, through the pack's alias list (`mw_sounds_hk416.lua`): the MCX's
    MW2019 moves and the pack's own magazine and charging handle sounds. The MW base's generic rattles and magazine
    drop are left out.
  - All three are voiced like the other ported guns' (see The ported guns' sounds). The shot keeps its pitch, the lows
    under 130 Hz are eased 8 dB after 30 ms, the recordings' own tail is eased 20 dB from 80 ms (it was baked in, like
    the FAL's), and there's 2 dB of presence for 25 ms. The ground comes 7.3 ms after the direct sound (the muzzle
    ~0.56 m ahead of the ear). The two recordings make four takes, pitch spread 0.98-1.02.
- It was ported with markings on, which `Tools/texture_markings/specs/hk416.json` takes off (52 regions over 8
  materials):
  - RoN's made-up maker on the receiver: the HaKa logos, "HaKa 416 Cal. 5.56 mm x 45", "Hartmann & Karl GmbH, Made in
    Deutschland", the serials (65-000404) and the red 30s beside the selector's pictograms;
  - the steel magazine's calibre and the made-up maker on its floorplate;
  - the stocks' and the polymer magazine's HK logos and names, its date wheel, and Made in Germany;
  - on the PMAGs, Magpul's names and logos, GEN M3, the CAGE code, part numbers, patent and web address, the mould
    numbers and date wheels, and the round counts.
  The moulded outlines, pills and the logo ring stay. Checked in before/after close-ups of the textures on 2026-10-08,
  not yet on the model.
- Bodygroups (DefaultMask 74069 by the bit rule, not yet read from the compiled models):
  - `muzzle_tip`: the flash hider, hidden under a muzzle device.
  - `iron_sights` and `sight_folded`: HK's flip-up diopter sights raised, and folded down under an optic.
  - `laser_rail`: an M-LOK rail section on the handguard's right side, shown only under a laser.
  - `magazine` and `stock`: the factory parts and the ones below.
- Slots: Optic on the upper's rail (`tag_reflex`; an optic folds the sights), Muzzle at the flash hider's rear face
  (`tag_silencer`) and Laser at the back of the M-LOK section (9.34 to 11.72), ahead of the left hand's fingertips, then
  Stock and Magazine. 48 of the M4's MWII parts are made eligible (optics, muzzle devices, lasers and tracer rounds).
  - No Underbarrel slot: the left hand cups the handguard's underside from x 6.5 to 10.4, and its bottom rail ends at
    11.1, where the M4's vertical grips need 2.26.
- Parts (`Prefabs.parts` in its `kastov_prefabs` entry, `Assets/gunsmith/hk416/`), with recoil relative to the
  viewmodel's own collapsible stock and weights against HK's steel magazine (~0.25 kg):
  - E1 Stock: HK's, with a broad rubber buttpad. 5% less recoil, +0.05 kg.
  - Slim Line Stock: HK's, lighter and narrower, with a thin buttpad. 5% more recoil, -0.05 kg.
  - Polymer 30 Round Mag: HK's polymer magazine (0.14 kg).
  - PMAG 20, 30 and 40: Magpul's Gen M3 (0.11, 0.136 and 0.18 kg). The 20 and 40 reload with the pack's own clips
    (`reload_variants` `_smag`, `_xmag`): the gun is level again at 2.07/2.17 s and 2.63/3.13 s. The 30s use the
    factory reloads.
  - Left out: the pack's ISO and TAQ magazines (Tarkov's made-up ones), its speed-pull loops, the other makers' AR
    stocks and an AK-12's stock, and its grips (there's no Underbarrel slot).
- No `GripFit`: the idle left hand has 78 vertices inside the handguard, at most 0.085" deep, and 80 (0.068") aimed
  (the verified 762's 54 go 0.10").
- Aimed, it fires with the pack's `fire_2` (`Weapon.ads_fire`, see the pipeline notes): the hip clip rolls the gun 2.5
  degrees about the bore and pitches it 1.1 every shot, and `fire_2` rolls it 0.54 at most and kicks it 0.5" straight
  back.
- The iron sights use the addon's own aim (its lua's Aim, 0.5 forward and 0.18 down) at ads_in's last frame. Not checked
  in a render or in-game.
- Its `OpticAimCorrection` `1.617,0,-0.105` is derived with the Bizon's formula, NOT checked in-game. Its z is small (the
  Kastovs' are about -1.2): its flip-up sights stand on the top rail, as the M4's do.
- It sprints with the M4's sprint and has the look sway and hand IK (see the pipeline notes).
- The charm hangs on the receiver end plate's left side, by the real gun's QD sling socket, in front of every stock.
  Every hand joint stays 0.97" or more from it through every clip (the right thumb is nearest). The sticker is on the
  magazine well's left side.
- Its third-person left hand (`4.97,2.47,2.57`, see Third-person left hand) hasn't been rendered.
- The models, the animgraph, the prefabs and its parts compiled in the editor on 2026-10-08, each leaving a compiled
  file. Nothing has been checked in-game. Its gunsmith review note stays until all of it has been checked in a match.

