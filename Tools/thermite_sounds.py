"""
The thermite grenade's sounds (Code/Weapons/Grenades/Fire/ThermiteBurnEffect.cs), synthesised so they can be re-tuned
here without any samples.

    python Tools/thermite_sounds.py [--preview <wav>]

Writes Assets/sounds/weapons/grenade/thermite_ignite.wav and thermite_burn.wav, and their .sound events if those don't
exist yet (an event may be tuned in the editor, so it isn't overwritten). --preview also writes one file that plays the
ignition into 12 s of the burn, then its last seconds and the fade.

Burning thermite doesn't crackle like wood or roar like a gas flame. It's a harsh, bright hiss, like a giant sparkler
or a road flare, torn by spitting as molten iron and slag burst from the burning point, with a turbulent rumble under
it and the odd sputter.
- thermite_burn: an 8 s loop, mono (the engine places it in the world).
  - hiss: noise from 1.5 to 9 kHz, wandering by about +-2 dB at a few Hz;
  - body: 600 Hz to 3 kHz, flickering at 4-6 Hz;
  - rumble: 90 to 900 Hz, flickering at 6 Hz;
  - spitting: short bursts of bright noise (0.3-3 ms), about 70 a second with a heavy-tailed spread of loudness, and
    now and then a sputter of 10-30 in a few tenths of a second.
  Every part is periodic over the loop's length (shaped in the frequency domain, bursts wrapped round the end), so it
  loops with no seam and no crossfade.
- thermite_ignite: the M201A1 fuze's end lighting the first fire mix. A pop, then a rising rush as the flare takes hold
  over 0.8 s (ThermiteGrenade.Kindle, over which the loop also fades in), dying away by 2.5 s.
"""
import argparse
import json
import os
import uuid
import wave

import numpy as np
from scipy import signal

SR = 44100
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "Assets", "sounds", "weapons", "grenade")
SOUND_PATH = "sounds/weapons/grenade"

LOOP_SECONDS = 8.0

# The loop's loudness: about the molotov fire loop's (-12.4 dBFS RMS), -1 dBFS peaks.
LOOP_RMS_DB = -13.0
PEAK_DB = -1.0

# How far each event carries (the .sound's Decibels): the molotov loop is 70, an HE grenade's blast carries further.
DECIBELS = {"thermite_burn": 80, "thermite_ignite": 85}


def band(low, high, f, order=2):
    """A Butterworth band-pass's magnitude at frequencies f (either edge None for none)."""
    gain = np.ones_like(f)
    if low:
        gain /= np.sqrt(1.0 + (low / np.maximum(f, 1e-6)) ** (2 * order))
    if high:
        gain /= np.sqrt(1.0 + (f / high) ** (2 * order))
    return gain


def periodic_noise(rng, n, low, high, order=2):
    """Unit-RMS noise shaped by a band-pass, periodic over n samples."""
    spectrum = np.fft.rfft(rng.standard_normal(n))
    y = np.fft.irfft(spectrum * band(low, high, np.fft.rfftfreq(n, 1 / SR), order), n)
    return y / np.sqrt(np.mean(y ** 2))


def wobble(rng, n, rate):
    """Slow random movement under `rate` Hz, unit RMS, periodic over n samples."""
    return periodic_noise(rng, n, None, rate, order=3)


def burst_noise(rng, length, low, high):
    sos = signal.butter(2, [low, min(high, SR * 0.45)], btype="bandpass", fs=SR, output="sos")
    return signal.sosfilt(sos, rng.standard_normal(length))


def spit(rng, tau):
    """One spit: bright noise that dies away with time constant tau (s)."""
    length = int(tau * 6 * SR) + 8
    t = np.arange(length) / SR
    low = rng.uniform(1200, 3000)
    x = burst_noise(rng, length, low, rng.uniform(7000, 16000)) * np.exp(-t / tau)
    x[: 3] *= np.linspace(0.2, 1.0, 3)
    return x / (np.abs(x).max() + 1e-9)


