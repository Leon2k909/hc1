"""
The recon octocopter's rotors, synthesised from how a coaxial multirotor makes its noise, with no samples.

    python Tools/octocopter_sounds.py [--preview <wav>] [--out <dir>]

Writes Assets/sounds/drones/octocopter_rotors.wav (an 8 s loop at hover), its .wav.meta (looping, written first so the
editor's first import loops it) and octocopter_rotors.sound (3D), if the event doesn't exist yet: an event may be tuned
in the editor, so a rerun keeps it. The WAV is seeded, so a rerun writes the same one. --preview writes the rotors
spinning up, hovering, climbing, settling and spinning down, as ReconOctocopter.UpdateSound plays them (pitch with the
rotor speed, volume with its cube).

The machine (Tools/build_recon_octocopter.py): a ~10 kg coaxial X8 like Inspired Flight's IF800 Tomcat, four arms with
a pair of 26 inch (0.66 m) two-blade props on each, the upper and lower props of a pair turning opposite ways. At hover
they turn ~2,900 rpm (ReconOctocopter.HoverRpm): 48.3 revolutions a second, tips at ~100 m/s (Mach 0.29), and a blade
passes a given point 96.7 times a second.

What's heard, prop by prop:
- The blade-pass tone. Each blade's lift and thickness push the air once a pass, so a rotor sings at its blade-pass
  frequency (96.7 Hz) and its harmonics. In clean air at a low tip Mach the harmonics fall away fast. An upper prop's
  air is clean but for the arm under it, whose blockage each blade feels as a kick, so its harmonics fall ~n^-1.5. A
  lower prop works in the upper's wake and cuts its tip vortices, so its loading is unsteady and its harmonics fall
  slower (~n^-1.1): it's the harsher of the two. A blade's small imbalance adds a once-a-revolution tone (48 Hz).
- The pair's interaction. Two two-blade props turning opposite ways pass over each other twice a relative revolution,
  four times a revolution of either: an impulsive tone at twice the blade-pass frequency (193 Hz) and its harmonics,
  strong on coaxial machines, which is why they sound rougher than a quad.
- Broadband noise: the blades' boundary layers shedding off their trailing edges, and the turbulence they fly
  through. Slow, wide blades like these put most of it round 0.5-2 kHz, falling away above ~4 kHz. Its loudness swells as each blade comes round towards the
  listener, so it's modulated at the blade-pass rate (the "swish"). The lower props, in turbulent air, are louder.
- The motors: 96 mm pancake outrunners, taken as 24 slots and 28 magnets (14 pole pairs, as such motors usually are).
  Their windings are fed at 14 x 48.3 = 676 Hz, and the stator's magnetic pull rings at twice that (1,352 Hz), with a
  little of the first and third. They're quiet next to the props: ~25 dB under.
- None of the eight turns at the same speed: the flight controller trims each to hold the attitude (~1% apart here),
  and corrects them all the time against gusts, wandering each by ~0.4% at 1-3 Hz. The tones beat against each other,
  which is most of what makes a multirotor sound alive rather than a steady drone.

Everything is periodic over the loop: each prop's speed is rounded to a whole number of cycles in 8 s, the speed
wander has no mean (so its phase comes back to where it started), and the noise is shaped in the frequency domain.
So the loop has no seam and no crossfade.

The level. Large multirotors are quoted at ~70 dB(A) at 10 m in a hover; at 3 m (ReconOctocopter's rotors span 1.5 m,
so nearer than that is the near field) that's ~80 dB(A), 17 dB over a footstep at the ear (~63). The game's mix squeezes
real differences 0.43 times (foley_voicing's docstring has why), so the loop sits 7.5 dB over the walk on concrete
(-36, K-weighted, loudest 50 ms) at the event's reference distance of 120 units (3 m), then falls 6 dB a doubling of
the distance (world_sounds.falloff) out to 6000 units (152 m), past the drone's 120 m ceiling.

The operator flying it hears it from where they stand, not from the camera: the body camera's AudioListener stays on
while the feed's camera draws (a real ground station's feed has no sound).
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_sounds as ws  # noqa: E402
from ordnance_sounds import periodic_noise, write_loop_meta  # noqa: E402
from ui_sounds import loudness  # noqa: E402
from world_sounds import SR  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "Assets")
SOUND_PATH = "sounds/drones"
NAME = "octocopter_rotors"

LOOP_SECONDS = 8.0
HOVER_RPM = 2900.0  # ReconOctocopter.HoverRpm
BLADES = 2
POLE_PAIRS = 14
TARGET = -36.0 + 7.5  # K-weighted, loudest 50 ms, at the reference distance
DISTANCE = 6000
REFERENCE = 120

# Each prop: (the arm it's on, upper or lower). Upper props alternate direction arm to arm; each lower turns opposite
# its upper.
PROPS = [(arm, level) for arm in range(4) for level in ("upper", "lower")]


def quantise(f):
    """The nearest frequency with a whole number of cycles in the loop."""
    return round(f * LOOP_SECONDS) / LOOP_SECONDS


def wander_phase(rng, n, rate, depth):
    """The extra phase (in cycles of the shaft) from a speed wandering by `depth` (a share of the speed) at about `rate`
    Hz, periodic over the loop: the wander has no mean, so its integral ends where it starts."""
    w = periodic_noise(rng, n, 0, rate, 2)
    w = w - w.mean()
    w *= depth / np.abs(w).max()
    return np.cumsum(w) / SR


def harmonics(phase, amplitudes, rng):
    """Sum of cos(k * phase + random phase) for each harmonic's amplitude; `phase` is in cycles."""
    out = np.zeros(len(phase))
    for k, a in enumerate(amplitudes, start=1):
        out += a * np.cos(2 * np.pi * k * phase + rng.uniform(0, 2 * np.pi))
    return out


