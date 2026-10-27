## AK-15 (Escape from Tarkov's AK-12 with its AK-103 magazine, ARC9 EFT Assault Rifles 2962829818)
- The real Kalashnikov AK-15 (6P71, category AssaultRifle): the AK-12 in 7.62x39, with the same receiver, furniture,
  sights and selector on a 7.62 barrel. It's the fourth of the user's list (see L85A2), after the AK-12. No pack has an
  AK-15 of the quality wanted, so it's the AK-12's model and rig (see AK-12) with a 7.62 magazine. No source shows the
  AK-15 with a different brake from the AK-12's, so it keeps the AK-12's. Its figures are in
  `kastov_prefabs.gameplay_ak15`, from Rosoboronexport's catalogue:
  - 700 rpm, with the AK-12's automatic, two-round burst and semi (`BurstAmount` 2, `BurstEndDelay` 0). It starts on
    automatic.
  - PS ball at 715 m/s from the 415 mm barrel, as from the AKM's of the same length (`PS_BALLISTICS`, G7 0.149). The
    sights are the AK-12's on the same receiver, 55.3 mm over the bore, zeroed at 300 m like the AKM's battle zero.
  - The Kastov 762's and RPK's PS damage (26) and falloff.
  - 3.5 kg without a magazine and ~4.24 kg with a loaded AK-103 30 (~0.25 kg, and 30 rounds of 16.3 g). Like the Uzi's
    ~4.2 kg, that's too little over the AKM's 3.75 kg for a WeightSlowdown. So it has SpeedPenalty 40 and 0.25 s ADS.
  - The recoil scale (1.94,4.85) is the M4's (2,5) scaled by free recoil (~1.80 against 1.86 m/s).
  - Reload times are the AK-105's clips', as for the AK-12: 2.3 s, and 2.6 s empty.
  - Bots can be issued it: it's a Primary AssaultRifle, so it's in `WeaponPool` and shares the rifles' half.
- `Tools/ak15_rig.py` builds the AK-12's pieces with Tarkov's AK-103 polymer 30-round magazine.
  - `ak12_rig.py` was split into `weapon_bones`, `add_mesh`, `place_model` and `Rig` for it.
  - The magazine goes where the pack's AK-103 puts it on `mod_magazine` (0, -0.05, -0.25).
  - The 7.62 rounds in its lips are the pack's c_ak100's (`762.smd`). c_ak100 and c_ak12 share their skeleton and clips.
  - It writes `decompiled/ak12/rig/ak15_mag.smd` and the side-on icon `ui/weapons/guns/ak15_01.png`.
  - The magazine's fit was checked against the rig's `j_mag1` / `j_mag2`, not in a render.
- Materials and sounds are from `Tools/ak15_assets.py`, run after `ak12_assets.py` and `rpk_assets.py`:
  - The materials are the AK-12's, plus:
    - the magazine, Tarkov's AK-103, built like the AK-12's;
    - the rounds, Tarkov's `patron_762x39`, greened towards lacquered steel cases like the AK-12's. They come from the
      ARC9 EFT SHARED pack that the Assault Rifles pack requires (Workshop 2917343547), downloaded to
      `extracted/2917343547` for it.
  - The shot is Tarkov's AKM: the same round from the same barrel length. Four 102 ms starts go under the last round's
    tail, mixed at 0 dB, which is the Kastov 762's voiced shot's level (the same round).
    - It's voiced at its own pitch (see The ported guns' sounds): the lows under 130 Hz eased 8 dB after 30 ms, Tarkov's
      tail eased 6 dB from 100 ms, 3 dB of presence for 25 ms, the ground at 6.9 ms and the echoes at -33 dB.
    - The heavy 45-90 Hz is in the blast's first 20 ms, where the voicing leaves it.
    - Four takes, pitch 0.98-1.02.
  - The suppressed shot is Tarkov's four suppressed AKM takes, built the same way, 10 dB under the voiced open shot.
  - The reloads are the AK-12's: the AK-105's clips, with Tarkov's AK-74 charging handle and polymer magazine foley,
    which suit the AK-103's polymer magazine. The AKM 30 part plays them too: it's steel, but uses the factory reload.
- It was ported with markings on, which `Tools/texture_markings/specs/ak15.json` takes off:
  - the magazine's calibre (762x39), a handwritten 13 and a moulded Izhmash triangle;
  - the rounds' headstamp.
  Checked in close-ups of the textures on 2026-10-08, not on the model. Everything else uses the AK-12's materials,
  which are already cleaned.
- Bodygroups (DefaultMask 36885 by the bit rule, not yet read from the compiled models):
  - `muzzle_tip` (2 choices) and `iron_sights` (2);
  - `pistol_grip` (8: the AK-12's);
  - `magazine` (3: the factory AK-103 30, the AKM 30 and the RPK 40).
- These are all the AK-12's:
  - the slots, and 56 of the M4's MWII parts made eligible;
  - the optic correction `3.18,0,-1.032` (derived, NOT checked in-game) and the iron sights' aim;
  - the hands: no `GripFit`, and the left hand's fit wasn't measured again, since only the magazine changed;
  - the fire clip (no `ads_fire`), the sticker and the charm;
  - the third-person left hand (`6.9,2.55,2.23`).
- Parts (`PARTS_AK15`, `Assets/gunsmith/ak15/`), 9 in all:
  - the AK-12's seven grips;
  - the AKM's ribbed steel 30 (`AKM 30 Round Mag`, the factory reload);
  - the RPK's 40 (`RPK 40 Round Mag`): the AK-105 45's clips through `reload_variants` `_xmag`, level again at 2.4 s,
    and 2.75 s empty.
  - Both magazines keep the RPK's materials. `part_masses.py` has its own magazine at 0.25 kg and its own grip at 0.09.
  - The RPK's 75-round drum isn't offered: the AK-105's clips have no drum reload.
- Made on 2026-10-08 with the editor's bridge down: nothing has been compiled or seen in-game.
  - If the first-person gun is invisible or keeps old clips, register its DMX and recompile `v_ak15.vmdl` and
    `v_ak15.vanmgrph` (see the pipeline notes).
  - If the gunsmith doesn't offer the parts, `recompile_asset` the shared ones and its own.
  - Its gunsmith review note stays until all of it has been checked in a match.

