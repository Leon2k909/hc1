"""
Rain, synthesised from how falling drops make their noise, with no samples.

    python Tools/rain_sounds.py [--preview <wav>] [--out <dir>]

Writes Assets/sounds/weather/: three seamless stereo loops, each with its .wav.meta (looping, written first so the
editor's first import loops it) and a flat (2D) .sound event on the default mixer, if the event doesn't exist yet: an
event may be tuned in the editor, so a rerun keeps it. The WAVs are seeded, so a rerun writes the same ones.

- rain_light: light rain (2 mm/h) outdoors.
- rain_heavy: heavy rain (20 mm/h) outdoors. RainView (MixWeights) crossfades the two by the rain's rate, and scales
  them 5 dB a decade of the rate past either end.
- rain_roof: heavy rain on a roof, heard from under it, which RainView plays while the camera has a roof over it.

--preview writes a minute of rain coming on (drizzle to a downpour) outdoors, then the walk in under a roof, as
RainView mixes them.

What's heard outdoors, layer by layer:
- Drops striking hard ground. A drop of diameter D lands at its terminal speed (9.65 - 10.3 exp(-0.6 D) m/s, Atlas and
  Ulbrich's fit to Gunn and Kinzer's measurements: 4 m/s at 1 mm, 6.5 at 2 mm, 8.7 at 4 mm) and its first contact
  is a sharp pressure pulse, a fraction of a millisecond, whose energy goes about as the drop's kinetic energy. So
  each tick is a burst of noise 0.2-0.8 ms long, bright (2-10 kHz) off stone and paving, as loud as D^2.3 of the
  drop (its momentum's share of the pulse), the drops' sizes from Marshall and Palmer's distribution at the loop's
  rate (N(D) = 8000 exp(-4.1 R^-0.21 D) per m3 per mm), cut to those big enough to be heard one by one (0.6 mm up).
- Drops on leaves and grass: a softer pat (0.5-3 kHz) and the leaf's own ring, 5-20 ms, as the blade springs back.
- Drops into puddles. A drop of 0.8-1.1 mm traps a bubble of 0.2-0.25 mm radius as its crater closes ("regular
  entrainment", Pumphrey and Elmore), which rings at its Minnaert frequency, 3.26 / a Hz for a in metres: 13-16 kHz,
  a millisecond or two, rising as it rises. That's the hiss's high peak over water in light rain. Bigger drops trap
  bigger bubbles irregularly: 1-8 kHz, rarer, each one a short "plink".
- The wash: every drop further off than the ear can pick out. They're countless, so their sum is noise, with the
  ticks' spectrum less the air's absorption of the highs over tens of metres: a broad band from ~300 Hz up, flat
  over 1-6 kHz, falling above 8 kHz. It swells and eases with the gusts (0.05-0.25 Hz, +-1.5 dB). Heavy rain's is
  louder against the near drops (more of them, and further off) and a little lower (bigger drops, more water running).
- The two ears hear different drops, and the wash is only partly the same in both (0.3), as round a listener in the
  open.

Under a roof (rain_roof): the drops hit the roof, and what comes through is what the roof's mass lets through, falling
6 dB an octave past ~600 Hz (the mass law), so it's a dense drumming of thumps at 150-1,000 Hz, with the roof's
panels ringing faintly at 90-240 Hz. The outdoor wash comes in round doors and windows, muffled (under 2.5 kHz) and
15 dB down.

The levels. Rain at the ear outdoors is ~50 dB(A) in light rain, ~60 in moderate and ~70 in a downpour (~12 dB a decade
of the rate), against ~63 for a footstep. The game's mix squeezes real differences 0.43 times (foley_voicing's
docstring has why), so against the walk on concrete (-36, K-weighted, loudest 50 ms): light rain at 2 mm/h sits at
-41.5 and heavy at 20 mm/h at -36.5, and the 12 dB a decade becomes 5. Under a tiled or sheet roof a downpour is about
as loud as the street outside at a light rain's level: -41.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_sounds as ws  # noqa: E402
from ordnance_sounds import periodic_noise, write_flat_event, write_loop_meta, write_stereo  # noqa: E402
from ui_sounds import loudness  # noqa: E402
from world_sounds import SR  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "Assets")
SOUND_PATH = "sounds/weather"

LOOP_SECONDS = 12.0
N = int(LOOP_SECONDS * SR)

LIGHT_RATE = 2.0    # mm/h: RainView.LightRate
HEAVY_RATE = 20.0   # mm/h: RainView.HeavyRate
TARGETS = {"rain_light": -41.5, "rain_heavy": -36.5, "rain_roof": -41.0}
DB_PER_DECADE = 5.0  # RainView.DecibelsPerDecade

KERNELS = 24        # waveforms per kind of impact, so no two neighbouring ticks are the same


def terminal_speed(d):
    """m/s for a drop of diameter d mm (Atlas and Ulbrich)."""
    return 9.65 - 10.3 * np.exp(-0.6 * d)


def drop_sizes(rng, rate, count, smallest=0.6, largest=5.5):
    """Diameters (mm) from Marshall and Palmer's distribution at `rate` mm/h, cut to [smallest, largest], weighted by
    how often each size lands (number density times fall speed)."""
    slope = 4.1 * rate ** -0.21
    d = np.linspace(smallest, largest, 400)
    weight = np.exp(-slope * d) * terminal_speed(d)
    cdf = np.cumsum(weight)
    cdf /= cdf[-1]
    return np.interp(rng.random(count), cdf, d)


def spectral(rng, n, curve):
    """Periodic noise over n samples with this amplitude curve over frequency (a function of f in Hz)."""
    spectrum = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    x = np.fft.irfft(spectrum * curve(np.maximum(f, 1.0)), n)
    return x / np.sqrt(np.mean(x ** 2))


def band_curve(low, high, order=2):
    return lambda f: 1 / np.sqrt(1 + (low / f) ** (2 * order)) / np.sqrt(1 + (f / high) ** (2 * order))


def circular_convolve(train, kernel):
    """The kernel struck at every impulse in the train, wrapping round the loop's end."""
    k = np.zeros(len(train))
    k[: len(kernel)] = kernel
    return np.fft.irfft(np.fft.rfft(train) * np.fft.rfft(k), len(train))


