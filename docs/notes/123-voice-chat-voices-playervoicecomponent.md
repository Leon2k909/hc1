## Voice chat (`Voices`, `PlayerVoiceComponent`)
- The user asked for a list of who's talking and their team, not just a mic icon. That icon, the green rounded square
  at the top right, is s&box's own (`MicOverlay` in the menu addon's `MenuOverlay`). s&box draws it over every game,
  lit while your mic hears you, and a game can't hide it.
- `Voices` (MainHUD's right column, above the weapon) has one plate per speaker, like the kill feed's:
  - a level meter (`VoiceMeter`), the Steam avatar ringed in the team colour, the name, and the team's crest, then an
    edge bar in the team colour at the screen edge;
  - under the name, the team's name in its colour (or SPECTATOR), with chips for ENEMY (the other team from you),
    SQUAD (your Steam party, as the scoreboard marks it) and DEAD (their body is still down). Free-for-all shows no team.
- Your own row shows while your mic hears you (`Application.IsMicrophoneRecording`):
  - `Voice.IsRecording` can't be used: it's only whether the mic is open, which is all the time without push-to-talk.
    Your voice never plays back to you, so `LastPlayed` doesn't work either.
  - It says YOU and who hears you, by `TeamVoiceChatFilter`'s rules: TEAM ONLY, PARTY ONLY, EVERYONE or NEARBY
    (proximity voice). `TeamVoiceChatFilter.ActiveMode` settles Auto for both the filter and the row.
- Other players' rows show while their voice has played in the last 0.4 s. The meter follows `Voice.Amplitude` (the
  playing sound's) times 4, a gain not yet tuned against real speech. Your own row has no amplitude, so its bars sway at
  a steady level.
- Mutes:
  - `Voice.ExcludeFilter` runs on the speaker's machine, but the scoreboard's voice mute is kept on the listener's, so
    muting someone did nothing.
  - `PlayerVoiceComponent.ShouldHearVoice` now drops a muted player's voice as it arrives: the engine asks it, with
    `Rpc.Caller`, before playing.
- `dev_voices_sample` adds made-up rows (you, a squadmate, a dead enemy, a spectator) to check the layout.
- Not yet checked in-game. The list, the meter's gain and the mute fix compiled (2026-09-28), but nobody has talked with
  them yet.

