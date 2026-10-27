## Rain (`Weather`, `RainView`, `Code/World/`)
- Weather progression update (2026-10-14, the user reported Lowtide always staying clear and asked for slight changes
  during matches): outdoor matches sample one wet match in each randomized block of four per map on the host, for
  the process's lifetime. This keeps the 25% share and permits at most six consecutive clear matches between blocks.
  - Fair-weather cloud cover changes smoothly over 5-8 minutes, with at most 11% daylight shading. Lowtide's cloud
    drift uses the synced match clock and its density follows the seeded cover profile.
  - Half of drizzle/steady fronts are already present; the others arrive 1.5-5 minutes into play. Rain builds over
    two minutes, starts easing off at 8-14 minutes of match time, and clears over three minutes. Cloud comes ahead
    of the rain and clears after it. The visual look approaches its target over 90 seconds.
  - Lowtide blends its moving coastal sky smoothly into a grey deck, using a private runtime material copy. Other
    maps retain the existing overcast material. Clear weather keeps a lightweight view, releases all rain effects,
    restores calm wind and leaves the authored sky asset unchanged.
  - Verified in native-engine isolated scenes: 4000 match choices kept exactly 1000 wet matches; all 256 tested seeds
    varied smoothly; clear/rain/clear created 0/3/0 particle effects; authored sky, sunlight and calm wind restored.
    Lowtide renders at 49% and 51% overcast showed a continuous sky transition. C# and material compilation passed.
  The older notes below describe the original system; the timing and sampling above supersede them.
- The user asked for the maps to rain sometimes (2026-10-08). A quarter of matches rain (`Weather.RainChance`). Of those,
  a quarter are drizzle, two fifths steady rain and the rest showers.
  - Drizzle is 0.2-0.8 mm/h and steady rain 2-6 mm/h, each wandering about 30% over minutes.
  - Showers come 10-90 s in, then last 3-8 minutes with dry gaps of 3-10 minutes. Most are moderate; a few reach
    40 mm/h. The sky stays overcast in the gaps.
  - Rain comes with a front's wind (`WorldWind`, on the calm's heading): 2-4 m/s in drizzle, 3-6 m/s in rain, gustier
    in showers.
  - A map with no sky (Reef Hall) never rains.
- The host rolls it once the map has loaded (`Weather.Ensure`, from `GameMode.OnStart`). Only the kind, a seed and the
  time are synced: every machine works the rate out from them (`Weather.Schedule`).