def add_wrapped(track, x, at):
    """x added into track from sample `at`, wrapping round the end (the track is a loop)."""
    idx = (at + np.arange(len(x))) % len(track)
    np.add.at(track, idx, x)


def spitting(rng, n, rate, sputters):
    track = np.zeros(n)
    for at in rng.integers(0, n, rng.poisson(rate * n / SR)):
        add_wrapped(track, spit(rng, rng.uniform(0.0003, 0.003)) * min(rng.pareto(2.5) + 0.3, 4.0), at)
    for start in rng.integers(0, n, rng.poisson(sputters * n / SR)):
        span = rng.uniform(0.15, 0.45)
        for _ in range(rng.integers(10, 31)):
            at = start + int(rng.uniform(0, span) * SR)
            add_wrapped(track, spit(rng, rng.uniform(0.0005, 0.004)) * rng.uniform(0.8, 2.2), at)
    return track


def burn(rng):
    n = int(LOOP_SECONDS * SR)
    hiss = periodic_noise(rng, n, 1500, 9000) * (1.0 + 0.25 * wobble(rng, n, 3.0))
    body = periodic_noise(rng, n, 600, 3000) * (1.0 + 0.3 * wobble(rng, n, 5.0))
    rumble = periodic_noise(rng, n, 90, 900) * (1.0 + 0.35 * wobble(rng, n, 6.0))
    spits = spitting(rng, n, 70.0, 0.7)
    spits /= np.sqrt(np.mean(spits ** 2)) + 1e-9
    x = 1.0 * hiss + 0.7 * body + 0.6 * rumble + 0.55 * spits
    return level(x, LOOP_RMS_DB)


def ignite(rng, seconds=2.5):
    n = int(seconds * SR)
    t = np.arange(n) / SR

    # The pop: a click of broadband noise over a low thump.
    pop = burst_noise(rng, n, 400, 14000) * np.exp(-t / 0.0015)
    sweep = 2 * np.pi * np.cumsum(60 + 60 * np.exp(-t / 0.03)) / SR
    thump = np.sin(sweep) * np.exp(-t / 0.05) * (1 - np.exp(-t / 0.002))

    # The rush: bands that come up one after another as the flare takes hold, so it rises in pitch.
    rush = np.zeros(n)
    for low, high, peak, amount in ((200, 600, 0.12, 0.35), (600, 1500, 0.25, 0.5), (1500, 4000, 0.45, 0.8),
                                    (4000, 11000, 0.7, 1.0)):
        rise = np.clip(t / peak, 0.0, 1.0) ** 2
        fall = np.exp(-np.maximum(t - peak, 0.0) / 0.45)
        rush += amount * burst_noise(rng, n, low, high) / 0.3 * rise * fall

    # The first fire mix spits hard as it catches.
    spits = np.zeros(n)
    for at in rng.integers(int(0.03 * SR), int(1.4 * SR), 160):
        age = at / SR
        add_wrapped(spits, spit(rng, rng.uniform(0.0004, 0.003)) * min(rng.pareto(2.2) + 0.4, 4.0) * np.exp(-max(age - 0.5, 0.0) / 0.5), at)
    spits[-int(0.1 * SR):] = 0.0

    x = 1.2 * pop + 0.9 * thump + rush / (np.abs(rush).max() + 1e-9) + 0.45 * spits / (np.abs(spits).max() + 1e-9)
    x = signal.sosfilt(signal.butter(2, 40, btype="highpass", fs=SR, output="sos"), x)
    fade = int(0.3 * SR)
    x[-fade:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, fade))
    return limit(x / np.abs(x).max())


def level(x, rms_db):
    """To an RMS of rms_db, then soft-limited under PEAK_DB. Pointwise, so a periodic signal stays periodic."""
    x = x / np.sqrt(np.mean(x ** 2)) * 10 ** (rms_db / 20)
    return limit(x)


