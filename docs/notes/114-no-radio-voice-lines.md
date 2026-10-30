## No radio voice lines
- The user had every radio voice line deleted (2026-10-05): the 39 events and 118 MP3s in `sounds/radio/`, and
  `radio_sounds/terrorist.radio` and `counter_terrorist.radio`, which listed them.
- `RadioSounds.Play( team, RadioSound )` does nothing now, and the radio menu's callouts (`Play( team, category,
  sound )`) only put their text in team chat ("Planting bomb", "Defusing the bomb"). Don't put the playback back.
  - Compiled files are git-ignored, so a machine that had the lines keeps its compiled `.radio_c` and `.sound_c` after
    a pull, and a compiled file with no source still loads. Without the playback, those can't play.
  - Delete the leftover `Assets/radio_sounds/` and `Assets/sounds/radio/` folders locally to tidy up.
- The callers stay, so nothing else changed: `PlayRadio` (in the game-mode prefabs), `PlayRadioOnKill`, the
  grenade throw's call in `Throwable`, the Radio volume slider and the Radio key (the radio menu, `Radio.razor`, is
  already out of MainHUD). Not compiled or checked in-game.

