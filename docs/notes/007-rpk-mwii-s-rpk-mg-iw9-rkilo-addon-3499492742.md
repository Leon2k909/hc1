## RPK (MWII's RPK, mg_iw9_rkilo, addon 3499492742)
- The real 7.62x39 RPK LMG (category LMG, 3 spare mags): 600 rpm and the Kastov 762's shot sounds
  (`kastov_prefabs.gameplay_rpk`). The factory magazine is MWII's 75-round drum; its parts (`PARTS_RPK`,
  `Assets/gunsmith/rpk/`) are the RPK's own 40-round box mag, the AKM's 30, and the AK-platform stocks and grips.
  Recoil scales are relative to its wooden club-foot stock. Left out: the 100-round drum and the other barrels.
- CoD's `ads_in` leaves the RPK's camera pitched and rolled, with the front post 0.8 deg under the aim point, so
  `kastov_weapons.RPK.aim` levels it on the post's top. That was checked in a render, not in-game.
- Its weight effects are real-world figures, sourced in `gameplay_rpk` and `kastov_weapons.RPK`, not balance knobs:
  - It keeps the rifles' SpeedPenalty 40, plus `Equipment.WeightSlowdown` 0.03 for the extra 3 kg (all gaits 3% slower).
  - Aiming in takes 0.3 s (`Weapon.ads_time`, written to the viewmodel prefab's `ViewModel.AimTime`) instead of the
    rifles' 0.25 s.
  - `BarrelHeat`: per-shot heating and Newton cooling. Past ~200 C above the air there's a small heat dispersion, and a
    chambered round cooks off at ~410 C, which takes ~280 rounds of nonstop fire.
  - No extra sprint-to-fire delay. In real life the weight shows up as a slower mount, which ads_time already covers,
    and a second penalty would count it twice. The user wants it left out.
- HC1's hand is thicker than CoD's, so on the RPK's wooden handguard the palm heel and thumb sank 0.39" in.
  `Weapon.left_grip` (`GripFit`) moves the left arm out and opens the fingers while the hand is on its grip, fading
  out when it leaves (`port_kastov.GRIP_FADE`, reloads). Tune it by skinning the arms against the gun mesh and counting
  hand vertices inside it (the verified 762 has 52, at most 0.10" deep).
- Magazines with their own reload animations: `Weapon.reload_variants` (`_mag`, `_xmag`) ports `reload<suffix>` and
  `reload_empty<suffix>`, and the animgraph picks them by the enum `reload_variant` (0 = the weapon's own). A
  magazine part sets `GunsmithPart.ReloadAnimation` (1-based index into reload_variants) plus its own
  ReloadTime / EmptyReloadTime / ReloadSounds / EmptyReloadSounds (`Part.reload_variant`, `Part.reload_times`;
  sounds from `rpk_assets.json` "reloads"). `Equipment.ReloadMagazine` hands it to `Reloadable` and `ViewModel`.
- The shot it shares with the Kastov 762 is voiced away from CoD's sound design (`Tools/kastov762_shot.py` on
  `shot_voicing.py`, 2026-09-30), like the AK-105's and M16A4's. The user asked that each gun worked on gets some of
  its CoD sounds, shot or reload, moved towards the real thing.
  - The rip is MW2019's AK-47 close shot mixed with CoD's "atmosphere" layer. That layer opens with a 45-180 Hz boom
    as loud as the blast's midrange, then washes out over 4.7 s like a hall. Under the close shot a designed rumble
    under 150 Hz runs on for a second.
  - Now it's the close shots alone:
    - 2% lower, for the 7.62's heavier report;
    - a 40 Hz high-pass, and under 130 Hz eased 6 dB after the first 40 ms;
    - the rip's own sound eased 10 dB from 110 ms, after the bolt carrier's clack at ~92 ms, which stays;
    - 1.5-5 kHz up 2 dB for 20 ms, and the ground at 7.1 ms;
    - echoes from 35 ms to 1.4 s, as on the other voiced rifles.
  - Loudness is within 0.1 dB of the old shot's. The tail is -32.5 dB 0.4 s after the loudest 100 ms (the rip's was
    -22).
  - Four takes (`kastov_shot_01-04.wav`, 04 new), pitch spread 0.98-1.02. The suppressed shots are voiced from the
    same settings (see The ported guns' sounds).
  - `kastov_sounds.py` builds the shot through it. `--preview <wav>` plays the old and new shots; the old WAVs and
    event are in `Backups/kastov762_shot_rip/`.
- Its reload foley is voiced too (`Tools/rpk_foley.py` on `Tools/foley_voicing.py`, 2026-09-30).
  - As ripped, the drum going in and the bolt being charged were louder than the shot (loudest 100 ms -1.2 and -1.6 dB
    against -4.7). The drum's seating was clipped flat for 50 ms at a time, and the draw and the gun's return to the
    shoulder boomed at 45-90 Hz.
  - Now:
    - a 90 Hz high-pass, which takes the booms 17-20 dB down;
    - the moves' lows under 250 Hz eased 6 dB;
    - one gain for the whole set (-19.5 dB), so the loudest clack is 16 dB under the shot and the rip's balance between
      the files stays.
  - The level comes from rough real figures at the ear (a shot ~137 dB(A) over 100 ms, a reload's loudest clack ~100,
    a walking footstep ~63), squeezed the way the game's mix squeezes the shot-to-footstep gap (74 dB to 32).
    `foley_voicing`'s docstring has it.
  - The 30-round magazine used the 74u's events. It now has its own voiced copies (`rpk.ak_*`, `rpk_assets.own_name`),
    and `att_vm_p04_ar_akilo_mag_v0.gnsmth` points at them, as `kastov_prefabs.py` would write it. The 74u's own
    sounds are unchanged.
  - The other ported guns' reloads were voiced the same way afterwards (see The ported guns' sounds). Only the
    Kastov-74u's are still at CoD's level.
  - `rpk_assets.py --sounds-only` rebuilds the sounds without the materials. `rpk_foley.py --preview <wav>` plays the
    shot and both drum reloads, before and after. The ripped WAVs are in `Backups/rpk_foley_rip/`.
- Both were made offline: the WAVs, the new events and the part need compiling, and none of it has been heard
  in-game.

