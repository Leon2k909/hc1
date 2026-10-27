## Ordnance and handling sounds (`Tools/ordnance_sounds.py`, `Tools/handling_sounds.py`)
- The user asked for some of the default s&box and CoD sounds to be changed "so we're unique", "ultra realistic"
  (2026-10-01). Both scripts synthesise from the physics of each event, with no samples, the way `world_sounds.py` does
  (and on its helpers). Each docstring has every layer, its source figures and why. A re-run rewrites the WAVs (seeded,
  so the same ones) and keeps an existing `.sound` event, which may have been tuned. `--preview <wav>` plays every take;
  `--out <dir>` writes somewhere else.
- `ordnance_sounds.py`:
  - The M67 frag (`frag_blast_near`, `_far`), the 9 kg C4 charge (`c4_blast_near`, `_far`) and the M84 flashbang
    (`flashbang_bang`), from Kinney-Graham blast waves (Friedlander pulses), Whitham N-waves for the fragments passing,
    the fireball's roar, debris and soil coming down, echoes and the rumble.
  - The ear overloads on a bang, so it's soft-clipped (`master`, `BANG_DRIVE`), and the tail goes in after at its own
    level against the bang. A millisecond bang can't reach a rifle shot's loudness, so the blasts play at full volume:
    5.5 dB over a rifle 15 m away for the frag, 12 dB for the C4 at 40 m.
  - The far sets are the bang dulled by the air and the echoes round the listener. `BlastSound`
    (`Code/Weapons/Grenades/BlastSound.cs`, on `he_explosion.prefab` and `c4_explosion.prefab`) plays the far set past
    `FarDistance` (1600 for the frag, 4000 for the C4; `FAR_DISTANCES` holds the same), and either one arrives when the
    sound gets there (`GunshotAudio.PlayDelayed`). The flashbang's bang is delayed the same way; its flash isn't.
  - The C4's explosion had a `Facepunch.SoundEmitter`, a type that doesn't exist (the library's is
    `Sandbox.Audio.SoundEmitter`), so it was probably silent.
  - The smoke grenade's hiss: `smoke_ignite` (the fuze and the composition catching) and `smoke_burn` (a seamless 8 s
    loop, `.wav.meta` loop true), on two emitters in `smoke_particles.prefab`. The loop fades in over 1.4 s and out from
    65 s to 70 s, with the emission.
  - The ear ringing after a flashbang (`sounds/player/ear_ringing`, stereo, 10 s): `FlashbangEffect` sets the handle's
    volume itself, so its level is in the file.
- `handling_sounds.py`:
  - Dry fire (`sounds/guns/handling/dryfire_{rifle,ak,pistol}`, each gun's `DryFireSound`): an AR's hammer, an AK's
    heavier hammer in a stamped receiver (the Kastov 762, RPK, AK-105, Vityaz, Bizon and Vepr-12), and a pistol's. The
    ported guns' come from `kastov_prefabs.py` (`Prefabs.dry_fire`). The Kastov-74u keeps its own.
  - Draws (`draw_{rifle,pistol,grenade}`, `DeploySound`) where upstream's `weapon_switch` was: the M4A1, M700, MP5,
    SCAR-H and Spaghelli (a rifle off its sling), the USP, USP-SD and 1911 (out of a Kydex holster), and the grenades,
    the C4 and the recon drone (out of a pouch; `build_recon_tactical.py` writes the drone's). The ported guns keep their
    own raise sounds.
  - Brass (`sounds/world/casings/brass_{rifle,pistol}_<floor>`): a case's ring modes, its chatter as it lands, and the
    floor's part. `SpentCasing` plays one on every bounce over 25 u/s (`WorldSounds.CasingBounce`, `CasingVolume`, as
    loud as the speed into the floor gives), by its `Brass` (the 9 mm casing prefab is Pistol). Its old `BounceSound`
    (upstream's `shell_case_bounce`) stays the fallback for floors we have none for.
  - Hits to the head (`sounds/player/hits/helmet_hit`, `head_hit`, the player prefab's `HeadshotWithHelmetSound` and
    `HeadshotSound`): an aramid composite helmet's crack, and a bare head's. They sit just over a flesh hit (-22.5), and
    reach 2500 units. Upstream's reached 13000 and were 7-10 dB over a flesh hit.
- Levels are the K-weighted loudness of the loudest 50 ms, against the walk on concrete (-36), with real differences
  squeezed 0.43 times like the rest of the mix: the dry fire ~8 dB over a step, a draw ~4.5 dB, a case on concrete 3 dB
  (tile and steel louder, earth and grass far quieter, a pistol case 1.5 dB under a rifle case).
- Made on 2026-10-01 with the editor open, which compiled the WAVs and events as they were written. The code compiled
  offline with dotnet. Nothing has been heard in-game yet.