def rotors(rng):
    n = int(LOOP_SECONDS * SR)
    t = np.arange(n) / SR
    shaft = HOVER_RPM / 60.0
    out = np.zeros(n)
    phases = {}
    for arm, level in PROPS:
        # The controller's trim, then its constant small corrections.
        f = quantise(shaft * (1 + rng.normal(0, 0.01)))
        phase = f * t + f * wander_phase(rng, n, rng.uniform(1.0, 3.0), 0.004)
        phases[arm, level] = phase
        blade_pass = BLADES * phase
        lower = level == "lower"

        roll_off = 1.1 if lower else 1.5
        tone = harmonics(blade_pass, [(1.25 if lower else 1.0) * k ** -roll_off for k in range(1, 17)], rng)
        tone += 0.06 * np.cos(2 * np.pi * phase + rng.uniform(0, 2 * np.pi))  # the blades' imbalance

        # Broadband, swelling as each blade comes round.
        broadband = periodic_noise(rng, n, 350, 1800, 2) + 0.3 * periodic_noise(rng, n, 1800, 4500, 2)
        broadband *= (0.45 if lower else 0.32) / np.sqrt(np.mean(broadband ** 2))
        broadband *= 1 + 0.45 * np.cos(2 * np.pi * blade_pass + rng.uniform(0, 2 * np.pi))

        # The motor's magnetic whine.
        electrical = POLE_PAIRS * phase
        motor = 0.02 * np.cos(2 * np.pi * electrical + rng.uniform(0, 2 * np.pi))
        motor += 0.05 * np.cos(4 * np.pi * electrical + rng.uniform(0, 2 * np.pi))
        motor += 0.015 * np.cos(6 * np.pi * electrical + rng.uniform(0, 2 * np.pi))

        out += tone + broadband + motor

    # Each pair's props passing over each other: four times a revolution of either.
    for arm in range(4):
        crossing = 2 * (phases[arm, "upper"] + phases[arm, "lower"])
        out += harmonics(crossing, [0.45 * k ** -0.9 for k in range(1, 11)], rng)
    return out


def octaves(x):
    """Level per octave band, relative to the loudest, for the printout."""
    spectrum = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    centres = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
    levels = [spectrum[(f >= c / np.sqrt(2)) & (f < c * np.sqrt(2))].sum() for c in centres]
    top = max(levels)
    return "  ".join(f"{c}:{10 * np.log10(v / top):.0f}" for c, v in zip(centres, levels))


def build():
    loop = rotors(np.random.default_rng(31000))
    loop = loop / np.abs(loop).max() * 10 ** (-1 / 20)
    volume = min(1.0, 10 ** ((TARGET - loudness(loop)) / 20))
    return loop, volume


def resample(loop, rates):
    """The loop played at a varying rate (one per output sample), as a sound's pitch plays it."""
    position = np.cumsum(rates) % len(loop)
    index = np.arange(len(loop) + 1)
    return np.interp(position, index, np.append(loop, loop[0]))


def preview(loop, volume, path):
    # The rotor speed as UpdateSound follows it: spin-up, hover, a climb (+15 %), hover, spin-down.
    keys = [(0.0, 0.05), (1.2, 1.0), (5.0, 1.0), (5.6, 1.15), (8.0, 1.15), (8.6, 1.0), (12.0, 1.0), (14.0, 0.05)]
    t = np.arange(int(keys[-1][0] * SR)) / SR
    speed = np.interp(t, [k[0] for k in keys], [k[1] for k in keys])
    out = resample(loop, np.clip(speed, 0.3, 1.4)) * np.clip(speed ** 3, 0, 1.6) * volume
    ws.write_wav(path, out)
    print(f"preview: {path} ({len(out) / SR:.1f} s)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", help="write a WAV of the rotors spinning up, hovering, climbing and stopping")
    parser.add_argument("--out", help="write under this folder instead of Assets (to try changes)")
    args = parser.parse_args()

    loop, volume = build()
    folder = os.path.join(args.out or ASSETS, *SOUND_PATH.split("/"))
    os.makedirs(folder, exist_ok=True)
    write_loop_meta(folder, NAME)
    ws.write_wav(os.path.join(folder, NAME + ".wav"), loop)
    written = ws.write_event(folder, SOUND_PATH, NAME, [NAME], volume, 0.0, "1", DISTANCE, REFERENCE)
    ws.describe(NAME, [loop], volume)
    print(f"  octaves (dB): {octaves(loop)}")
    if not written:
        print(f"  {NAME}.sound exists, left as it is")
    if args.preview:
        preview(loop, volume, args.preview)


if __name__ == "__main__":
    main()
