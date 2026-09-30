"""Checks Code/Weapons/BulletFlyby.cs offline: its crack synthesis (MakeCrack) and Whitham's N-wave levels.

Prints each load's crack at 0.5-50 m off its path: the overpressure, its peak in dB, its length, the band-limited
peak of a unit N-wave, and the level it plays at (a full-scale sample is 356 Pa). Keep it in step with BulletFlyby.

    python Tools/bullet_cracks.py [preview.wav]
    python Tools/bullet_cracks.py --scenes <scenes.wav>

With a path, it also writes an M855's cracks at 1, 5, 20 and 50 m, each with the sharp, firm, spiked, rounded and
soft fronts, 0.4 s apart.

--scenes writes what a listener hears when an M16A4 fired from 100 m, then 300 m, misses them by 0.5, 1, 3, 10 and
30 m: the crack, its ground reflection and the ground's scattered tail (hard ground, the path and the head 1.7 m up),
then the report, each where and when the game plays it, the report at GunshotAudio's level (the shot's own WAV, full to
4 m, then -6 dB a doubling). Each scene plays twice: as it was before the tail and the ear's reflex, then with them
(BulletFlyby.PlayScatter, AcousticReflex). It leaves out the engine's air absorption and 3D panning. It prints each
scene's loudness (K-weighted, loudest 100 ms): the crack with its tail, the tail alone, and the report without and
with the reflex. A rough real-world figure to hold it against: in the field a crack a metre off the path is 15-25 dB
over the report from 100 m, and 25-35 dB over it from 300 m.
"""
import math
import wave
import sys
from pathlib import Path

import numpy as np
from scipy import signal

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


def m855_shock(along, b):
    """TryShock for an M855: (pressure, length, arrival, Mach) of the crack reaching a point `along` metres down the
    path and `b` off it, or None."""
    if along <= 0:
        return None

    def behind(x):
        mach = m855_speed(x) / C
        return math.inf if mach <= 1.03 else x + max(b, 0.15) / math.sqrt(mach * mach - 1) - along

    if behind(0) > 0 or behind(along) < 0:
        return None
    low, high = 0.0, along
    for _ in range(24):
        middle = (low + high) / 2
        if behind(middle) < 0:
            low = middle
        else:
            high = middle
    mach = max(m855_speed(low) / C, 1.03)
    p, t = whitham(mach, max(b, 0.15), 0.0057, 0.023)
    return p, t, m855_flight(low) + math.hypot(along - low, b) / C, mach


def scene_cracks(rng, miss, height=1.7):
    """The direct crack and the ground's, as BulletFlyby plays them: (samples, arrival) pairs, and the share of its
    pressure the direct crack plays at (under 1 when it's capped at full scale)."""
    out = []
    share = 1.0
    for b, gain in ((miss, 1.0), (math.hypot(miss, 2 * height), 0.9)):
        p, t, arrival, _ = m855_shock(rng, b)
        k = min(20, max(0, round(math.log(t / 40e-6) / math.log(1.2))))
        y, unit = crack(40e-6 * 1.2 ** k, "sharp")
        wanted = gain * p / FS * unit
        y = y / np.abs(y).max() * min(wanted, 1)
        if not out:
            share = min(wanted, 1) / wanted
        out.append((y, arrival))
    return out, share


# BulletFlyby's tail: its windows, its grains' decays and cracks, and the ground's patches (m).
TAIL_WINDOWS = (0, 0.006, 0.02, 0.06, 0.18, 0.6)
TAIL_DECAYS = (0.003, 0.008, 0.02, 0.05, 0.12)
TAIL_CRACKS = (4, 8, 11, 15)
GROUND_ALONG = (-60, -30, -15, -7, -3, -1, 0, 1, 3, 7, 15, 30, 60, 120)
GROUND_ACROSS = (-30, -15, -7, -3, -1, 0, 1, 3, 7, 15, 30)


def widths(grid):
    grid = np.array(grid, float)
    middles = (grid[1:] + grid[:-1]) / 2
    low = np.concatenate([[grid[0] - (middles[0] - grid[0])], middles])
    high = np.concatenate([middles, [grid[-1] + (grid[-1] - middles[-1])]])
    return high - low


def grain(decay, crack_index, seed):
    """MakeScatter: rounded cracks in a Poisson train, 6000 a second, Gaussian weights, exp(-t / decay)."""
    y, _ = crack(40e-6 * 1.2 ** crack_index, "rounded")
    random = np.random.default_rng(seed)
    span = 5 * decay
    tail = np.zeros(int(span * SR) + len(y) + 1)
    time = 0.0
    while True:
        time += random.exponential(1 / 6000)
        if time > span:
            return tail
        at = int(time * SR)
        tail[at:at + len(y)] += random.normal() * math.exp(-time / decay) * min(1, time / 0.0005) * y


