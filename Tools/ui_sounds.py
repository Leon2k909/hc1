"""
Menu sounds: the header's navigation click, in place of s&box's stock "ui.button.press" (Kenney's drop_002). They're
synthesised, so they can be re-tuned here without any samples.

    python Tools/ui_sounds.py [--preview <wav>]

Writes Assets/sounds/ui/menu/ui_nav_tab_01-03.wav, three takes of one click that the event picks between at random, and
ui_nav_tab.sound if it doesn't exist yet (an event may be tuned in the editor, so it isn't overwritten). The event plays
on the UI mixer (Settings' UI volume). --preview also writes one file that plays each take, then five tabs in a row.

The click is a rifle's selector lever going over into its next detent, over in about 0.2 s:
- tick: 1 ms of band-passed noise (3.5-10 kHz), the edge that makes it precise;
- latch: the lever's steel, four damped inharmonic modes from 1.7 to 6.9 kHz;
- thump: a short sine falling from 160 to 62 Hz, soft-clipped so small speakers still hear its harmonics, which gives
  it weight without making it loud;
- seat: 16 ms later a softer, lower click, the detent seating;
- slide: a breath of noise whose band rises from 0.9 to 4.5 kHz over 90 ms, the page moving on.
The takes differ in the noise, a 1.5% detune of the modes and the seat's timing, so repeated clicks don't sound
machine-made.
"""
import argparse
import json
import os
import wave

import numpy as np
from scipy import signal

SR = 44100
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "Assets", "sounds", "ui", "menu")
SOUND_PATH = "sounds/ui/menu"

# ProjectSettings/Mixer.config's "UI" mixer, the one Settings' UI volume sets.
UI_MIXER = {"Name": "UI", "Id": "a0a4a16b-c992-48a4-859d-37854d43116f"}

# Each take: (noise seed, detune of the modes, the seat's delay in s).
TAKES = [(11, 1.0, 0.016), (12, 0.985, 0.0145), (13, 1.015, 0.0175)]

# The stock press (Kenney's drop_002 at its event's volume 0.1) measures -33.9 dB in the K-weighted loudest 50 ms
# (loudness()). The click sits 2 dB over it, so it doesn't read as quieter than what it replaces.
TARGET_LOUDNESS = -31.9


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
    return np.concatenate([np.zeros(int(round(seconds * SR))), x])[: len(x)]


def unit(x):
    return x / np.abs(x).max()


def sweep(rng, n, start, end, seconds, q=1.2):
    """Noise through a band-pass whose centre rises exponentially from `start` to `end` Hz over `seconds`."""
    x = rng.standard_normal(n)
    y = np.zeros(n)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(n):
        f = start * (end / start) ** min(i / (seconds * SR), 1.0)
        w = 2 * np.pi * f / SR
        alpha = np.sin(w) / (2 * q)
        a0 = 1 + alpha
        b0, b2 = alpha / a0, -alpha / a0
        a1, a2 = -2 * np.cos(w) / a0, (1 - alpha) / a0
        y[i] = b0 * x[i] + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, x[i]
        y2, y1 = y1, y[i]
    return unit(y)


def nav_tab(seed, detune, seat_delay, seconds=0.22):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR

    tick = noise(rng, len(t), 3500, 10000) * envelope(t, 0.00015, 0.0012)
    latch = modes(t, [(1720 * detune, 1.0, 0.014), (2960 * detune, 0.55, 0.009), (4630 * detune, 0.35, 0.006),
                      (6900 * detune, 0.2, 0.004)])
    latch = delayed(unit(latch * envelope(t, 0.0003, 1.0)), 0.0003)

    # Three cycles or so: a thock you feel, not a boom.
    pitch = 85 + 95 * np.exp(-t / 0.010)
    thump = np.sin(2 * np.pi * np.cumsum(pitch) / SR) * envelope(t, 0.0008, 0.014)
    thump = np.tanh(2.2 * thump) / np.tanh(2.2)

    seat_tick = noise(rng, len(t), 2000, 7000) * envelope(t, 0.0002, 0.0008)
    seat_ring = unit(modes(t, [(1240 * detune, 1.0, 0.012), (2380 * detune, 0.5, 0.008), (3720 * detune, 0.3, 0.005)])
                     * envelope(t, 0.0004, 1.0))
    seat = delayed(0.6 * seat_tick + 0.4 * seat_ring, seat_delay)

    slide = delayed(sweep(rng, len(t), 900, 4500, 0.09, q=2.0) * envelope(t, 0.012, 0.030), 0.004)

    # The tick is only a millisecond long, so it needs the most level to be heard as the leading edge.
    return 1.3 * tick + 0.7 * latch + 0.5 * thump + 0.4 * seat + 0.1 * slide


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


