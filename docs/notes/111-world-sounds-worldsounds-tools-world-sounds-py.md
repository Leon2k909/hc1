## World sounds (`WorldSounds`, `Tools/world_sounds.py`)
- The user asked which of s&box's default sounds the game used, then for them to be replaced with sounds as close to
  the real thing as possible, and for every sound to be made that way from now on (2026-09-29): "ultra real 1:1 or
  close enough". Replaced so far: bullet impacts, knife strikes and the knife's swing, grenade bounces, footsteps,
  running steps and landings, and the menus' press and hover.
- `Tools/world_sounds.py` synthesises them from the physics of each event, with no samples. Its docstring has every
  layer and why.
  - It writes `sounds/world/impacts/bullet_<material>`, `sounds/world/knife/knife_<material>` and `knife_swing`,
    `sounds/world/grenades/{frag,can}_<floor>`, `sounds/world/footsteps/{step,run,land}_<floor>` and
    `sounds/ui/menu/ui_button_{press,hover}`: WAVs and a `.sound` event per set.
  - A re-run rewrites the WAVs but keeps an existing event, which may have been tuned. Its takes are seeded, so a re-run
    writes the same WAVs.
  - `--compare <wav>` plays s&box's stock sound, then the new one, for each set (decoded from the s&box install or the
    project's Assets), and `--preview <wav>` every take, with walks, runs, bursts and bouncing grenades. `--out <dir>`
    writes somewhere else, to try changes.
- Impacts: masonry, tile, metal, sheet metal, glass, wood, plastic, dirt, grass, fabric and flesh. Footsteps: concrete,
  tile, wood, metal, dirt and grass. The script's octave spectra were compared with s&box's own recordings, which
  showed the first version had almost no low end.
- The metal impacts were redone on 2026-10-19, after the user played Ares (decks, galleries and the column are the
  `metal` surface): "sounds like im playing table tennis". They rang like a steel target hung on chains: a pitched
  ~1.4 kHz "ping" 0.25 s long over plate modes decaying in up to 0.28 s, 64-72% of the sound after the first 50 ms,
  only 20 dB down after 0.55-0.78 s.
  - Now steelwork built into a structure (`structural_modes`): 64 dense, pitchless bending modes, each dying in
    T60 = 2.2 / (f x loss) with a built-up structure's loss factor of 1-2.5%, weak under the plating's coincidence
    frequency (~1 kHz). A bright crack and a short clank, the frame's brief thud and lead splashing. One take in five
    ricochets (it was two), quieter.
  - Sheet metal the same way, with a panel's loss of 2-6%: a short "pank".
  - The non-ricochet takes are 20 dB down after 80-100 ms, with 6-11% of the sound after 50 ms. In an 800 rpm burst
    the level drops 17 dB between rounds, where it dropped 4.6 dB. Metal sits at -13 dB, 2 dB over masonry (it was -11).
  - Only the metal and sheet metal WAVs and their events' volumes were replaced (`--out` to a scratch folder, then
    copied in), so the other sets' files weren't touched. Compiled in the editor, not yet heard in a match.
