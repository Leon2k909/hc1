## AK-105 (MWII's "Kastov 545", mg_iw9_akilo105, addon 3499492742)
- The real 5.45x39 AK-105 carbine under its real name, all figures from the AK-102/104/105 manual
  (`kastov_prefabs.gameplay_ak105`): 600 rpm, auto and semi, 30-round mag, 7N6 at 840 m/s from the 314 mm barrel
  (G7 0.157), front post 48.5 mm over the bore, zero 300 m (sight 3 hitting 16 cm high at 100 m). At 3.5 kg loaded
  it weighs what the M4 does: SpeedPenalty 40, no WeightSlowdown, 0.25 s ADS. Damage and falloff are the M4's 5.56
  ones, like the 74u's. The recoil scale (1.54,3.85) is the M4's (2,5) scaled by free recoil (1.43 against 1.86 m/s).
- Materials and sounds are from `Tools/ak105_assets.py`: its own shot and suppressed shots (-3 dB, to the 74u's level)
  and reload foley at the viewmodel QC's event frames.
- Its shot is voiced away from CoD's sound design (`Tools/ak105_shot.py`, 2026-09-29). The user asked for one gun's
  sound to be "more realistic and different from cod", slightly, then for another gun's (see M16A4). The steps are
  `Tools/shot_voicing.py`'s, shared by both guns, with each gun's settings (a `Voicing`) and findings in its own script.
  - The rip's shot is designed: a 27 Hz sub drop ringing 300 ms under the blast, clipped almost square, and dry.
  - Now: 3% higher; a 40 Hz high-pass, and the thump under 110 Hz eased 5 dB after the first 35 ms; the blast's
    1.5-5 kHz up 4 dB for its first 25 ms; a ground reflection; and echoes from 35 ms to 1.4 s, different in each ear.
  - The tail sits where the M16A4's and AUG's do (-33 dB 0.4 s after the loudest 100 ms). Loudness matches the old
    shot's within 0.2 dB (K-weighted, loudest 100 ms), through a soft clipper, since the limiter alone ducked the blast.
  - The two recordings make four takes (`ak105_shot_01-04.wav`), and the event's pitch spread is 0.98-1.02.
  - The suppressed shots are voiced from the same settings (see The ported guns' sounds).
  - `--preview <wav>` writes the old and new shots and eight-round bursts. The old WAVs and event are in
    `Backups/ak105_shot_rip/`.
  - Made with the editor closed: the WAVs and `ak105.fire.sound` need compiling (03 and 04 are new), and it hasn't
    been heard in-game.
- Parts (`PARTS_AK105`, `Assets/gunsmith/ak105/`): the AK-platform stocks and grips, with the 74u's materials, and the 20-,
  RPK-74 45- and four-column 60-round mags, each with its own reloads (`reload_variants` `_smag`, `_xmag`, `_xmaglrg`;
  the rip names the 60's empty reload `reload_xmaglrg_empty`, which `port_kastov.clips` falls back to). Reload times
  are when the gun is level again: 2.3/2.6 s for the factory 30, then 2.05/2.3, 2.4/2.75 and 2.5/2.8. Stock recoil is
  relative to its factory stock, the AK-74M's side-folder (the Polymer Folding Stock part).
- The folding stock's hinge block is its own bodygroup (`stock_hinge`, shown by default). The Wooden and Thumbhole
  stocks hide it through `Part.bodygroups`, as the addon's do (`tag_stock_hinge`).
- The left hand holds the handguard through MW's grip pose (`Weapon.grip_pose`): the barrel's
  `a_delta_barhvyshort_additive_for_offset` minus its corrective, layered on while the hand is on its grip, with
  GRIP_FADE's fade (`Kastov.with_grip_pose`). It needs no `GripFit`: the idle left hand sinks 54 vertices, at most
  0.10", like the verified 762's.
- Optics sit on the rail mount (`optic_rail`, shown only under an optic). Its `OpticAimCorrection` `3.18,0,-1.269` is
  derived with the Bizon's formula, NOT checked in-game. The iron sights (ads_in's last frame, post centred in the
  U-notch) were checked in a render, not in-game.

