"""Checks Code/Weapons/BulletFlyby.cs offline: its crack synthesis (MakeCrack) and Whitham's N-wave levels.

Prints each load's crack at 0.5-50 m off its path: the overpressure, its peak in dB, its length, the band-limited
peak of a unit N-wave, and the level it plays at (a full-scale sample is 356 Pa). Keep it in step with BulletFlyby.

    python Tools/bullet_cracks.py [preview.wav]

With a path, it also writes an M855's cracks at 1, 5, 20 and 50 m, each with the sharp, firm, spiked, rounded and
soft fronts, 0.4 s apart.
"""
import math
import wave
import sys
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


GUNS = {
    "M855 (M4) 905": (905, 0.0057, 0.023),
    "M80 (FAL) 840": (840, 0.00782, 0.0287),
    "PS (762) 715": (715, 0.00792, 0.0268),
    "9x19 (MP5) 380": (380, 0.00902, 0.0155),
    "SS190 715": (715, 0.0057, 0.0216),
}
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
    pcm = (np.clip(out, -1, 1) * 32767).astype("<i2")
    with wave.open(sys.argv[1], "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    print("wrote", sys.argv[1])
