## The ported guns' sounds (`ported_shots.py`, `suppressed_shots.py`, `ported_foley.py`)
- The user asked for each gun worked on to have its CoD sounds moved towards the real thing, then (2026-09-30) for any
  CoD or s&box sounds left to be changed. So every ported gun's shot, suppressed shot and reload foley is voiced from
  its rip, bar the Kastov-74u's (another session's hand-tuned sounds). Each script's docstring has what the rips get
  wrong and every step.
- Open shots: the AK-105, M16A4 and Kastov 762 have their own scripts (see their sections). `Tools/ported_shots.py`
  voices the Vityaz, Bizon, Vepr-12, P90, MP7A1, AUG, Uzi, FAL, M18, FAMAS, MCX, L85A2, HK416, AK-12, AK-15, AK-74M, MCX-SPEAR,
  M16A2 and RPK-16 with `shot_voicing.py`'s steps, a `Voicing` each:
  - pitch by the charge and the barrel: the 9 mm guns and the P90 2% up, the MP7A1 3%, the FAMAS 1%, the Vepr-12 1%
    down, the FAL 2% down, the M16A2 2% up (as the M16A4's), the AUG, M18, MCX, L85A2, HK416, AK-12, AK-15, AK-74M, MCX-SPEAR and RPK-16 as ripped;
  - a 40 Hz high-pass (the Uzi's 70), the lows eased 3-10 dB after the blast's first 20-50 ms, and the FAL's, Vepr-12's,
    AUG's, Uzi's, HK416's, AK-12's, AK-15's, AK-74M's, MCX-SPEAR's, M16A2's and RPK-16's designed tails eased;
  - the blast's 1.5-5 kHz up 2-5 dB for 20-25 ms (the dark Uzi's 1-6 kHz 7 dB for 30 ms);
  - the ground reflection by the gun's length, and echoes from 35 ms to 1.4 s, as loud against the blast as the
    muzzle's distance from the ear gives (0.4 s after the loudest 100 ms: -31.5 dB for the FAL to -36 for the P90).
  - Loudness stays each rip's. A gun with one recording gets several takes with their own echoes (pitch 0.97-1.03).
- Suppressed shots (`Tools/suppressed_shots.py`): the Kastov 762's, Vityaz's, Bizon's, AK-105's, M16A4's, P90's,
  MP7A1's, AUG's, Uzi's, FAL's, FAMAS's, MCX's, L85A2's, HK416's, AK-12's, AK-15's, AK-74M's, MCX-SPEAR's, M16A2's and RPK-16's. The Vepr-12 and the M18 have none.
  - As ripped they were levelled to each other, not to their guns: 1.4 dB (the Kastov) to 10.6 dB (the P90) under the
    open shot, counting the SMG events' Volume 0.5. The Uzi's WAV was louder than its open shot's.
  - A real suppressor takes about 20-25 dB off at the shooter's ear. Squeezed as the rest of the mix is (0.43 times,
    see RPK), a suppressed shot sits 10 dB under its gun's voiced open shot (`SUPPRESSION_DB`), counting its event.
  - Each is voiced with its gun's open-shot `Voicing`, but with no pitch change or presence lift (the can takes the
    crack off) and the lows under 130 Hz eased 6 dB after 25 ms, which takes MW2019's designed thumps (the P90's, AUG's,
    FAL's, FAMAS's and M16A4's) down 2-8 dB. Its echoes sit where the open shot's do.
- Reload foley (`Tools/ported_foley.py`, on `foley_voicing.py`, as the RPK's): the Kastov 762's (its drum and xmag sets
  too), Vityaz's, Bizon's, AK-105's, Vepr-12's, M16A4's, P90's, MP7A1's, AUG's, Uzi's, FAL's, M18's, FAMAS's, MCX's,
  L85A2's, HK416's and AK-12's.
  - Every set's loudest file but the Kastov's was louder than the gun's voiced shot, by up to 4.4 dB (the AK-105's bolt
    pull).
  - Now: a 90 Hz high-pass; the moves' lows under 250 Hz eased 6 dB (`MOVES`, by name; the Kastov's and FAMAS's files
    are only numbered, so theirs are listed by number); and one gain per set, so its loudest 100 ms is 16 dB under the
    shot. The sets came down 15-20.4 dB. Mono files stay mono.
- The rips are in `Backups/{ported_shots,suppressed_shots,ported_foley}_rip/<gun>/`. Each script voices from them,
  backing up any file that has no copy there yet, so a rerun writes the same files. After a re-rip, delete that gun's
  backups first. Each gun's assets script (`kastov_sounds.py`, and `ak47_gunsmith.py` for the Kastov's drum and xmag
  sets) calls them after writing those sounds. `ported_foley.py <gun> --list` shows which files count as moves, and
  `ported_shots.py` / `ported_foley.py --preview <wav>` play the rip and then the voiced sounds.
- Made offline on 2026-09-30 with the editor closed. The WAVs and the fire events need compiling, and none of it has
  been heard in-game.