def k_weighted(x, sr=SR):
    """ITU-R BS.1770's K-weighting (a +4 dB shelf over ~1.7 kHz and a 38 Hz high-pass), for loudness as heard."""
    def biquad(b, a):
        return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x)

    f0, gain, q = 1681.97, 3.9998, 0.7072
    k = np.tan(np.pi * f0 / sr)
    vh = 10 ** (gain / 20)
    vb = vh ** 0.4997
    a0 = 1 + k / q + k * k
    x = biquad([(vh + vb * k / q + k * k), 2 * (k * k - vh), (vh - vb * k / q + k * k)],
               [a0, 2 * (k * k - 1), 1 - k / q + k * k])
    f0, q = 38.135, 0.5003
    k = np.tan(np.pi * f0 / sr)
    return biquad([1, -2, 1], [1 + k / q + k * k, 2 * (k * k - 1), 1 - k / q + k * k])


def loudness(x, sr=SR):
    """The K-weighted RMS of the loudest 50 ms, in dB: what a short click's loudness is heard as."""
    y = k_weighted(x, sr) ** 2
    window = int(0.05 * sr)
    return 10 * np.log10(np.convolve(y, np.ones(window) / window, "valid").max())


def write_wav(path, x):
    pcm = np.round(np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def write_sound_event(name, takes, volume):
    """A 2D (UI) event on the UI mixer, picking one take at random."""
    path = os.path.join(OUT, name + ".sound")
    if os.path.exists(path):
        return False
    event = {
        "UI": True,
        "Volume": f"{volume:.3f}",
        "Pitch": "1",
        "Decibels": 70,
        "SelectionMode": "Random",
        "Sounds": [f"{SOUND_PATH}/{take}.vsnd" for take in takes],
        "Occlusion": False,
        "AirAbsorption": False,
        "Transmission": False,
        "OcclusionRadius": 64,
        "DistanceAttenuation": False,
        "DefaultMixer": UI_MIXER,
        "__references": [],
        "__version": 1,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(event, f, indent=2)
        f.write("\n")
    return True


def describe(name, x, volume=1.0):
    spectrum = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    print(f"{name}: {len(x) / SR:.3f} s, peak {20 * np.log10(np.abs(x).max()):.1f} dBFS, "
          f"loudness {loudness(x):.1f} dB ({loudness(x * volume):.1f} dB at volume {volume:.3f}), "
          f"spectral centroid {np.sum(spectrum * freqs) / np.sum(spectrum):.0f} Hz")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", help="also write a WAV with each take, then five tabs in a row")
    args = parser.parse_args()

    takes = {f"ui_nav_tab_{i + 1:02d}": finish(nav_tab(*take)) for i, take in enumerate(TAKES)}

    # All as loud as the quietest, so no take stands out.
    quietest = min(loudness(x) for x in takes.values())
    takes = {name: x * 10 ** ((quietest - loudness(x)) / 20) for name, x in takes.items()}
    volume = min(1.0, 10 ** ((TARGET_LOUDNESS - quietest) / 20))

    os.makedirs(OUT, exist_ok=True)
    for name, x in takes.items():
        write_wav(os.path.join(OUT, name + ".wav"), x)
        describe(name, x, volume)
    if write_sound_event("ui_nav_tab", list(takes), volume):
        print(f"ui_nav_tab.sound: volume {volume:.3f}")
    else:
        print("ui_nav_tab.sound exists, left as it is")

    if args.preview:
        gap = lambda seconds: np.zeros(int(seconds * SR))
        parts = []
        for x in takes.values():
            parts += [x, gap(0.8)]
        order = list(takes.values())
        for i in range(5):
            parts += [order[i % len(order)], gap(0.35)]
        write_wav(args.preview, np.concatenate(parts))
        print(f"preview: {args.preview}")


if __name__ == "__main__":
    main()