def scene_tail(rng, miss, share, height=1.7, scatter=0.12):
    """PlayScatter over hard ground: (samples, start in seconds after the direct crack) per window, and the tail's
    energy in each."""
    direct = m855_shock(rng, miss)[2]
    windows = len(TAIL_WINDOWS) - 1
    energy, first, lags, lengths = np.zeros(windows), np.full(windows, np.inf), np.zeros(windows), np.zeros(windows)
    for u, du in zip(GROUND_ALONG, widths(GROUND_ALONG)):
        for v, dv in zip(GROUND_ACROSS, widths(GROUND_ACROSS)):
            r = math.sqrt(u * u + (miss - v) ** 2 + height * height)
            wave = m855_shock(rng + u, math.hypot(v, height))
            if wave is None:
                continue
            p, t, arrival, mach = wave
            # The wave comes down onto the patch from the path's point it left.
            travel = math.hypot(v, height) * mach / math.sqrt(mach * mach - 1)
            cos_in = height / travel
            lag = max(0.0, arrival + r / C - direct)
            k = np.searchsorted(TAIL_WINDOWS, lag, side="right") - 1
            if k >= windows:
                continue
            e = scatter * p * p * t / 3 * cos_in * du * dv * (height / r) / (math.pi * r * r)
            energy[k] += e
            first[k] = min(first[k], lag)
            lags[k] += e * lag
            lengths[k] += e * t
    out = []
    for k in range(windows):
        if energy[k] <= 0:
            continue
        decay = max(lags[k] / energy[k] - first[k], 0.001)
        decay = min(TAIL_DECAYS, key=lambda d: abs(math.log(decay / d)))
        index = math.log(lengths[k] / energy[k] / 40e-6) / math.log(1.2)
        index = min(TAIL_CRACKS, key=lambda c: abs(c - index))
        g = grain(decay, index, k)
        g *= math.sqrt(energy[k] / ((g * g).sum() / SR)) * share / FS
        g /= max(1, np.abs(g).max())
        out.append((g, first[k]))
    return out, energy


def reflex(p, t, arrival, n):
    """AcousticReflex's contraction, sample by sample over n samples from the shot, after a crack of p Pa for t s."""
    level = 10 * math.log10(p * p / 3 * t / 0.2 / (20e-6) ** 2)
    strength = min(max((level - 85) / 25, 0), 1)
    onset = arrival + 0.12 + (0.03 - 0.12) * strength
    since = np.arange(n) / SR - onset
    shape = lambda x: np.exp(-x / 0.15) - np.exp(-x / 0.03)
    peak = shape(math.log(0.15 / 0.03) * 0.03 * 0.15 / 0.12)
    return np.where(since > 0, strength * np.clip(shape(np.maximum(since, 0)) / peak, 0, 1), 0)


def reflex_filter(x, contraction):
    """ReflexProcessor: two first-order low shelves at 2 kHz, each x - cut * lowpass(x), the cut eased over 5 ms."""
    target = 1 - 10 ** (-15 * contraction / 40)
    ease = 1 - math.exp(-1 / (0.005 * SR))
    cut = signal.lfilter([ease], [1, -(1 - ease)], target)[:, None]
    alpha = 1 - math.exp(-2 * math.pi * 2000 / SR)
    lowpass = lambda v: signal.lfilter([alpha], [1, -(1 - alpha)], v, axis=0)
    y = x - cut * lowpass(x)
    return y - cut * lowpass(y)


def scenes(path):
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    import shot_voicing
    shot = shot_voicing.read_wav(str(root.parent / "Assets/weapons/m16/sounds/m16_shot_01.wav"))
    step = 2.5
    n = int(step * SR)
    plan = [(rng, miss) for rng in (100, 300) for miss in (0.5, 1, 3, 10, 30)]
    out = np.zeros((2 * n * len(plan), 2))
    for i, (rng, miss) in enumerate(plan):
        cracks, share = scene_cracks(rng, miss)
        tail, energy = scene_tail(rng, miss, share)
        distance = math.hypot(rng, miss)
        p, t, direct, _ = m855_shock(rng, miss)
        first = min(t for _, t in cracks)
        # The scene starts 0.1 s before the first crack; times are from the shot.
        zero = first - 0.1
        crack_part, tail_part, report_part = np.zeros((n, 2)), np.zeros((n, 2)), np.zeros((n, 2))
        for y, at in cracks:
            s = int((at - zero) * SR)
            crack_part[s:s + len(y)] += y[:, None]
        for y, start in tail:
            s = int((direct + start - 0.001 - zero) * SR)
            e = min(n, s + len(y))
            tail_part[s:e] += y[: e - s, None]
        report = shot * min(1, 4 / distance)
        s = int((distance / C - zero) * SR)
        e = min(n, s + len(report))
        report_part[s:e] += report[: e - s]

        contraction = reflex(p, t, direct - zero, n)
        old = crack_part + report_part
        new = reflex_filter(crack_part + tail_part + report_part, contraction)
        out[2 * i * n:(2 * i + 1) * n] = old
        out[(2 * i + 1) * n:(2 * i + 2) * n] = new

        loud = lambda x: shot_voicing.loudest(x)[0]
        crack_level = loud(crack_part)
        new_crack = loud(reflex_filter(crack_part + tail_part, contraction))
        report_level = loud(report_part)
        dulled = loud(reflex_filter(report_part, contraction))
        at_report = contraction[int((distance / C - zero) * SR)]
        print(f"from {rng} m, missing by {miss:>4} m: crack {crack_level:6.1f} dB (with its tail {new_crack:6.1f}, "
              f"the tail alone {loud(tail_part) - crack_level:+5.1f}), report {report_level:6.1f} dB, "
              f"{dulled:6.1f} after the reflex ({at_report:.2f} contracted); crack over report "
              f"{crack_level - report_level:+5.1f} -> {new_crack - dulled:+5.1f}, {1000 * (distance / C - first):.0f} ms apart")
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
