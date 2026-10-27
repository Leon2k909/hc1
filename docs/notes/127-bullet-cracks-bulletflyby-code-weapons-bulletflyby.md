## Bullet cracks (`BulletFlyby`, `Code/Weapons/BulletFlyby.cs`)
- The user asked for "hyper realistic supersonic cracks at the right distances and everything" (2026-09-30). A round
  that passes someone is heard as it really is:
  - A supersonic round's crack: its Mach cone sweeping over them, an N-wave a few hundred microseconds long.
  - A subsonic round's whizz, within 6 m: the .45s, and the 9x18 Bizon.
  - Then what it strikes, once it's got there and the sound has come back.
  - The report from the gun comes at the speed of sound too (Gunshot audio), so downrange the crack comes first and the
    gap grows with the range: the crack-thump soldiers judge a shooter's distance by.
- Where and when:
  - The crack leaves the path where the cone through the listener meets it, `miss / sqrt(M^2 - 1)` before the point
    nearest them, at the Mach number the round had there (`TryShock`, solved by halving). So it's heard from there, not
    from the gun.
  - It arrives at the round's time of flight to that point plus the sound's way from it. The speeds along the path are
    the load's (`Ballistics.Trajectory.Speed`, solved with the drop table), so a crack weakens and lengthens downrange.
  - There's none beside or behind the gun, past where the round stopped, more than 100 m off the path, or where the
    round is under Mach 1.03.
- How loud and how long: Whitham's far-field N-wave, which measured small-arms cracks follow:
  - overpressure `0.53 p0 (M^2 - 1)^(1/8) d / (b^(3/4) l^(1/4))`;
  - length `1.82 M b^(1/4) d / (c (M^2 - 1)^(3/8) l^(1/4))`;
  - for a bullet of diameter d and length l passing b away (at least 0.15 m).
  - An M855 a metre away is ~985 Pa (154 dB peak) for ~106 us; 20 m away, 104 Pa (134 dB) for 224 us. A 9 mm round is
    about as loud and twice as long, a duller snap.
  - A full-scale sample stands for 356 Pa (`FullScalePascals`: the shots' mastering puts a full-scale sine at ~142 dB
    SPL). So closer than about 3-5 m a crack is capped at full scale, well under a real one.
  - The engine's distance falloff is off for it, but air absorption and occlusion are on.
- Reflections: the ground under the listener, a ceiling over them and the nearest two walls (eight probes 30 m out, kept
  for 0.25 s) each send a second crack (`PlayReflection`).
  - Each is the crack that reaches the listener's mirror image in the surface, played from the mirror image of where it
    left, and only if the wave's way to the surface is clear and the listener can see the spot.
  - Hard surfaces send back 0.9 of the pressure. Grass sends 0.45, earth 0.6 and cloth 0.3, with a rounded front.
  - Standing on hard ground, that's the real "double crack".
  - Only the first pellet of a shot gets them.
- The sounds are made at runtime, not recorded, and cached by name for the session (`SoundFile.FromPcm`,
  `hc1/flyby/...`):
  - Cracks: an N-wave drawn at 16 times 44.1 kHz and band-limited to 20 kHz (`MakeCrack`), in 21 lengths from 40 us,
    20% apart.
    - Each has a sharp, firm, spiked (turbulence focusing it) or rounded front. It's rounded more often the further it
      came (`PickFront`: 10%, rising to 60% at 60 m).
    - The soft front is only for grass and earth's reflections.
  - Whizzes: band-passed noise heard through the Doppler shift as the round comes and goes (`MakeWhizz`). The level
    grows with the speed cubed and the diameter, and falls with the miss: 0.05 of full scale at 1 m for a .45.
- Networking:
  - `Shootable.Shoot` records each pellet's path: from the aim ray to the last thing it met that wasn't glass, or its
    full range. `SendFlybys` broadcasts up to four of them, unreliably (`DoFlybyEffects`, a `ByteStream`).
  - Everyone but the shooter hears them pass. Everyone but the owner's machine, which played its own impact effects,
    hears them strike.
  - The shooter's own impacts are delayed the same way (`ImpactSoundDelay`).
  - Bots' shots call `BulletFlyby.Pass` in their `DoShootEffects`, which now gets whether the shot hit. A miss flies on
    to the gun's `MaxRange`.
- The path is taken as straight from the aim ray to where the round stopped, so drop is left out (a few cm off at the
  ranges a crack is heard). The bot's rounds leave from its muzzle.
