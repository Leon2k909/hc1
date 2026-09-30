"""Checks Code/Weapons/BulletFlyby.cs offline: its crack synthesis (MakeCrack) and Whitham's N-wave levels.

Prints each load's crack at 0.5-50 m off its path: the overpressure, its peak in dB, its length, the band-limited
peak of a unit N-wave, and the level it plays at (a full-scale sample is 356 Pa). Keep it in step with BulletFlyby.

    python Tools/bullet_cracks.py [preview.wav]
    python Tools/bullet_cracks.py --scenes <scenes.wav>

With a path, it also writes an M855's cracks at 1, 5, 20 and 50 m, each with the sharp, firm, spiked, rounded and
soft fronts, 0.4 s apart.

--scenes writes what a listener hears when an M16A4 fired from 100 m, then 300 m, misses them by 0.5, 1, 3, 10 and
30 m: the crack and its ground reflection (hard ground, the head 1.7 m up), then the report, each where and when the
game plays it, the report at GunshotAudio's level (the shot's own WAV, full to 4 m, then -6 dB a doubling). It leaves
out the engine's air absorption and 3D panning. It prints each scene's loudness (K-weighted, loudest 100 ms) against a
rough real-world figure: in the field a crack a metre off the path carries 20-25 dB more energy than the report from
100 m.
"""
import math
import wave
import sys
from pathlib import Path

import numpy as np

SR = 44100
C = 340.29
P0 = 101325.0
FS = 356.0


def whitham(mach, b, d, l):
    m2 = mach * mach - 1
    p = 0.53 * P0 * m2 ** 0.125 * d / (b ** 0.75 * l ** 0.25)
    t = 1.82 * mach * b ** 0.25 * d / (C * m2 ** 0.375 * l ** 0.25)
    return p, t


def smooth(x, width):
    taps = max(1, int(round(width))) | 1
    if taps == 1:
        return x
    k = 0.5 - 0.5 * np.cos(2 * np.pi * (np.arange(taps) + 1) / (taps + 1))
    return np.convolve(x, k / k.sum(), mode="same")


