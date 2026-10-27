## Cloud sessions can't upload LFS files
- From a cloud session the network policy refuses `github-cloud.s3.amazonaws.com`, where GitHub keeps LFS objects
  (2026-10-05, and earlier for Railhead's atlases). Every `.wav`, `.png`, `.mp3`, `.fbx` and compiled model or
  texture goes through LFS (`.gitattributes`), so a cloud session can't commit new ones. Downloads work
  (`git lfs pull --include=<path>`). Deleting LFS files works too: it's only a commit.
- So when the user asked for the remaining s&box, original-project and CoD sounds to be replaced (2026-10-05), they
  called it off rather than have the WAVs go into plain git. The audit found what's left:
  - CoD rips: all 16 ported guns' shots, suppressed shots, reloads and raises (~530 events), the Kastov-74u's unvoiced.
  - The original project's: the M4A1, MP5, SCAR-H, USP, USP-SD, M700, Spaghelli and 1911 shots and reloads, the swb
    suppressed shots, the swb guns' sounds, the C4's beeps and `loot_box`, the cash bag's and drone's draw
    (`weapon_switch`), the drone's flight loop, Zombies' buy chime and power-up sting, and the spent-casing fallback
    bounce (`shell_case_bounce`).
  - s&box's own, by name: `impact-bullet-generic` (swb's impact fallback), `footstep-concrete-land` (the player's
    `LandSound` fallback), `impact-melee-metal` (`grenade.surface`), `explosion_small` (`tec/explosion_med_tec`),
    `countdown.beep` (`c4_planting_beep`), and the soundscape's `birdchirp`.

