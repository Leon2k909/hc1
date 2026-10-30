## No start sting
- The user didn't like the noise when a game starts, so on 2026-09-28 the music sting
  (`sounds/music/round_intro/round_start.sound`) came out: the `Facepunch.PlaySound` component that played it in every
  game-mode prefab, and Zombies' call in `StartNextRound`. Don't put them back.
- The radio's ~2 s RoundStarted voice line is off too (2026-09-30, the user: "i dont like the talking when i first spawn
  in"): its `Facepunch.PlayRadio` component is disabled (`__enabled: false`) in all nine game-mode prefabs that had one.
  Don't turn it back on.
- Still there: the same sting when a Zombies power-up is picked up (`ZombiesRoundSystem`).