def decimate(x, factor):
    taps = 64 * factor + 1
    half = taps // 2
    cutoff = 20000 / (SR * factor)
    n = np.arange(taps) - half
    sinc = np.where(n == 0, 2 * cutoff, np.sin(2 * np.pi * cutoff * n) / (np.pi * np.where(n == 0, 1, n)))
    ph = 2 * np.pi * np.arange(taps) / (taps - 1)
    k = sinc * (0.42 - 0.5 * np.cos(ph) + 0.08 * np.cos(2 * ph))
    k /= k.sum()
    y = np.convolve(x, k, mode="full")[half:half + len(x)]
    return y[::factor][: len(x) // factor]


FRONTS = {"sharp": (2e-6, 0), "firm": (8e-6, .15), "spiked": (3e-6, .5), "rounded": (25e-6, 0), "soft": (90e-6, 0)}


def crack(duration, front, frac=0.3):
    rise, spike = FRONTS[front]
    f = 16
    rate = SR * f
    lead = 0.001 + frac / SR
    w = np.zeros(int((lead + duration + 0.002) * rate))
    i = np.arange(len(w))
    start, end = lead * rate, (lead + duration) * rate
    inside = (i >= start) & (i < end)
    w[inside] = 1 - 2 * (i[inside] - start) / (end - start)
    if spike:
        dec = 8e-6 * rate
        w += np.where(i >= start, spike * np.exp(-(i - start) / dec), 0)
        w += np.where(i >= end, spike * np.exp(-(i - end) / dec), 0)
    w = smooth(w, rise * rate)
    y = decimate(w, f)
    return y, np.abs(y).max()


def write_wav(path, x):
    x = x if x.ndim == 2 else np.stack([x, x], axis=1)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    print("wrote", path)


# An M855's speed along its path: 905 m/s falling ~9% a 100 m (826 m/s at 100 m, 689 at 300 m, near its G7 table).
M855_DECAY = 1100.0


def m855_speed(x):
    return 905 * math.exp(-x / M855_DECAY)


def m855_flight(x):
    return M855_DECAY / 905 * (math.exp(x / M855_DECAY) - 1)


def scene_cracks(rng, miss, height=1.7):
    """The direct crack and the ground's, as BulletFlyby plays them: (samples, arrival) pairs."""
    out = []
    for b, gain in ((miss, 1.0), (math.hypot(miss, 2 * height), 0.9)):
        mach = m855_speed(rng) / C
        cone = math.sqrt(mach * mach - 1)
        p, t = whitham(mach, max(b, 0.15), 0.0057, 0.023)
        k = min(20, max(0, round(math.log(t / 40e-6) / math.log(1.2))))
        y, unit = crack(40e-6 * 1.2 ** k, "sharp")
        y = y / np.abs(y).max() * min(gain * p / FS * unit, 1)
        out.append((y, m855_flight(rng - b / cone) + b * mach / cone / C))
    return out


def scenes(path):
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    import shot_voicing
    shot = shot_voicing.read_wav(str(root.parent / "Assets/weapons/m16/sounds/m16_shot_01.wav"))
    step = 2.5
    plan = [(rng, miss) for rng in (100, 300) for miss in (0.5, 1, 3, 10, 30)]
    out = np.zeros((int(step * SR * len(plan)), 2))
    for n, (rng, miss) in enumerate(plan):
        cracks = scene_cracks(rng, miss)
        distance = math.hypot(rng, miss)
        report = shot * min(1, 4 / distance)
        first = min(t for _, t in cracks)
        scene = np.zeros((int(step * SR), 2))
        for y, t in cracks:
            s = int((t - first + 0.1) * SR)
            scene[s:s + len(y)] += y[:, None]
        crack_level = shot_voicing.loudest(scene)[0]
        s = int((distance / C - first + 0.1) * SR)
        e = min(len(scene), s + len(report))
        report_level = shot_voicing.loudest(report)[0]
        scene[s:e] += report[: e - s]
        out[n * len(scene):(n + 1) * len(scene)] += scene
        print(f"from {rng} m, missing by {miss:>4} m: crack {crack_level:6.1f} dB, report {report_level:6.1f} dB "
              f"({crack_level - report_level:+5.1f}), {1000 * (distance / C - first):.0f} ms apart")
    write_wav(path, out)


GUNS = {
    "M855 (M4) 905": (905, 0.0057, 0.023),
    "M80 (FAL) 840": (840, 0.00782, 0.0287),
    "PS (762) 715": (715, 0.00792, 0.0268),
    "9x19 (MP5) 380": (380, 0.00902, 0.0155),
    "SS190 715": (715, 0.0057, 0.0216),
}
if len(sys.argv) > 2 and sys.argv[1] == "--scenes":
    scenes(sys.argv[2])
    sys.exit()

for name, (v, d, l) in GUNS.items():
    mach = v / C
    row = []
    for b in (0.5, 1, 5, 20, 50):
        p, t = whitham(mach, b, d, l)
        k = min(20, max(0, round(math.log(t / 40e-6) / math.log(1.2))))
        _, unit = crack(40e-6 * 1.2 ** k, "sharp")
        peak = min(p / FS * unit, 1)
        row.append(f"b={b}: {p:6.0f} Pa {20*math.log10(p/2e-5):5.1f} dB {t*1e6:5.0f} us unit {unit:.2f} -> {20*math.log10(peak):6.1f} dBFS")
    print(name)
    for r in row:
        print("   ", r)

if len(sys.argv) > 1:
    # Cracks from an M855 at 1, 5, 20 and 50 m, each front, 0.4 s apart.
    out = np.zeros(int(SR * 0.4 * 20))
    pos = 0
    for b in (1, 5, 20, 50):
        p, t = whitham(905 / C, b, 0.0057, 0.023)
        for front in ("sharp", "firm", "spiked", "rounded", "soft"):
            y, unit = crack(t, front)
            y = y / unit * min(p / FS * unit, 1)
            s = int(pos * SR * 0.4)
            out[s:s + len(y)] += y
            pos += 1
    write_wav(sys.argv[1], out)