- Each machine that draws makes a `RainView` round its own camera. Nothing in it is networked.
  - Drops (`RainDropParticles`, up to 10,000 in three rings out to 900): sizes from Marshall and Palmer's spread for
    the rate, each at its size's terminal speed (4 m/s at 1 mm, 8.7 at 4 mm), drifting with the wind's gusts. More of
    them show the harder it rains (`ActiveShare`: 800 at 1 mm/h, 2,100 at 5, 5,500 at 25).
  - How a drop is drawn (2026-10-09, the user: "the rain looks a little fake"):
    - a streak as long as it falls in 1/60 s, one frame at 60 fps (it was ~45 ms, then 1/30 s);
    - blurred by an eye's depth of field (a 4 mm pupil focused at 15 m), so a near drop is a soft, wide streak;
    - never under a pixel and a half wide (it was two), and fainter by as much as it's widened, so a far drop is a
      faint thread and a near one a clear streak;
    - each a little brighter or dimmer than the next (0.55-1.45), as drops catch the light differently;
    - covering at most 35% of what's behind it (`MaxAlpha`; it was 60%).
    - The middle and far rings hold 10 and 70 times fewer drops to the cubic unit than the near one, so each of their
      drops is drawn 1.6 and 2.4 times as strong (`Layers`' weight), far short of the 10 and 70: past 15-20 m nobody
      makes out single drops, and the fog does the rest. At 2.5 and 5.6 the far ones read as bright threads.
  - Their colour (2026-10-09, the user: "it has like white lines coming down"). The drops were a light grey (0.75),
    about 3.4 times as bright as the overcast horizon they fell against, so they read as white lines. Water shows what's
    round it: a drop refracts the scene behind it upside down through ~165 degrees, half sky (1-1.67 of the horizon in
    `rain_sky.py`'s sky) and half wet ground (0.32), plus a few per cent reflected.
    - So each is drawn in a share of the rain's haze (`RainView.Haze`: the fog's horizon grey, lit by lightning as the
      fog is): drops 0.85 (`DropShade`), splashes 1.0 and the puddles' rings 1.3, whose tilted crests reflect sky
      higher up.
    - A drop is a little darker than the sky round it and a little brighter than a dark wall behind it, never white.
  - The user asked for no rain on the camera: no drops on the lens or the screen, no screen-space pass. Everything is in
    the world.
  - Shelter (`ShelterGrid`): 32-unit columns round the camera, each probed with a trace down and one up. Drops show only
    over open sky and above where they'd land, so none fall indoors, under a roof or through a floor. A hit on the
    map's sky brush or its lid counts as sky.
  - Splashes (`RainSplashParticles`): a crown for each drop over 1 mm that lands on open, level ground in view
    (`DropFlux`: about 730 a square metre a second at 5 mm/h).
    - Within a core radius every drop gets one, and past it, out to 900, a share (r0 / r)², each drawn stronger for the
      ones it stands for (`CoreRadius`). That comes to 30,000 a second (`SplashBudget`): at 5 mm/h every drop within
      ~3 m. It was 2,500 a second within ~13 m, by a made-up curve.
    - A crown spreads to 5-9 times its drop's width and is gone in 25-110 ms, bigger and longer for bigger drops. Each
      particle's `TimeScale` runs its age 0-1 over its own life, under the effect's Lifetime of 1, so a short-lived one
      doesn't hold its slot.
    - Places tried that aren't open ground in view are skipped, and the budget is raised by the share that are.
  - Rings on the puddles (`RainRippleParticles`): a ring for each drop over 0.5 mm that lands on a puddle's water in
    view, flat on the water (the sprite renderer's `Particle` alignment, anisotropic filtering).
    - It starts in a random wet cell of the puddle's shape (`RainPuddles.WetOrder`), on the ground's slope there
      (`Water.PointAt`), and spreads at a capillary wave's ~0.2 m/s, with two fainter ripples inside its crest.
    - It fades over 0.2-0.6 s (bigger drops longer), sooner where the water's edge is near: `PuddleShapes` (generated by
      `Tools/puddle_textures.py`, `--code-only` from the height maps it wrote) says how far round each cell is under
      water at each fill.
    - At most 6,000 a second: past a distance a share (reach / d)² of the drops get one, drawn stronger.
  - Sound (`Tools/rain_sounds.py`, synthesised): light (2 mm/h) and heavy (20 mm/h) loops crossfaded by the rate
    (`MixWeights`). They get quieter the less open sky there is round you, and a loop of rain on a roof plays while one
    is over you. Light rain sits 5.5 dB under the walk on concrete and heavy rain at about its level.
  - The look (`RainLook`), easing in over 20 s:
    - the sky becomes an overcast panorama (`Tools/rain_sky.py`, `materials/weather/overcast_sky.vmat`), swapped at
      halfway, and darkens in heavy rain;
    - the sun drops to a third of its light in drizzle and about a seventh in a downpour, and goes grey;
    - the fog closes in to rain's visibility (8 km dry, ~3.3 km at 5 mm/h, ~1.6 km at 25 mm/h);
    - the reflection probes lose the clear sky's blue.
    Every value is put back when it clears. Cloud maps' baked lighting isn't changed, so their shadows stay.
- Fire: rain wets dead grass (`Weather.FuelWetting`, on the host). A tenth of a millimetre slows a grass fire, and
  about half a millimetre stops it running (`FireFuels.HeadRate`). Thermite still burns.
- `dev_weather [clear|drizzle|steady|showers] [mm/h]` (host) sets it. With a rate it holds at that rate; with none it
  follows the kind's schedule. With no arguments it logs the weather now.
- It has rained before the match too (`Schedule.RainStart`): a front's rain set in 10 minutes to 2 hours earlier. Seven
  showery matches in ten had a shower in the hour before, ending 5 minutes to an hour before the start. The puddles go
  by that history.
- Thunder and lightning (the user asked for them after the rain, 2026-10-08). `Weather.Schedule.Strikes` lists the
  match's flashes from the seed, so every machine has the same ones. Nothing new is synced.
  - A shower that peaks over 12 mm/h is a thunderstorm's. Its cell drifts past at 6-14 m/s, closest 0.5-6 km off when
    the rain's heaviest. It flashes from 5 minutes before its rain to 3 after, mostly in its middle: half a flash to
    three a minute, by its peak. Three in five flashes stay in the cloud.
  - One steady rain in three has storms embedded far off: a flash every 3-6 minutes, 6-15 km off, four in five in the
    cloud. Drizzle has none.
  - The flash (`Schedule.FlashAt`): a ground strike is 2-5 return strokes 35-85 ms apart, each gone in tens of
    milliseconds, with the channel glowing between them. One in the cloud is 3-6 softer pulses over half a second.
    `RainLook.Apply` lights the sky, the sun's sky light, the sun a little, and the fog a bluish white with it.
  - The thunder comes when its sound gets there, at 338 m/s (cool, wet air), from the strike's foot, or from the cloud
    6 km over a flash in it. Past 18 km none is heard (refracted up over the listener); the flash still shows.
  - It plays from the strike's bearing, low over the horizon for a ground strike and up in the cloud for one in it,
    0.6 placed (a long channel, not a point). It follows the camera's place, with no distance falloff or occlusion,
    and indoors it's 0.4 as loud.
  - Three sets, by distance: near under 2 km (the crack and the tearing of the near channel), mid 2-6 km (a peal) and
    far past that (a low rumble). Within its set the level goes as (reference / distance)^0.43, the mix's squeeze.
  - `Tools/thunder_sounds.py` synthesises them (`sounds/weather/thunder_{near,mid,far}`, 3, 3 and 4 takes), after Few's
    model: a tortuous channel at two scales (~80 m runs, then ~4 m ones turning 16 degrees), each bit an N-wave as long
    as its radius gives, summed by its arrival time. On the way: ISO 9613-1 air absorption (11 C, 95% humidity), the
    ground's reflection, a refraction shadow, and the echoes off the land 11-13 dB under. Its docstring has the rest.
  - Levels (K-weighted, loudest 50 ms): near -18, mid -23.5 and far -28, against the walk on concrete's -36. They're
    rough real levels (~100-105 dB(A) at 1 km, ~90 at 3.5 km, ~80 at 9 km), squeezed 0.43 times like the rest of the
    mix. Near thunder keeps some 2-4 kHz; far thunder is all under ~500 Hz. A take is 15-24 s.
    `--preview <wav>` plays every take over the heavy rain loop.
  - `dev_thunder [metres] [cloud]` (this machine only) strikes that far off where you're looking, 1500 m to the ground
    by default. It only shows while it rains.
- Puddles (`RainPuddles`, run by `RainView`). Nothing is networked: where a hollow lies, its size and depth and how much
  ground drains into it come from the seed and the place, and how full it is from the rain's history.
  - The map is cut into 220-unit cells out to 1700 round the camera. A cell has a hollow 1 time in 4 on paving and nearly
    1 in 2 on bare earth. It must be level (normal z 0.985), open to the sky, not water or a moving body, with the ground
    level and the same at 8 points round it.
  - Paving is "default", concrete, stone and tile (`WorldSounds.Classify`'s masonry and tile). Bare earth is dirt, gravel
    and mud. Grass, wood, metal and water have none.
  - Paving's are 20-140 units across and 5-25 mm deep, draining 3-12 times their area. Mud's are 40-180 across and 10-60
    mm deep, draining 4-15 times theirs.
  - How full: dg/dt = 2 (k Rrun + sqrt(g) (R - s)) / Hd, where g is the share of the volume that's full, and sqrt(g) of
    the depth (a bowl). Paving holds the first 0.5 mm, then sheds 85%. Earth soaks 8 mm/h when dry, down to 1 mm/h as
    its top 3 mm wet (Horton). Seepage is 0.5 mm/h through paving and 1.5 into earth.
  - So drizzle puddles paving over hours and never earth, steady rain fills paving's in about a quarter of an hour, and a
    shower puddles both within minutes. They drain over hours.
  - Each is a decal (`decals/weather/puddle_{paving,mud}_{0-2}`, from `Tools/puddle_textures.py`). Its height map is
    the hollow, and `CoverageAmount` is the water's share of its depth, so the edge follows the hollow's contours as it
    fills. The water halves the paving's albedo; muddy water is silt-brown. Its surface is a flat mirror (roughness
    0.02). Puddles fade in over 1.5 s, and out over the last 300 units. At most 192 at once, 6 cells probed a frame.
  - `dev_puddles [fill]` (this machine only) holds every puddle at a share of its depth, 0-1; with none, or below 0,
    they follow the rain again. Puddles only show while it rains.
- Not modelled: wet surfaces (beyond the puddles), splashing through puddles, rain on the gun or the screen (see
  above), and a setting to turn it off. Theater doesn't record it.
- Made offline on 2026-10-08 and compiled with dotnet. The editor hasn't loaded it: nothing has been seen or heard
  in-game. To check: `dev_weather steady 5` on Belltower and Railhead (the sky, the fog, no drops under the shed's roof,
  the splashes, the roof's sound), the frame time with 6000 drops, and a second machine seeing the same weather.
  - The editor compiled the thunder's WAVs and events and the puddles' decals on 2026-10-08 with no errors. To check:
    `dev_thunder` at 500, 3000 and 10000 m (the flash, the delay, the direction, the levels against a gunshot),
    `dev_puddles 0.3` and `1` on paving and on earth (the shapes, the edge following the hollow, the mirror), and a
    showers match's first storm. Whether the height map should be read as linear rather than sRGB wasn't checked.
  - The drops' blur, weights and variance, the splashes' flux and the puddles' rings (2026-10-09) compiled with dotnet,
    with the editor's match running, and haven't been seen. To check: `dev_weather steady 5` and `25` (the streaks near
    and far, the splashes' density, the rings filling the puddles, not past their edges), and the frame time with
    10,000 drops, 3,000 splashes and 3,000 rings.
  - The drops' haze colour, shorter streaks and lower far weights (2026-10-09, after the user's "white lines") compiled
    with dotnet and haven't been seen. To check: the streaks against the sky and against a dark brick wall (neither
    white nor black lines), a lightning flash lighting them, and whether they still show at all in drizzle.