def struck(rng, times, amplitudes, kernels):
    """Each strike played with one of the kernels, picked at random."""
    out = np.zeros(N)
    pick = rng.integers(0, len(kernels), len(times))
    for i, kernel in enumerate(kernels):
        train = np.zeros(N)
        mine = pick == i
        np.add.at(train, (times[mine] * SR).astype(int) % N, amplitudes[mine])
        out += circular_convolve(train, kernel)
    return out


def burst_kernel(rng, length, tau, low, high):
    """A burst of noise band-passed to [low, high], decaying with tau seconds, `length` s long."""
    n = int(length * SR)
    t = np.arange(n) / SR
    x = periodic_noise(rng, n, low, high, 2) * np.exp(-t / tau)
    x[: max(1, int(0.00004 * SR))] *= np.linspace(0, 1, max(1, int(0.00004 * SR)))
    return x / np.abs(x).max()


def ring_kernel(rng, f0, tau, rise, length):
    """A damped tone at f0 Hz rising by `rise` (a share) as it rings, after a click."""
    n = int(length * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + rise * (1 - np.exp(-t / tau)))
    phase = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(phase + rng.uniform(0, 2 * np.pi)) * np.exp(-t / tau)
    x[: int(0.0003 * SR)] += burst_kernel(rng, 0.0003, 0.0001, 2000, 12000)[: int(0.0003 * SR)] * 0.5
    return x / np.abs(x).max()


def poisson_times(rng, rate):
    count = rng.poisson(rate * LOOP_SECONDS)
    return np.sort(rng.random(count) * LOOP_SECONDS)


def pan(rng, count):
    """Left and right gains for sources all round (equal power)."""
    p = rng.uniform(-1, 1, count)
    return np.cos((p + 1) * np.pi / 4), np.sin((p + 1) * np.pi / 4)


def gusts(rng, depth_db=1.5):
    """A slow swell, periodic over the loop."""
    g = periodic_noise(rng, N, 0, 0.25, 2)
    g /= np.abs(g).max()
    return 10 ** (depth_db * g / 20)


