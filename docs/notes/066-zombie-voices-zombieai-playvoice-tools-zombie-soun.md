## Zombie voices (`ZombieAI.PlayVoice`, `Tools/zombie_sounds.py`)
- ZombieAI played s&box's `zombie.attack`, `zombie.pain` and `zombie.die`, events the game doesn't have, so zombies were
  silent (the user, 2026-10-01). `Tools/zombie_sounds.py` synthesises their voices with no samples, from a source-filter
  model of a man's voice (its docstring has every layer):
  - groans while they hunt, every 5-12 s;
  - a snarl as they swing;
  - a grunt when hit, at most one every 0.35 s;
  - a groan as they die, the last breath bubbling out.
- Levels are a real voice's against a walk on concrete, squeezed as the rest of the mix is: groans -32 dB, the death
  groan -30, the grunt -29 and the snarl -23.5.
- `sounds/zombies/zombie_{groan,attack,pain,death}.sound`. A re-run rewrites the WAVs and keeps the events.
  `--preview <wav>` plays every take.
- The voice comes from the mouth and follows the zombie (the death groan stays where it fell). One throat, so a new sound
  cuts the last short. Until an event has compiled, the stock name plays, which is silent.
- The editor compiled the WAVs and events as they were written (2026-10-01), but they haven't been heard in-game.

