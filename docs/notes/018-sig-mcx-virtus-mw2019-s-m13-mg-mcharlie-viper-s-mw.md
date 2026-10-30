## SIG MCX Virtus (MW2019's "M13", mg_mcharlie, Viper's MW2019 Assault Rifles pack 2528829149)
- The real SIG MCX Virtus SBR (category AssaultRifle) in 5.56x45, through the Kastov pipeline from MW2019
  (`extracted/2528829149`, decompiled to `decompiled/mcharlie`). The user asked for a real gun from the packs that looks
  like the real one, not one changed for CoD (2026-10-03). MW2019's M13 is the Virtus SBR as SIG sells it, at the real
  gun's size: the 11.5-inch barrel, the free-float M-LOK handguard with its full-length top rail, flip-up sights, SIG's
  three-prong flash hider, a 30-round polymer magazine and the folding telescoping stock. Its figures are in
  `kastov_prefabs.gameplay_mcx`:
  - 850 rpm (the middle of the 800-900 usually quoted), automatic and semi, from the 30-round magazine.
  - M855 at ~837 m/s from the 292 mm (11.5-inch) barrel, where the M4's 14.5-inch gives 905, G7 0.151. The sights sit
    68 mm over the bore (the sight line through the rear aperture and the front post's tip), zeroed at 300 m like the
    other M855 rifles.
  - The M4's M855 damage (20), falloff curve and recoil pattern, with MaxRange cut to 0.855 of the M4's: the short
    barrel's share of its muzzle energy, as for the M18.
  - About 2.9 kg empty and 3.4 kg loaded, what the M4 weighs: SpeedPenalty 40, no WeightSlowdown, 0.25 s ADS. The
    recoil scale (1.85,4.62) is the M4's (2,5) scaled by free recoil (~1.72 against 1.86 m/s).
  - A suppressor doesn't change its rate (`SuppressorFireRateScale` 1): the Virtus's short-stroke piston has a
    two-position gas valve with a setting for one.
  - Reload times are when the gun is level again: 2.33 s, and 2.6 s empty, after the bolt release.
  - Bots can be issued it: it's a Primary AssaultRifle, so it's in `WeaponPool` and shares the rifles' half.
- Like the FAL's, its rig has no pistol grip part (the grip is the lower receiver's), so `tag_pistolgrip_attach` is an
  extra bone on the centreline. The viewmodel's stock adapter (its `tag_stock` bodygroup) is left out: it's for MW's
  generic stocks, and each MCX stock carries its own hinge. The flip-up sights are two models' pieces joined with `+`
  (`port_kastov.part_triangles`): the rear sight is the receiver model's `tag_sight` bodygroup, the front the barrel's.
- Materials and sounds are from `Tools/mcx_assets.py`: the MCX's own lower (with the pistol grip, magazine well and
  trigger guard), upper (the handguard and the top rail), flip-up sights, barrel, flash hider, magazine (its window
  see-through, the vmt's `$translucent`) and both stocks.
  - The shot is the pack's six dry recordings, each levelled to the same loudness (+9 dB), so every shot sounds a little
    different, at about the AUG's level. The pack's own event plays a premixed copy of the first, with a long reverb
    tail baked in. The suppressed shot is the six suppressed recordings at -12 dB. The .300 BLK conversion's subsonic
    set isn't used.
  - Reload foley plays at the viewmodel QC's event frames. The MW base's generic rattles and magazine drop are left out.
  - All three are voiced like the other ported guns' (see The ported guns' sounds). The rip's shot has a designed low
    ring (under 150 Hz at -11 dB 100-250 ms after the onset, where the other voiced rifles' are at -19 to -24) and is
    dark (its first 30 ms centre at 0.67-1.15 kHz). A short barrel's blast at the shooter is a sharp crack, with much of
    the powder burning past the muzzle, so it keeps its pitch and gets the lows eased 8 dB and 5 dB of presence: voiced,
    the ring is at -23 dB and the first 30 ms centre at 1.1-1.55 kHz. The reload foley came down 17.2 dB: its loudest
    file, the empty reload's magazine going in, was 1.2 dB over the shot.
- It was ported with markings on: QR codes and a coded strip on the lower and one on the handguard, serials (TA
  300248-B-77 and TA 300240-B-77, and TA 300249-B-77 on the Thin Folding Stock's hinge), the rip's made-up makers TEMPUS
  ARMAMENT INC (its name and address, and its logo on the handguard), CRONEN and SOLOZERO OPTICS (its name, and its
  chevron logo on the rear sight's leaf and a knob), a RESTRICTED MILITARY/GOVERNMENT LAW ENFORCEMENT USE ONLY label,
  the selector's lettering, the rail's slot numbers, lettering on the charging handle's latch, a helmeted skull emblem
  on the upper's round plate, a worn stamp, the sights' R and UP, the magazine's round counts (10, 20, 30) and a painted
  181, and handwriting (T8) inside it. `Tools/texture_markings/specs/mcx.json` takes them off (64 regions over 8
  materials), checked in before/after close-ups of the textures on 2026-10-03, not yet on the model. The selector's
  pictograms, the sights' arrows and the counts' moulded underlines stay.
  - The markings tool got two keys for it (its README has them): a region with `maps` edits only those maps (the 181 is
    paint, so only the colour and roughness), and a `keep` region's pixels are never written (the underlines).
- Bodygroups (DefaultMask 341 by the bit rule, not yet read from the compiled models):
  - `muzzle_tip`: the flash hider, hidden under a muzzle device.
  - `iron_sights` and `sight_folded`: the flip-up sights raised, and folded down under an optic.
  - `stock`: the factory stock and the Thin Folding Stock.
- Slots: Optic on the top rail (`tag_reflex`; an optic folds the sights), Muzzle at the flash hider's rear face
  (`tag_tip`), Underbarrel on the handguard's flat bottom (below) and Laser on the handguard's right side at the bore's
  height, ahead of the fingertips, then Stock. 56 of the M4's MWII parts are made eligible (optics, muzzle devices,
  grips, lasers and tracer rounds).
- The Underbarrel slot's origin is at x 9.76 (2026-10-05). The handguard's flat bottom runs 5.82 to 12.0 in the world
  model, and the left hand's index finger wraps it at 9.1.
  - It was at the pack's `tag_grip_attach` (11.168). The M4's grips reach forward from their origin (the vertical ones
    and the stubbies 2.1, the bipod 2.14; the angled one reaches 4.2 back), so every vertical grip ended 1.3 past the
    handguard's front, out under the flash hider. The user saw it on the Bipod, Slotted Vertical, Stubby, Tall Vertical
    and Wide Stubby Foregrips.
  - Now their fronts are 0.1 inside the handguard's front, as on the other guns (their grips end at their rail's
    front), and their backs 0.5 clear of the index finger. The angled grip runs 5.53 to 9.83.
  - Measured from the OBJs and `w_mcx.dmx` (the DMXs are keyvalues2 text). The prefabs were patched by hand to what
    `kastov_prefabs.py` writes. Not seen in-game.
- Its own part (`Prefabs.parts`, `Assets/gunsmith/mcx/stocks/`): the Thin Folding Stock, SIG's thin folding stock (the
  pack's light stock), a skeleton stock with a narrow buttplate: 5% more recoil, and 0.06 kg lighter. Left out: the
  pack's other stock (CoD's), its 50- and 60-round magazines, its .300 BLK magazine and barrel (another calibre), and
  its other barrels.