def near_drops(rng, rate, ticks_per_second, leaf_share, puddle_share):
    """The drops close enough to pick out, in both ears."""
    hard = [burst_kernel(rng, 0.004, rng.uniform(0.00015, 0.0006), rng.uniform(1000, 2000), rng.uniform(5000, 8000))
            for _ in range(KERNELS)]
    leaf = [burst_kernel(rng, 0.03, rng.uniform(0.004, 0.012), rng.uniform(400, 700), rng.uniform(2000, 3500))
            for _ in range(KERNELS)]
    bubbles = [ring_kernel(rng, rng.uniform(12500, 16000), rng.uniform(0.0008, 0.002), 0.08, 0.012)
               for _ in range(KERNELS)]
    plinks = [ring_kernel(rng, rng.uniform(1200, 8000), rng.uniform(0.002, 0.008), 0.15, 0.04)
              for _ in range(KERNELS)]

    channels = [np.zeros(N), np.zeros(N)]
    times = poisson_times(rng, ticks_per_second)
    d = drop_sizes(rng, rate, len(times))
    # Further drops are quieter: 1/r for drops spread evenly over the ground round the ear, out to the wash.
    distance = np.sqrt(rng.uniform(0.25, 1.0, len(times)))
    amplitude = (d / 2.0) ** 2.3 / distance
    kind = rng.random(len(times))
    left, right = pan(rng, len(times))
    for mask, kernels, gain in (
            (kind >= leaf_share + puddle_share, hard, 1.0),
            (kind < leaf_share, leaf, 0.55),
            ((kind >= leaf_share) & (kind < leaf_share + puddle_share), None, 0.0)):
        if kernels is None:
            continue
        for c, g in enumerate((left, right)):
            channels[c] += struck(rng, times[mask], amplitude[mask] * g[mask] * gain, kernels)

    # Into puddles: the impact, then a bubble for the drops that trap one.
    puddle = (kind >= leaf_share) & (kind < leaf_share + puddle_share)
    regular = puddle & (d >= 0.8) & (d <= 1.1)
    irregular = puddle & (d > 2.2) & (rng.random(len(times)) < 0.35)
    for c, g in enumerate((left, right)):
        channels[c] += struck(rng, times[puddle], amplitude[puddle] * g[puddle] * 0.6, hard)
        channels[c] += struck(rng, times[regular], 0.2 * g[regular] / distance[regular], bubbles)
        channels[c] += struck(rng, times[irregular], 0.7 * g[irregular] / distance[irregular], plinks)
    return np.stack(channels, axis=1)


def wash(rng, lowest, brightest, correlation=0.3):
    """The far drops: periodic noise with the ticks' spectrum less the air's toll on the highs."""
    curve = lambda f: band_curve(lowest, brightest, 2)(f) * (f / 1000.0) ** -0.5  # noqa: E731
    shared = spectral(rng, N, curve)
    own = [spectral(rng, N, curve) for _ in range(2)]
    a = np.sqrt(correlation)
    b = np.sqrt(1 - correlation)
    return np.stack([a * shared + b * own[0], a * shared + b * own[1]], axis=1)


def rms(x):
    return np.sqrt(np.mean(x ** 2))


def outdoor(rng, rate, ticks_per_second, wash_share, lowest, brightest):
    near = near_drops(rng, rate, ticks_per_second, leaf_share=0.3, puddle_share=0.2)
    far = wash(rng, lowest, brightest)
    far *= wash_share * rms(near) / rms(far)
    swell = gusts(rng)[:, None]
    return (near + far) * swell


def roof(rng):
    """A downpour on a roof, heard from under it."""
    thumps = [burst_kernel(rng, 0.03, rng.uniform(0.004, 0.012), rng.uniform(120, 200), rng.uniform(800, 1200))
              for _ in range(KERNELS)]
    channels = []
    times = poisson_times(rng, 900)
    d = drop_sizes(rng, HEAVY_RATE, len(times))
    amplitude = (d / 2.0) ** 2.3 * np.sqrt(rng.uniform(0.3, 1.0, len(times)))
    left, right = pan(rng, len(times))
    for g in (left, right):
        channels.append(struck(rng, times, amplitude * (0.7 + 0.3 * g), thumps))
    x = np.stack(channels, axis=1)
    # The panels' own modes, set ringing by the drumming.
    for f0 in (92.0, 141.0, 187.0, 236.0):
        f0 = round(f0 * LOOP_SECONDS) / LOOP_SECONDS
        swell = 0.5 + 0.5 * periodic_noise(rng, N, 0, 0.5, 2) / 3
        tone = np.sin(2 * np.pi * f0 * np.arange(N) / SR + rng.uniform(0, 2 * np.pi)) * swell
        x += 0.05 * rms(x) * tone[:, None] / rms(tone)
    # The mass law: 6 dB an octave down past ~600 Hz.
    spectrum = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(N, 1 / SR)
    spectrum *= (1 / np.sqrt(1 + (f / 600.0) ** 2))[:, None]
    x = np.fft.irfft(spectrum, N, axis=0)
    # The street outside, round the doors and windows.
    leak = wash(rng, 300, 2500, correlation=0.5)
    x += 10 ** (-15 / 20) * rms(x) / rms(leak) * leak * 3
    return x * gusts(rng, 1.0)[:, None]


