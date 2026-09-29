"""
Kill-confirm sounds: what you hear when you kill an enemy (Code/GameLoop/Audio/KillSounds.cs). They're synthesised,
so they can be re-tuned here without any samples.

    python Tools/kill_sounds.py [--preview <wav>]

Writes Assets/sounds/ui/kill/kill_confirm.wav (a kill) and kill_confirm_headshot.wav (a headshot kill), and their
.sound events if those don't exist yet (an event may be tuned in the editor, so it isn't overwritten). --preview also
writes one file that plays a kill, the three multikill steps KillSounds climbs through, then a headshot kill.

A kill is a short "thwack" in four layers, over in about 0.3 s so it never masks the next shot:
- snap: 3 ms of band-passed noise (2.5-9 kHz), the tick that cuts through gunfire;
- knock: a hollow "tock", three damped modes at 420, 1130 and 1870 Hz;
- body: a kick-drum sine falling from 170 to 58 Hz, soft-clipped so small speakers still hear its harmonics;
- ting: a short inharmonic metal tone on E6, which gives the sound a pitch for the multikill steps.
A headshot kill adds a ping, a thin metal shell's ring on B6 (a fifth over the ting) whose fundamental is doubled
3.5 Hz apart so it shimmers, for about 0.6 s, and a little more air in the snap.
"""
import argparse
import json
import os
import wave

import numpy as np
from scipy import signal

SR = 44100
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "Assets", "sounds", "ui", "kill")
SOUND_PATH = "sounds/ui/kill"

# KillSounds.Steps: semitones for the 1st, 2nd, 3rd and later kills in quick succession.
STREAK_STEPS = [0, 2, 4, 7]

TING = 1318.5  # E6
PING = 1975.5  # B6


def envelope(t, attack, tau):
    """A half-cosine rise over `attack` seconds, then an exponential decay with time constant `tau`."""
    rise = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / attack, 0.0, 1.0))
    return rise * np.exp(-np.maximum(t - attack, 0.0) / tau)


def modes(t, partials):
    """Damped sines, each (frequency in Hz, amplitude, decay time constant in s)."""
    return sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / tau) for f, a, tau in partials)


def noise(rng, n, low, high):
    sos = signal.butter(2, [low, high], btype="bandpass", fs=SR, output="sos")
    y = signal.sosfilt(sos, rng.standard_normal(n))
    return y / np.abs(y).max()


def delayed(x, seconds):
    return np.concatenate([np.zeros(int(seconds * SR)), x])[: len(x)]


def unit(x):
    return x / np.abs(x).max()


def kill(rng, seconds=0.3):
    t = np.arange(int(seconds * SR)) / SR

    snap = noise(rng, len(t), 2500, 9000) * envelope(t, 0.0003, 0.005)
    crack = noise(rng, len(t), 1000, 3500) * envelope(t, 0.0005, 0.012)
    knock = unit(modes(t, [(420, 1.0, 0.030), (1130, 0.55, 0.018), (1870, 0.3, 0.011)]) * envelope(t, 0.0006, 1.0))

    pitch = 55 + 105 * np.exp(-t / 0.022)
    body = np.sin(2 * np.pi * np.cumsum(pitch) / SR) * envelope(t, 0.0012, 0.04)
    body = np.tanh(1.8 * body) / np.tanh(1.8)

    ting = modes(t, [(TING, 1.0, 0.17), (TING * 2.009, 0.42, 0.10), (TING * 2.693, 0.30, 0.07),
                     (TING * 3.891, 0.16, 0.045)])
    ting = delayed(unit(ting * envelope(t, 0.0015, 1.0)), 0.003)

    # The snap and crack are only milliseconds long, so they need the most level to be heard as the leading edge.
    return 1.5 * snap + 0.75 * crack + 0.45 * knock + 0.45 * body + 0.2 * ting


def headshot(rng, seconds=0.75):
    t = np.arange(int(seconds * SR)) / SR

    air = noise(rng, len(t), 7000, 15000) * envelope(t, 0.0003, 0.006)
    ping = modes(t, [(PING, 1.0, 0.42), (PING + 3.5, 0.6, 0.42), (PING * 2.756, 0.45, 0.20),
                     (PING * 5.404, 0.18, 0.09)])
    ping = delayed(unit(ping * envelope(t, 0.0008, 1.0)), 0.005)

    return kill(rng, seconds) + 0.3 * air + 0.3 * ping


def finish(x):
    """No DC or rumble under 30 Hz, a touch of soft clipping to glue the layers, -1 dBFS peaks, the silent tail cut
    and faded so it can't click."""
    x = signal.sosfilt(signal.butter(2, 30, btype="highpass", fs=SR, output="sos"), x)
    x = np.tanh(unit(x))
    x = unit(x) * 10 ** (-1 / 20)

    audible = np.nonzero(np.abs(x) > 10 ** (-60 / 20))[0]
    end = min(len(x), audible[-1] + int(0.01 * SR))
    x = x[:end]
    fade = int(0.015 * SR)
    x[-fade:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, fade))
    return x


def write_wav(path, x):
    pcm = np.round(np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def write_sound_event(name):
    """A 2D (UI) event: KillSounds sends it to the UI mixer and sets its pitch for the multikill steps."""
    path = os.path.join(OUT, name + ".sound")
    if os.path.exists(path):
        return
    event = {
        "UI": True,
        "Volume": "1",
        "Pitch": "1",
        "Decibels": 70,
        "SelectionMode": "Random",
        "Sounds": [f"{SOUND_PATH}/{name}.vsnd"],
        "Occlusion": False,
        "AirAbsorption": False,
        "Transmission": False,
        "OcclusionRadius": 64,
        "DistanceAttenuation": False,
        "__references": [],
        "__version": 1,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(event, f, indent=2)
        f.write("\n")


def repitch(x, semitones):
    """What SoundHandle.Pitch does: plays faster, so higher and shorter."""
    rate = 2 ** (semitones / 12)
    return np.interp(np.arange(0, len(x) - 1, rate), np.arange(len(x)), x)


def describe(name, x):
    head = x[: int(0.15 * SR)]
    spectrum = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    print(f"{name}: {len(x) / SR:.2f} s, peak {20 * np.log10(np.abs(x).max()):.1f} dBFS, "
          f"RMS of the first 150 ms {20 * np.log10(np.sqrt(np.mean(head ** 2))):.1f} dBFS, "
          f"spectral centroid {np.sum(spectrum * freqs) / np.sum(spectrum):.0f} Hz")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", help="also write a WAV with a kill, the multikill steps and a headshot kill")
    args = parser.parse_args()

    rng = np.random.default_rng(7)
    sounds = {"kill_confirm": finish(kill(rng)), "kill_confirm_headshot": finish(headshot(rng))}

    os.makedirs(OUT, exist_ok=True)
    for name, x in sounds.items():
        write_wav(os.path.join(OUT, name + ".wav"), x)
        write_sound_event(name)
        describe(name, x)

    if args.preview:
        gap = lambda seconds: np.zeros(int(seconds * SR))
        parts = [sounds["kill_confirm"], gap(1.0)]
        for step in STREAK_STEPS:
            parts += [repitch(sounds["kill_confirm"], step), gap(0.45)]
        parts += [gap(0.6), sounds["kill_confirm_headshot"], gap(0.5)]
        write_wav(args.preview, np.concatenate(parts))
        print(f"preview: {args.preview}")


if __name__ == "__main__":
    main()
