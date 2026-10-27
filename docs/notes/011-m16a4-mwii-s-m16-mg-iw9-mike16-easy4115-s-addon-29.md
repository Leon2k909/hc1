## M16A4 (MWII's M16, mg_iw9_mike16, easy4115's addon 2962304029)
- The real 5.56x45 M16A4 (category AssaultRifle), through the Kastov pipeline from a separate addon
  (`extracted/2962304029`, decompiled to `decompiled/mike16`). The user asked for a real gun from the CoD packs, not a
  made-up one. Its figures are in `kastov_prefabs.gameplay_m16`:
  - Semi-automatic and three-round burst, no automatic, at 800 rpm cyclic (the middle of the M16's 700-900).
  - The M4's M855 round (damage 20, falloff and recoil pattern) from the 20-inch barrel: 945 m/s, G7 0.151. The sights
    sit 68.5 mm over the bore (the eye height at ADS, through the carry handle's aperture), zeroed at 300 m.
  - About 4.0 kg loaded, 0.6 kg over the M4: SpeedPenalty 40, no WeightSlowdown, 0.25 s ADS. The recoil scale
    (1.78,4.44) is the M4's (2,5) scaled by free recoil (~1.65 against 1.86 m/s).
  - Reload times are when the gun is level again: 2.3 s, 2.4 s empty.
- Burst (`Shootable.OnInputUpdate`): a trigger pull fires one whole burst, and holding the trigger fires no more, as in
  semi. A burst also ends when the magazine runs dry. `BurstEndDelay` is 0, so the next pull can follow at the cyclic
  rate. The real gun's non-resetting burst cam isn't modelled, and letting go doesn't cut a burst short. The AK-12's
  two-round burst works the same way (see AK-12). With a gun that has no automatic, bots fire at most `BurstAmount` rounds a pull
  (`LightweightCombatBot._roundsPerPull`) instead of their 3-7 round strings.
- Materials and sounds are from `Tools/m16_assets.py`: the M16's own receiver, carry handle, barrel, handguard, rails
  and stock, plus the MWII M4 flash hider, pistol grip, 30-round magazine (with a see-through window) and rounds that
  the addon ships. The shots are MWII's M4 recordings, levelled to the AK-105's (-3 dB, suppressed -10 dB). Reload
  foley plays at the viewmodel QC's event frames.
- Its shot is voiced away from CoD's sound design like the AK-105's (`Tools/m16_shot.py` on `Tools/shot_voicing.py`,
  2026-09-29). The user asked for another gun after the AK-105. The script's docstring has each step and why.
  - The rip is a carbine's shot mastered for a game: a 48 Hz boom for 200 ms, a rumble under 200 Hz running on for the
    whole second, lows as loud as the blast's midrange, and its first 83 ms clipped flat. The clipping stays: the codec
    smeared the plateaus, and fitting curves across them left them flat.
  - Now: 2% higher (a 20-inch barrel's lower muzzle pressure gives a shorter blast); a 45 Hz high-pass, and under 140 Hz
    eased 6 dB after the first 25 ms; the rip's own sound eased 12 dB from 80 ms to 200 ms (`Voicing.rip_tail_db`), so
    its designed tail gives way to the echoes; 1.5-6 kHz up 3 dB for the first 20 ms; the ground 6.8 ms after the
    direct sound (the muzzle 0.75 m ahead of the ear); echoes from 35 ms to 1.4 s, as the AK-105's.
  - The tail is where the rip's was (-32.7 dB 0.4 s after the loudest 100 ms, against -32.5), but it's echoes, not a
    low rumble. Loudness matches the old shot's within 0.1 dB.
  - Four takes (`m16_shot_01-04.wav`), pitch spread 0.98-1.02 (was 0.96-1.04). The suppressed shots are voiced from
    the same settings (see The ported guns' sounds).
  - `--preview <wav>` writes the old and new shots and three three-round bursts each. The old WAVs and event are in
    `Backups/m16_shot_rip/`.
  - Made with the editor closed: the WAVs and `m16.fire.sound` need compiling (03 and 04 are new), and it hasn't been
    heard in-game.
- A part mesh path ending in `#bone,bone` keeps only the triangles on those bones, and `#!bone,bone` only the rest
  (`port_kastov.part_triangles`). CoD hides the rail cover by its bone (`tag_grip_hide`), and the magazine's rounds are
  one mesh with the clips' loose round (`j_ammo_31`). `Weapon.unmerged_bones` places the barrel's `tag_grip_hide` by
  the part's own reference pose: bone-merged onto the rig's (5.7 back, 1.7 higher), it lifted the cover into the
  handguard.
- Bodygroups:
  - `muzzle_tip`: the birdcage flash hider, hidden under a muzzle device.
  - `laser_rail`: a rail section on the handguard's right side, shown only under a laser.
  - `carry_handle`: with the rear sight. An optic takes it off, as on the real flat-top.
  - `factory_front_sight`: the front sight post, on the barrel's fixed front sight base. It stays up under an optic,
    as on the real M16A4, and the optics co-witness with it (`ManualOffset.OpticSightLines`, below). An optic briefly
    took it off, because the dot sat low between the post's ears (the user: "it has the red dot inside of the front
    ironsight"), and the user turned that down: "it should be realistic rather than removing the front post". A
    replacement barrel takes the post off, and the barrel's own front sight folds under an optic
    (`GunsmithMw22Attachment.RefreshMount`).
  - `grip_cover`: the bottom rail's front cover, which a grip takes off.
- The left hand holds the four-rail handguard through the grip pose `a_delta_grip_barmidhvy_additive_for_offset`, the
  mid-length heavy barrel's (the QC's `grip_barmidhvy_offset`), made for a thick handguard: the palm on its left side,
  the thumb over the top and the fingers under it.
  - The factory barrel's lua asks for `grip_vertpro_offset`, which is a QC `$sequence` name: the QC plays the vertshort
    clip there, which holds a short vertical grip. With it the hand closed on air 2.3" under the handguard (the user:
    "im not holding it correctly"). Look a grip sequence's clip up in the QC; don't go by its name. The vertpro clip
    itself also moves `tag_pistolgrip_attach`, which shifted every world point by (-4.4,0,2.4).
  - The grip pose moves only the left arm: the gun, the camera and the right hand are where they were, so the aim and
    the optic correction stand.
  - No `GripFit`: the idle left hand has 121 vertices inside the handguard, at most 0.09" deep (the verified 762's 52
    go 0.10").
- The fire clip is `Weapon.steady_fire` (`Kastov.steady_fire`): the addon's first 15 frames with the gun and arms held
  in the idle pose, so only the bolt, dust cover, trigger and trigger finger play, as in the Kastovs' own clips, and
  HC1's recoil does the kick.
  - The addon's clip rocked the gun 0.2" each way sideways and 2.5 degrees about the bore, settling over 1.4 s, and
    every shot started it again, at the hip and aimed (the user: "too much moving horizontally its like bouncy").
  - Its aimed clip, `fire_2`, still turns the gun 0.78 degrees, so the M16A4 doesn't take `ads_fire`.
  - The fire state now lasts 0.5 s instead of 1.7 s, so a sprint straight after a shot animates sooner.
- Its walk sway measured the same as the AK-105's and the 762's, so it was left alone.
- No parts of its own: it takes the M4's MWII parts (56 made eligible: optics, muzzle devices, grips, lasers and tracer
  rounds) in Optic, Muzzle, Underbarrel and Laser slots. The addon's M16 20-round magazine, and the M4 stocks, grips,
  magazines and barrels it ships, aren't ported.
- The hold and the steady fire clip were checked in renders of the compiled model on 2026-09-28: the muzzle and the
  camera bone didn't move through a hip shot or an aimed one.
- The iron sights were checked in a render (ads_in's last frame), not in-game. The addon's aim put the sight line 0.113
  above the camera, with the front post 0.32 deg over the aim point and low in the rear aperture. `kastov_weapons.M16.aim`
  lowers the gun onto the line through the aperture's centre and the post's top.
- The front sight post stood 1.514" over the flat-top's rail, 0.104" taller than an AR's iron sight line: 1.41" over
  the rail is the absolute co-witness height red dot mounts are made to (SIG's ROMEO8T manual; Scalarworks' LEAP/01 and
  fixed front sight, 1.42). Since 2026-10-19 it screws down into its sight base (`Weapon.part_moves` on `sighton.smd`),
  its tip 1.418" over the rail, and the base's ears stand over it as on a real A2 base.
  - The aim turns the gun 0.293 degrees nose up about the rear aperture (4.2 ahead of the eye), so the lower tip is back
    on the aim point: `aim` pitch -0.235 (was 0.058), z 0.003 (was 0.022). The arm retarget is built at that pose, so
    every clip's arms turn with it (about 0.02" at the fingertips).
  - Solved from the meshes, not checked in a render or in-game. The carry handle's rear aperture still sits about 0.077"
    over the 1.41" line, as if its drum were set a click higher.
- Its `OpticAimCorrection` `1.613,0,0.079` is derived with the Bizon's formula, NOT checked in-game. Its z is near 0
  where the Kastovs' are about -1.2, because the irons sit 1.5 above the rail on the carry handle.
- Co-witness: each 1x optic has a sight line on top of the correction (`ManualOffset.OpticSightLines`, written from
  `kastov_prefabs` `Prefabs.optic_sight_lines`), so the dot sits against the post as a real one does. Since the
  reticles were collimated (2026-10-18, see Red dots on the bullet line), the dot only shows where the sight points: the
  gun-level `OpticAimAngleCorrection` (`0.2325,-0.0001,0` since the post went down: the aim's 0.293 degrees nose up put
  the dots 0.287 high; it was `-0.0547,0.0031,0`) puts it on the screen's centre, and each line only moves the eye
  (Angles `0,0,0`), up or down in the window (Position z -0.30 to +0.03) until the post's tip is at its mark. The old
  lines also turned the gun 0.44-2.18 degrees nose down to bring the drawn-at-depth dot onto the post; collimated,
  that put the dots up to 2 degrees low. Each optic takes its real analog's height on a flat-top:
  - Absolute (the dot on the post's tip, the optic on its own low base): the Box Collimator (`att_vm_reflex_02`, an
    EOTech-type holographic, which sits absolute on an M16A4's rail, so it isn't raised), the Tube Collimator, the Dial
    Holographic, and the Long-Body, Hooded and Round-Hood Reflex.
  - Lower 1/3 (the post's tip 0.14" under the dot, from a real optic's 1.535-1.57" line over the rail against 1.41" at
    absolute): the `_tall` risers (the three Mini Red Dots, the Ring Reflex, the Tube Red Dot), and the raised-base
    Enclosed and QD Holographic.
  - The eye stays within the middle 60% of the window's height; past that a small window would hide the dot. On
    2026-10-18 six optics couldn't reach their mark inside it, because the post stood 0.104" too tall and five optics sat
    too low. Since 2026-10-19 both are at real heights and all 13 reach it, the QD Holographic's eye nearest the limit
    (0.258 of 0.303).
  - The five sat 0.3-0.47" under their real analogs: the three Mini Red Dots' windows 1.08-1.10" over the rail on their
    riser, the Tube Red Dot's 1.25 and the Tube Collimator's 1.10, against 1.516-1.57" for lower 1/3 mounts (Trijicon's
    AC32059, Aimpoint's 39 mm, Scalarworks) and 1.41 absolute. `Tools/optic_risers.py` lengthens their mounts: the Mini
    Red Dots and the Tube Red Dot to 1.55" (lower 1/3), the Tube Collimator to 1.41" (absolute).
    - Each mount is cut through a plain, vertical part of it, everything over the cut goes up, and a band between the
      halves repeats the texture's row at the cut, so the riser reads as the same block, taller, with nothing stretched.
    - Every part made from these models (the M4's MWII parts, which the ported guns share, and the MP5's copies) lowers
      its `OpticAimOffset` z by the same, so on every gun the eye stays where it was in the window and the collimated
      dot where it was on the screen (the survey after it found every other gun's dots unmoved).
    - It also lifts the tags over the cut and the bounds' top in `Sources/MW2022/models/<model>.json`, where the QA
      tools find `tag_reticle_attach`.
    - The rips, records and original offsets are in `Backups/optic_risers_rip/`, which every run starts from. Rerun it
      after `Sources/MW2022/convert_models.py` rewrites these models; `--check` lists what's stale.
  - Solved with `output/reticle-survey-20261018/collimated/m16-cowitness.cs.txt` (`m16-cowitness-risers.jsonl`,
    2026-10-19; `m16-cowitness.jsonl` is 2026-10-18's): the gun turned for the dot by the prefab's correction, then the
    eye stepped with numerical derivatives until the post's tip (on `tag_barrel_attach`, `14.287,0,1.418`; the old
    `13.872,0,1.522` was 0.415 short of the tip) is at its mark.
  - The 2x-6x optics have no line, and haven't been looked at with the post up.
- `hc1_m16_cowitness [optic|all]` (`Editor/Hc1M16OpticQa.cs`) finds the lines: it renders the aimed view, finds the red
  dot in a 9-degree close-up and the post's tip on `tag_barrel_attach` (`14.287,0,1.418`), and steps the line (first
  order) until both are within 0.006 degrees. It writes `output/m16-gunsmith/cowitness.txt`, with `LINE` entries ready for
  `kastov_prefabs.py`, and before/after views (`cowitness-<optic>-{before,absolute,lower-third}.png`). The lens shader
  drew the dot at a virtual depth then, so it moved with the eye: hence the steps, re-rendered each time. Since
  2026-10-18 it looks for the dot along the sight's axis, far off, as the collimated shader draws it. It doesn't keep
  the eye inside the window; the collimated solve above does.
  - In its offscreen scene, a GameObject moved after its first render drew where it was first placed, so the tool moves
    the camera (the eye, at minus the aim offset, turned by the inverse aim angles) and leaves the gun still. Turning the
    optic's ModelRenderers off didn't hide it either.
- `hc1_m16_optic_check [optic] [label]` (default the Box Collimator) checks the optic's bodygroups on both models, with
  the factory barrel and a replacement one, and renders the aimed view (with the M16's line for the optic), a close-up
  round the dot and the world model to `output/m16-gunsmith/optic-<optic>[-label]-*.png`. A cyan ring marks
  `tag_reticle_attach`. It fails unless the dot is within 0.02 degrees of the centre and the post's tip on it or 0.14"
  under it. Since the reticles were collimated its rig applies `OpticAimAngleCorrection` (by reflection) and looks for
  the dot along the sight's axis. On 2026-10-18 the Box Collimator passed (the dot 0.004 degrees off the centre, the
  tip 0.001" under it), and the Mini Red Dot failed as expected (the tip 0.227" over the dot): its rig, the ADS clip's
  pose with no camera bone, agrees with the collimated solve's.
  - On 2026-10-19, with the post and the five optics at real heights, all 13 passed (`optic-<optic>-risers.*`): every
    dot within 0.003 degrees of the centre, the post's tip 0.001" under the six absolute sights' dots and 0.140" under
    the seven lower 1/3 ones'. `output/reticle-survey-20261018/collimated/optic-check-all.cs.txt` (run_csharp) runs it on
    all 13 in turn.
- The weapon prefab's sight lines reach an M16 when it spawns: one already out keeps the old aim. None of it has been
  checked in-game yet.