def finish(x, target):
    x = x / np.abs(x).max() * 10 ** (-1 / 20)
    mono = x.mean(axis=1)
    volume = min(1.0, 10 ** ((target - loudness(mono)) / 20))
    return x, volume


def build():
    loops = {
        "rain_light": outdoor(np.random.default_rng(52001), LIGHT_RATE, 70, wash_share=1.4, lowest=500, brightest=6500),
        "rain_heavy": outdoor(np.random.default_rng(52002), HEAVY_RATE, 650, wash_share=2.4, lowest=350,
                              brightest=5000),
        "rain_roof": roof(np.random.default_rng(52003)),
    }
    return {name: finish(x, TARGETS[name]) for name, x in loops.items()}


def rate_gain(rate, design):
    return 10 ** (DB_PER_DECADE * np.log10(max(rate, 0.01) / design) / 20)


def mix_weights(rate):
    """RainView.MixWeights: the light and heavy loops' gains at this rate (mm/h)."""
    w = np.clip(np.log(max(rate, 1e-3) / LIGHT_RATE) / np.log(HEAVY_RATE / LIGHT_RATE), 0, 1)
    light = np.cos(w * np.pi / 2) * (rate_gain(rate, LIGHT_RATE) if rate < LIGHT_RATE else 1.0)
    heavy = np.sin(w * np.pi / 2) * (rate_gain(rate, HEAVY_RATE) if rate > HEAVY_RATE else 1.0)
    return light, heavy


def preview(loops, path):
    seconds = 60
    n = seconds * SR
    t = np.arange(n) / SR
    rate = np.interp(t, [0, 10, 35, 45, 60], [0.3, 2.0, 25.0, 25.0, 25.0])
    under = np.clip((t - 45) / 2, 0, 1)
    out = np.zeros((n, 2))
    idx = np.arange(n) % N
    for i0 in range(0, n, SR // 10):
        i1 = min(n, i0 + SR // 10)
        light, heavy = mix_weights(rate[i0])
        open_air = 1 - under[i0] * 0.9
        for name, gain in (("rain_light", light * open_air), ("rain_heavy", heavy * open_air),
                           ("rain_roof", under[i0] * rate_gain(rate[i0], HEAVY_RATE))):
            x, volume = loops[name]
            out[i0:i1] += x[idx[i0:i1]] * volume * gain
    write_stereo(path, out / max(1.0, np.abs(out).max()))
    print(f"preview: {path} ({seconds} s)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", help="write a minute of rain coming on, then going in under a roof")
    parser.add_argument("--out", help="write under this folder instead of Assets (to try changes)")
    args = parser.parse_args()

    loops = build()
    folder = os.path.join(args.out or ASSETS, *SOUND_PATH.split("/"))
    os.makedirs(folder, exist_ok=True)
    for name, (x, volume) in loops.items():
        write_loop_meta(folder, name)
        write_stereo(os.path.join(folder, name + ".wav"), x)
        written = write_flat_event(folder, SOUND_PATH, name, name, volume)
        mono = x.mean(axis=1)
        spectrum = np.abs(np.fft.rfft(mono)) ** 2
        f = np.fft.rfftfreq(len(mono), 1 / SR)
        centroid = np.sum(spectrum * f) / np.sum(spectrum)
        print(f"{name}: {LOOP_SECONDS:.0f} s, loudness {loudness(mono):.1f} dB, volume {volume:.4f} "
              f"({loudness(mono * volume):.1f} dB, target {TARGETS[name]}), centroid {centroid:.0f} Hz"
              + ("" if written else f"; {name}.sound exists, left as it is"))
    if args.preview:
        preview(loops, args.preview)


if __name__ == "__main__":
    main()