- The metal footsteps and grenade bounces were redone on 2026-10-20 (the user, on Ares: "running on the floor ... just
  constant pinging ... maybe too loud"). Ares's whole floor, the ground slab and the decks, is the `metal` surface.
  - Each step rang a hung plate on 16 sparse modes for up to a second (half its sound after the first 50 ms, a pitched
    line 28 dB over the spectrum round it). A sprint steps every 0.25 s (`PlayerFootsteps`), so the rings overlapped
    and the level only dropped 13 dB between steps.
  - Now a boot on a deck (`soft_strike_modes`): a rubber heel's few ms of contact barely reach the plate's upper modes,
    and a plate on its frame or slab, with the boot on it, damps the rest (loss 2.5-5%). A hollow clank, 3-4 dB more
    than concrete at 250-500 Hz, 20 dB down there by 60-100 ms. Its pitched line is 10-14 dB (concrete's 10.5), and a
    sprint goes quiet between steps.
  - A steel deck is now 2 dB over concrete (it was 4): walk -34, run -28, land -24.
  - Grenades on metal had the same ringing plate, 0.4-0.65 s long. They now use `structural_modes` (loss 1.5-3%): a
    bright clank, 20 dB down in ~80 ms.
  - Only the step, run, land, frag and can metal WAVs and their events' volumes were replaced, the same way. The old
    files are in this session's scratch only. Compiled in the editor, not yet heard in a match.
- Ricochets were redone the same day (the user, on Ares: "in the distance i hear pews like im in an action movie").
  - One masonry take and one metal take in five had a whine mixed in: a tonal glide from 2.6-4.3 kHz down an octave
    over half a second, the movie "pyeeow". It played on any hit, at any angle, as far as impacts carry (~76 m).
  - A real round only skips off a hard face struck at a grazing angle, and breaks up on the rest. It leaves at
    250-500 m/s away from where it struck, so it's Doppler-shifted down from the start. The gliding scream needs it to
    come at you and pass close.
  - The impacts have no whine now. `bullet_ricochet` (its own set, -30 dB, heard to 1500 units) is a tumbling slug's
    buzzing wake. It's shifted down, falls 10-20% as it slows, and is audible ~150-190 ms (the old one 570 ms).
    Its tonal line is 10-12 dB over the spectrum round it (the old 16-21).
  - `WorldSounds.BulletRicochet` plays it beside the impact (`Shootable.CreateImpactEffects` for your own rounds,
    `BulletFlyby.PlayImpact` for everyone else's and bots'). It needs a grazing hit: under 15 degrees on metal and
    10 on masonry or tile. The chance is 0.6 times (1 - angle / critical). The dice are a hash of where it struck, to
    the nearest 4 units, so every machine mostly agrees.
  - Checked in the editor on Ares's edited scene (`run_csharp`, real traces): on the steel floor 25-36% ricochet at
    2-8 degrees, 11% at 12, 4% at 14 and none from 20 up. The editor compiled the code (0 errors) and the sounds.
    Not yet heard in a match.
- Levels are real ones against each other, by K-weighted loudness:
  - Masonry impacts stay at s&box's generic impact; the rest are set relative to it.
  - Walking on concrete stays at s&box's; the other floors follow real footfalls: a steel deck 2 dB over concrete,
    grass 10 dB under it. s&box had grass 21 dB under.
  - A run is 6 dB over a walk, and a jump's landing 4 dB over a run.
  - The press sits with `ui_nav_tab`, and the hover 2 dB over s&box's. They're on the UI mixer, so the UI slider
    sets them now, not the SFX one.
- `WorldSounds.Classify` sorts a surface by its name, then its base surfaces' names. "default", which most of a map's
  walls are, is masonry. Water, snow, mud, carpet and anything unrecognised keep their own surface's sounds, and so
  does a set whose event hasn't compiled. On terrain, `SurfaceAt` takes the ground material's surface under the hit,
  as `FireFuel` does.
- Where they play:
  - `Shootable.CreateImpactEffects` plays `WorldSounds.BulletImpact`. Bodies (hitboxes, zombies) sound like flesh
    whatever their colliders' surface is. A living player's body plays nothing there, because
    `PlayerPawn.BloodImpactSound` (now `bullet_flesh`) plays it on every machine; before, a hit played both. That no
    longer plays for fall damage.
  - `PlayerFootsteps` plays the run while sprinting. Someone else's steps are now occluded: s&box's weren't.
  - `PlayerPawn.PlayFallSound` traces the floor and plays its landing (`LandSound` is the fallback). It's louder the
    faster you land: volume times speed / 300, from 0.6 to 2 (a jump lands at ~280 u/s).
  - Every `"ui.button.press"` / `"ui.button.over"` (Sound.Play and scss `sound-in`) is now `"ui_button_press"` /
    `"ui_button_hover"`.
  - Knives (2026-09-30):
    - `Melee.CreateImpactEffects` broadcasts `WorldSounds.KnifeImpact`, so everyone nearby hears the strike. It used to
      be the surface's stock bullet sound, and only the swinger heard it.
    - A knifed player plays `WorldSounds.KnifeFlesh` on every machine instead of the bullet's thwack
      (`PlayerPawn.Health`, by `DamageFlags.Melee`).
    - The swing is `WorldSounds.KnifeSwing` ahead of the prefab's `SwingSound` (upstream's, 19 dB louder, heard to
      5000 units), which stays as the fallback.
  - Grenades (2026-09-30): `BaseGrenade` is a collision listener. On the thrower's machine (it simulates the grenade)
    each bounce broadcasts `WorldSounds.GrenadeBounce` for the grenade's `Body` (`HEGrenade`: Frag, the rest: Can) and
    the surface, scaled by `BounceVolume` (speed^1.2, none under ~1 m/s, at most 2x), at most one every 0.06 s. Once
    the events have compiled, `OnStart` turns off the Rigidbody's own collision sounds (`EnableCollisionSounds`).
    Whether that also silences the engine's sound for the surface it hits wasn't checked: listen for a double knock.
  - Doors (2026-09-30): `prefabs/Door.prefab` (Refinery's doors and the test scenes') played HL2's door sounds from a
    cloud package. It now plays the Ridgeback buildings' synthesised ones (`sounds/buildings/door_open`, `door_swing`
    as it starts to shut, `door_close` when it's shut; see Ridgeback buildings). Innocent Hotel's doors are the cloud
    map's own and keep its sounds.
- Still s&box's, upstream's or not there at all:
  - Zombies' buy chime (upstream's `buy.sound`). Nothing real to match it to. The zombies' voices are synthesised now
    (see Zombie voices).
  - The upstream guns' shots and reloads (M4A1, MP5, SCAR-H, USP, M700, Spaghelli, 1911), and the grenades' pins
    and throws: upstream's own recordings, not CoD's or s&box's. Their blasts, dry fire and draws are synthesised now
    (see Ordnance and handling sounds).
  - The cash bag's and the streak drone's draw (upstream's `weapon_switch`): neither is a gun or a grenade.
  - Impacts are heard by everyone within ~76 m, when the round gets there and the sound has come back (see Bullet
    cracks). The shooter's machine plays them where its rounds struck; the others find them by a short trace at the
    round's end.
  - Bots' shots make no impact effects, only the sounds, and bots make no footsteps.
- The editor has to compile the new WAVs and events. They were made without it (2026-09-29, the knife and grenade sets
  2026-09-30), so none of it has been heard in-game. The code compiled offline with dotnet.