- Scattered tail (`PlayScatter`, 2026-09-30): the patches of ground, wall and ceiling the cone sweeps each throw a
  little of it back every way, not only the mirror bounce. That's the rattle after a real crack.
  - Each reflector is taken as a plane. Its energy is summed over a grid of patches round the path's point nearest the
    listener: along the path and across it (up a wall), finest near the path. The ground's grid is 14 x 11 patches out to
    60 m back, 120 m ahead and 30 m to each side.
  - A patch of area A sends `s E cos i A cos o / (pi r^2)` to the listener r away, where E is the wave's energy there
    (its own `TryShock`, 16 halvings) and s is the surface's scattering coefficient (`Reflector.Scatter`: hard ground
    0.12, walls 0.25, earth 0.14, grass 0.1, cloth 0.05). That's Lambert's law. It arrives when the wave got there plus
    r / c.
  - The energy is binned by arrival into five windows (0-6, 6-20, 20-60, 60-180 and 180-600 ms after the direct
    crack). Each window plays as one grain (`MakeScatter`): rounded cracks of the patches' mean length (soft off grass
    and earth), coming at random ~6000 a second with Gaussian weights, fading over the window's own decay.
  - Each grain plays from where its energy came from. The more evenly it comes from all round, the less it's placed
    (`SpacialBlend` is the length of the energy-weighted mean direction).
  - The tail is as loud against the direct crack as it really is, less the direct crack's share when that was capped.
    Over hard ground it's 10-15 dB under the crack (K-weighted, loudest 100 ms), 17 dB at a 0.5 m miss. Most of it
    comes within 50 ms, and at a 30 m miss it lasts ~150 ms.
  - It's worked out for the first pellet only, and at most once every 60 ms (`TailInterval`). Surfaces aren't traced
    past where the probes met them, so a wall is taken to run on ±30 m. Trees and props scatter nothing.
- The ear's acoustic reflex (`AcousticReflex`, `Code/GameLoop/Audio/AcousticReflex.cs`, 2026-09-30): after a loud enough
  sound the stapedius muscle stiffens the middle ear, which dulls what follows.
  - It's set off by the crack's real energy over the ear's ~200 ms integration, whatever level the crack plays at: an
    ~85 dB threshold, and full strength 25 dB over it. A 1 m miss is ~116 dB (full strength), 20 m ~100 dB and 100 m
    ~91 dB.
  - It starts 30 ms after a strong crack and 120 ms after a weak one, so the crack itself goes in whole. It peaks
    ~60 ms after that and has let go within ~0.5 s.
  - Cracks arriving within 50 ms of each other (a shotgun's pellets) add their energies.
  - At full strength `ReflexProcessor` takes up to 15 dB off the lows: ~13 dB at 500 Hz, 9 at 1 kHz, 5 at 2 kHz and
    under 2 above 4 kHz. It's two first-order low shelves at 2 kHz on the Game mixer (every world sound: the reports,
    impacts, footsteps and the tails). The UI, music, radio and voice mixers aren't the character's ears, so they're
    left alone. It's added the first time a crack sets it off, and at rest it passes the sound through untouched.
  - The latency, twitch times and threshold are textbook figures, first guesses to tune by ear.
  - Not modelled: the reflex from the player's own shots, a nearby report or explosions. It would dull the mix after
    every shot the player fires, a big change to how the guns sound, so it's left for the user to decide.
- `Tools/bullet_cracks.py` replicates the crack synthesis and levels offline, and `python Tools/bullet_cracks.py <wav>`
  writes an M855's cracks at 1-50 m with each front. `--scenes <wav>` writes an M16A4 fired from 100 m and 300 m
  missing by 0.5-30 m. Each scene has the crack, its ground reflection and the ground's tail, then the report, at the
  game's levels and delays. It plays twice: first without the tail and the reflex, then with them. It prints how loud
  each part is.
  None of it has been heard in-game: not the levels, the reflections, the tail, the reflex, the whizz, or the delayed
  reports and impacts.
- Checked against the report (2026-09-30, `--scenes`; the user asked whether it really sounds right), K-weighted, loudest
  100 ms:
  - Before the tail and the reflex: fired from 100 m, a 1 m miss's crack was 9 dB over the report, and from 300 m
    19 dB. In the field it's roughly 15-25 dB and 25-35 dB. The crack's energy is Whitham's; the report's real level at
    range is the uncertain part, +-5 dB.
  - Close in, the gap is because a crack is only 4-6 samples long at 44.1 kHz, so full scale holds its energy down, and
    0.5 m and 1 m misses sound the same. A soft clipper doesn't help (tried: under 1.5 dB, since band-limiting so short
    a wave puts its peak back). From ~10 m out it's within a few dB of real.
  - With them, from 100 m the reflex is at 0.66-0.72 of full when the report arrives, 150-180 ms after the crack, and
    takes 4.4 dB off it (at a 30 m miss 0.46, 3.9 dB). A 0.5-3 m miss's crack is now 13.5-13.9 dB over the report,
    10 m 7 dB, 30 m 1 dB.
  - From 300 m the report comes ~0.5 s after the crack, when the reflex has let go (0.08), so the gap is as it was:
    +19 dB at 1 m.
  - The lever left, the user's call as it changes the whole mix: the reports' level. `GunshotAudio` holds the shooter's
    own level out to 4 m, and a real rifle's blast in front is roughly 7-10 dB under what the shooter hears.
  - The game has no reverb for `ReverbEnabled` to use, so the tails and reflections are the only room the cracks get.