- Its left thumb lies over the top rail from the left side. The user saw it sink into the rail (2026-10-05). An
  earlier count had the idle left hand at 84 vertices inside the handguard (0.08") and 128 aimed (0.15"). So it has a
  `GripFit` (`kastov_weapons.MCX.left_grip`): the arm 0.05 right and 0.15 up, and the thumb's bend 20% open.
  - The thumb's axis went from 0.44 over the rail at the hip and 0.25 aimed to 0.60 and 0.52. The AK-105's, M16A4's
    and FAL's thumbs keep 0.49-0.52.
  - The fingertips went from 0.13 to 0.18 off the handguard, and the palm stays 0.57 off it (the M16A4's 0.57).
  - The arms' mesh is a cloud model whose glTF export wasn't to hand, so this was measured from the bones (sample
    points along the palm and each finger) against the skinned gun mesh, with the tools in `Tools/grip_fit/`.
  - The rips weren't to hand either, so the fit went into the exported clips directly (`Tools/grip_fit/apply.js`),
    as `port_kastov.Kastov.pose` would apply it: the same weight, arm shift, `ik_hand_L` and finger opening.
    `port_kastov.py` from the rips gives the same clips. Don't run `apply.js` on them again: it would add the fit twice.
  - Not yet seen in-game. If the old grip still shows, the editor missed the changed DMXs: recompile `v_mcx.vmdl` (see
    the pipeline notes).
  - The right hand's go up to 0.39" into the gun (155 vertices; the 762's 0.37").
- The iron sights use ads_in's last frame. The addon's aim (`0,-1,0`) left the rear aperture's centre 0.01 above the
  camera and the front post's tip 0.058 degrees over the aim point; `kastov_weapons.MCX.aim` lowers the gun onto the
  line through them and turns out its tilt. Checked in a render, not in-game.
- Aimed, it fires with the pack's `fire_2` (`Weapon.ads_fire`, see the pipeline notes): the hip clip rolls the gun up to
  2.5 degrees about the bore and pitches it 1.1 every shot, and at 850 rpm each shot starts it again; `fire_2` rolls it
  0.5 at most and kicks it 0.5" straight back.
- It sprints with the M4's sprint and has the look sway and hand IK (see the pipeline notes).
- The charm hangs on the stock's hinge block at the back of the receiver, by the real gun's QD sling sockets, which both
  stocks share: not over the grip, where the right thumb rests, nor on the factory stock, where it would float beside
  the thin one. Every hand joint stays 1.07" or more from it through every clip. The sticker is on the upper receiver's
  left side above the magazine well.
- Its `OpticAimCorrection` `3.118,0,-0.274` is derived with the Bizon's formula, NOT checked in-game. Its z is small
  (the Kastovs' are about -1.2): its flip-up sights stand on the top rail, as the M4's do.
- Its third-person left hand (`4.2,2.735,2.49`, see Third-person left hand) hasn't been rendered.
- Made offline on 2026-10-03 with the editor closed. When the editor next opened (2026-10-04) it compiled the models
  (`v_mcx.vmdl_c` 1 MB, `w_mcx.vmdl_c`), the animgraph, the materials, sounds, prefabs and its part, each leaving a
  compiled file. Nothing has been checked in-game. If the gunsmith doesn't offer it the 56 shared parts,
  `recompile_asset` them after a hotload. Its gunsmith review note stays until all of it has been checked in a match.