def limit(x):
    ceiling = 10 ** (PEAK_DB / 20)
    knee = 0.7 * ceiling
    over = np.abs(x) > knee
    y = x.copy()
    y[over] = np.sign(x[over]) * (knee + (ceiling - knee) * np.tanh((np.abs(x[over]) - knee) / (ceiling - knee)))
    return y


def write_wav(path, x):
    pcm = np.round(np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def write_loop_meta(name):
    """The loop's import settings: it has to loop. Written before the WAV so the editor's first import loops it."""
    path = os.path.join(OUT, name + ".wav.meta")
    meta = {"loop": True, "start": 0, "end": 0, "rate": SR, "compress": False, "bitrate": 256}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            meta = {**json.load(f), "loop": True}
    meta.setdefault("guid", str(uuid.uuid4()))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, indent=2)


def write_sound_event(name):
    """A world sound, like the other grenades': occluded, absorbed by air and attenuated with distance."""
    path = os.path.join(OUT, name + ".sound")
    if os.path.exists(path):
        return
    event = {
        "UI": False,
        "Volume": "1.00,1.00,0",
        "Pitch": "1.00,1.00,0",
        "Decibels": DECIBELS[name],
        "SelectionMode": "Random",
        "Sounds": [f"{SOUND_PATH}/{name}.vsnd"],
        "Occlusion": True,
        "AirAbsorption": True,
        "Transmission": True,
        "OcclusionRadius": 64,
        "DistanceAttenuation": True,
        "__references": [],
        "__version": 0,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(event, f, indent=2)


def describe(name, x, loop=False):
    spectrum = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    text = (f"{name}: {len(x) / SR:.2f} s, peak {20 * np.log10(np.abs(x).max()):.1f} dBFS, "
            f"RMS {20 * np.log10(np.sqrt(np.mean(x ** 2))):.1f} dBFS, spectral centroid "
            f"{np.sum(spectrum * freqs) / np.sum(spectrum):.0f} Hz")
    if loop:
        # The step from the last sample back to the first, against every other step: a seam would stand out.
        steps = np.abs(np.diff(x))
        text += f", seam step at the {100 * np.mean(steps < abs(x[0] - x[-1])):.0f}th percentile of steps"
    print(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", help="also write the ignition into the burn and its fade, as one WAV")
    parser.add_argument("--out", help="write the sounds here instead of Assets (for trying things out)")
    args = parser.parse_args()

    global OUT
    if args.out:
        OUT = args.out

    rng = np.random.default_rng(40)
    sounds = {"thermite_ignite": ignite(rng), "thermite_burn": burn(rng)}

    os.makedirs(OUT, exist_ok=True)
    write_loop_meta("thermite_burn")
    for name, x in sounds.items():
        write_wav(os.path.join(OUT, name + ".wav"), x)
        write_sound_event(name)
        describe(name, x, loop=name == "thermite_burn")

    if args.preview:
        # What ThermiteBurnEffect does: the ignition, the loop fading in over the kindling (0.8 s), 12 s of it, then its
        # last 3 s dying down and a 1.5 s stop.
        loop = sounds["thermite_burn"]
        body = np.tile(loop, 3)[: int(16.5 * SR)]
        t = np.arange(len(body)) / SR
        kindle = np.clip(t / 0.8, 0, 1)
        gain = kindle * kindle * (3 - 2 * kindle)
        gain *= np.clip((15.0 - t) / 3.0, 0, 1)
        stop = np.clip(1.0 - (t - 15.0) / 1.5, 0, 1)
        body = body * np.minimum(gain * 1.1, 1.0) * np.where(t > 15.0, stop, 1.0)
        ignition = np.concatenate([sounds["thermite_ignite"], np.zeros(len(body) - len(sounds["thermite_ignite"]))])
        write_wav(args.preview, limit(body + ignition))
        print(f"preview: {args.preview}")


if __name__ == "__main__":
    main()
