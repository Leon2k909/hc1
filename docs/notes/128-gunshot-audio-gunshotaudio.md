## Gunshot audio (`GunshotAudio`)
- The user: gunshots were "far too loud". The guns' sound events fell only 9 dB by 79 m and had occlusion off, so a
  fight anywhere on the map sounded as if it was in the next room. `GunshotAudio.Play` now plays every shot, players'
  and bots', with:
  - the inverse-distance law: full level out to `ReferenceDistance` (160, ~4 m), then 6 dB down every time the distance
    doubles (14 dB at 20 m, 26 dB at 80 m, 38 dB at 330 m), easing to silence over the last tenth of the event's
    `Distance`;
  - air absorption, which takes the top off a far shot, and occlusion, which muffles it through a wall;
  - the blast's directivity: 6 dB quieter straight behind the muzzle, 2.5 dB off to the side.
- The shooter's own shot plays at full level, nearly flat (`SpacialBlend` 0.15).
- Compiled on 2026-09-29, not yet heard in a match.
- Since 2026-09-30 anyone else's shot is heard when its sound gets there, at 340 m/s (`GunshotAudio.PlayDelayed`: 0.3 s
  from 100 m). `PlayDelayed` plays an event as `Sound.Play` does, with `Sound.PlayFile`'s delay. The engine delays a
  sound by holding back its samples, which it can only do once the file has loaded: a file played for the first time
  that hasn't loaded yet plays at once.
- Indoors (a roof within 1200 over the muzzle and walls within 800 round it, `RoomEnclosure`) every shot gets more of the
  engine's own reverb (`Reverb` up to 1). A session on 2026-10-19 also played each shot again 65 ms and 145 ms later as
  "room reflections" (`PlayRoomReflections`). The user, on Ares that day: "sounds like im playing table tennis, the
  shots are so common". Copies that late are past the ear's echo threshold for a bang (~30 ms), so each was heard as
  another shot: at 800 rpm (75 ms a round) the copies fell between the rounds, about three bangs a round. They were
  taken out the same day. A real room's reflections come from every surface at once and blur into its reverb. Compiled
  in the editor, not yet heard in a match.

