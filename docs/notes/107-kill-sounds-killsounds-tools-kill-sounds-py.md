## Kill sounds (`KillSounds`, `Tools/kill_sounds.py`)
- The user asked for satisfying kill sounds. The player being viewed hears a kill-confirm for each enemy they kill: a
  short "thwack" (`sounds/ui/kill/kill_confirm.sound`), or for a headshot kill the same with a bright metal ping
  (`kill_confirm_headshot.sound`). `Tools/kill_sounds.py` synthesises both (its docstring has the layers), and
  `--preview <wav>` writes a demo. A re-run rewrites the WAVs but keeps the `.sound` events, which may be tuned.
- Players and bots: `MainHUD`'s KillEvent handler calls `KillSounds.OnKill`. Every machine gets every KillEvent, so it
  checks the killer is the viewer and the victim an enemy player or bot. Zombies raise no KillEvent, so
  `ZombieAI.ShowHitmarker` plays it on a kill (`OnZombieKill`).
- Kills within 3 s of each other (the medals' rapid-kill window) climb 0, 2, 4, then 7 semitones (`KillSounds.Steps`),
  in step with the double, triple and fury kill medals. The viewer's death starts it again. Zombie kills don't climb.
- It plays on the UI mixer, so Settings' UI volume sets it. It replaces upstream's `KillSound` component, which no
  prefab used. Upstream's long, boomy `sounds/kill_sound.wav` and `sounds/guns/kill.wav` are still in Assets, unused.
- Not yet checked in-game.

