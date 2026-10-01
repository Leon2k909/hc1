"""
The zombies' voices: groans while they shamble, a snarl as they swing, a grunt when they're hit and a groan as they die.
ZombieAI used to play s&box's zombie events, which the game never had, so the zombies were silent. These are
synthesised with no samples, from a source-filter model of a man's voice, the way speech synthesisers make one, so every
figure here can be re-tuned.

    python Tools/zombie_sounds.py [--preview <wav>] [--out <dir>]

Writes Assets/sounds/zombies/zombie_{groan,attack,pain,death}_<n>.wav, and a .sound event for each set if it doesn't
exist yet (an event may be tuned in the editor, so it isn't overwritten; delete one to have it rewritten). --preview
writes every take in a row; --out writes the sounds under another folder instead of Assets.

The source is the vocal folds' airflow, one Rosenberg pulse per cycle: the folds part over SQ / (1 + SQ) of the open
phase, snap shut over the rest, then stay closed. Its rate of change is what's radiated from the lips. On top of that:
- jitter and shimmer, the cycle-to-cycle wobble of period and amplitude every voice has (about 1% and 6% in a healthy
  voice, several times that in a rough one);
- creak (vocal fry): slack, thick folds, cycles at 28-55 Hz with the folds shut most of each, irregular and often in
  pairs. It's the rattle a groan trails off into as the breath runs out;
- growl: the false folds and the aryepiglottic folds flapping at half the folds' rate (period doubling), with turbulence
  in the narrowed larynx, as in a growled shout;
- roughness: an irregular flutter of 30-60 Hz;
- breath: aspiration through the open folds, and an exhale on its own.
The vocal tract is five formant resonances in cascade (Klatt's resonators), gliding from vowel to vowel. The vowels are
Hillenbrand et al.'s (1995) averages for men, scaled for a large man's 18.5 cm tract. The snarl and the groans narrow
the pharynx, which raises F1 and lowers F2, as a strained, constricted voice does. A dying man's breath bubbles through
what's in his airway: wet crackles of 300-1500 Hz, 15-35 a second.

Levels are a real voice's against a footstep's (a walk on concrete, about 63 dB(A) at a pace, -36 dB here), squeezed the
way the game's mix squeezes the gap between a gunshot and a footstep, 74 dB to 32 (0.43 times; see Tools/foley_voicing.py):
- a groan at ordinary effort, about 72 dB(A) at a metre: -32 dB;
- a death groan, about 78: -30 dB;
- a grunt of pain, about 80: -29 dB;
- the snarl of an attack, a growled shout, about 92: -23.5 dB.
Each is heard out to where a voice that loud carries in the game's falloff (Tools/world_sounds.py's).
"""

import argparse
import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_sounds as ws  # noqa: E402
from world_sounds import SR, add, band, build_set, describe, gap, seconds_axis, surroundings, unit  # noqa: E402

FOLDER = ("sounds", "zombies")
SOUND_PATH = "sounds/zombies"
REFERENCE = 64

# Name: (target loudness, takes, distance, volume spread in dB, pitch range).
SETS = {
    "zombie_groan": (-32.0, 8, 2000, 3.0, "0.92 1.06"),
    "zombie_attack": (-23.5, 6, 3000, 1.5, "0.94 1.05"),
    "zombie_pain": (-29.0, 6, 2400, 2.0, "0.94 1.06"),
    "zombie_death": (-30.0, 4, 2400, 1.5, "0.95 1.04"),
}

# F1, F2, F3 for men (Hillenbrand et al. 1995), then F4 and F5.
VOWELS = {
    "u": (378, 997, 2343),     # boot
    "U": (469, 1122, 2434),    # book
    "o": (652, 997, 2538),     # caught
    "a": (768, 1333, 2522),    # father
    "A": (623, 1200, 2550),    # but
    "ae": (588, 1952, 2601),   # bat
    "e": (500, 1500, 2500),    # the schwa
}
HIGH_FORMANTS = (3400, 4300)
BANDWIDTHS = (90, 110, 170, 250, 300)
# An 18.5 cm tract against the average man's 17.5.
TRACT_SCALE = 0.95
BLOCK = 64


def track(points, t):
    """Piecewise-linear (time, value) breakpoints, sampled at times t."""
    times, values = zip(*points)
    return np.interp(t, times, values)


def smooth_track(points, t):
    """Breakpoints joined by half-cosine eases, for envelopes with no corners."""
    times = np.array([p[0] for p in points])
    values = np.array([p[1] for p in points])
    i = np.clip(np.searchsorted(times, t, side="right") - 1, 0, len(times) - 2)
    span = np.maximum(times[i + 1] - times[i], 1e-9)
    u = np.clip((t - times[i]) / span, 0.0, 1.0)
    w = 0.5 - 0.5 * np.cos(np.pi * u)
    return values[i] * (1 - w) + values[i + 1] * w


def drift(rng, n, rate, depth):
    """A slow random wander (low-passed noise at `rate` Hz), `depth` at one standard deviation."""
    x = band(rng.standard_normal(n + SR), 0, rate, order=2)[SR:]
    return 1.0 + depth * x / max(x.std(), 1e-9)


def rosenberg(n, oq, sq):
    """One cycle of glottal flow, n samples: open for oq of it, opening over sq / (1 + sq) of that."""
    k = np.arange(n)
    opening = max(1.0, oq * n * sq / (1 + sq))
    closing = max(1.0, oq * n / (1 + sq))
    g = np.where(k < opening, 0.5 - 0.5 * np.cos(np.pi * k / opening), 0.0)
    shut = (k >= opening) & (k < opening + closing)
    g[shut] = np.cos(0.5 * np.pi * (k[shut] - opening) / closing)
    return g


def glottis(rng, n, f0, amp, creak, growl, oq, jitter, shimmer):
    """The folds' flow and its rate of change (what's radiated), pulse by pulse. f0, amp and creak are per sample."""
    flow = np.zeros(n + SR // 10)
    t = 0
    k = 0
    while t < n:
        c = creak[t]
        if rng.random() < c:
            # A creak cycle: long, irregular, the folds shut most of it, sometimes a second pulse just after the first.
            period = 1.0 / rng.uniform(28, 55)
            cycle_oq, a = 0.3, rng.uniform(0.55, 1.15)
            double = rng.random() < 0.3
        else:
            period = (1.0 / f0[t]) * (1 + jitter * rng.standard_normal())
            cycle_oq, a = oq, 1.0 + shimmer * rng.standard_normal()
            double = False
        side = 1.0 if k % 2 else -1.0
        period *= 1 + 0.06 * growl * side
        a *= 1 + 0.55 * growl * side
        length = max(16, int(round(period * SR)))
        pulse = amp[t] * max(a, 0.05) * rosenberg(length, cycle_oq, 2.5)
        end = min(len(flow), t + length)
        flow[t:end] += pulse[: end - t]
        if double:
            lag = int(rng.uniform(0.003, 0.006) * SR)
            add(flow, 0.5 * pulse[: length // 2], (t + lag) / SR)
        t += length
        k += 1
    flow = flow[:n]
    return flow, np.diff(flow, prepend=0.0)


def formant_tracks(vowels, t, pharynx):
    """Each block's five formants (Hz), gliding through the (time, vowel) breakpoints."""
    names = [v for _, v in vowels]
    times = [time for time, _ in vowels]
    out = np.zeros((len(t), 5))
    for k in range(3):
        log_f = [np.log(VOWELS[v][k]) for v in names]
        out[:, k] = np.exp(np.interp(t, times, log_f))
    out[:, 3], out[:, 4] = HIGH_FORMANTS
    # A narrowed pharynx raises F1 and lowers F2.
    out[:, 0] *= 1 + 0.12 * pharynx
    out[:, 1] *= 1 - 0.08 * pharynx
    return out * TRACT_SCALE


def tract(x, formants, widen):
    """Klatt's resonators in cascade (unit gain at 0 Hz), their coefficients set block by block."""
    y = x
    for k in range(5):
        bw = BANDWIDTHS[k] * widen
        r = np.exp(-np.pi * bw / SR)
        state = np.zeros(2)
        out = np.empty_like(y)
        for b in range(0, len(y), BLOCK):
            f = min(formants[b // BLOCK, k], SR * 0.45)
            c = -r * r
            bb = 2 * r * np.cos(2 * np.pi * f / SR)
            seg, state = signal.lfilter([1 - bb - c], [1, -bb, -c], y[b:b + BLOCK], zi=state)
            out[b:b + BLOCK] = seg
        y = out
    return y


def voice(rng, seconds, f0, voicing, breath, vowels, creak=((0, 0.0),), growl=0.0, rough=0.2, oq=0.6,
          pharynx=0.3, jitter=0.012, shimmer=0.07):
    """A voiced sound `seconds` long. f0, voicing, breath and creak are (time, value) breakpoints: the folds' rate in
    Hz, how hard they're driven (0-1), aspiration and exhaled breath (against the voice's level) and the share of creak
    cycles. vowels is (time, vowel) breakpoints."""
    t = seconds_axis(seconds)
    n = len(t)
    pitch = track(f0, t) * drift(rng, n, 3.0, 0.025)
    amp = smooth_track(voicing, t)
    flow, voiced = glottis(rng, n, pitch, amp, np.clip(track(creak, t), 0, 1), growl, oq, jitter + 0.03 * rough,
                           shimmer + 0.1 * rough)
    voiced = voiced / max(np.sqrt(np.mean(voiced[amp > 0.3] ** 2)) if np.any(amp > 0.3) else 1.0, 1e-9)

    # Roughness: the flow flutters irregularly at 30-60 Hz.
    flutter_rate = np.cumsum(rng.uniform(30, 60) * drift(rng, n, 4.0, 0.3)) / SR
    voiced *= 1 - 0.45 * rough * (0.5 + 0.5 * np.sin(2 * np.pi * flutter_rate))

    # Aspiration through the open folds, and breath on its own where the folds are still.
    open_share = flow / max(flow.max(), 1e-9)
    gate = np.clip(amp, 0, 1) * (0.25 + 0.75 * open_share) + (1 - np.clip(amp, 0, 1))
    air = band(rng.standard_normal(n), 400, 7000) * gate * smooth_track(breath, t)
    # The growl's turbulence in the narrowed larynx, pulsing with the cycles.
    rasp = growl * 0.6 * band(rng.standard_normal(n), 900, 4500) * np.clip(amp, 0, 1) * (0.3 + 0.7 * open_share)

    formants = formant_tracks(vowels, (np.arange(0, n, BLOCK) + BLOCK / 2) / SR, pharynx)
    out = tract(voiced + air + rasp, formants, 1.0 + 0.4 * rough)
    return band(out, 55, 9000, order=2)


def gurgle(rng, seconds, rate, level):
    """Breath bubbling through what's in the airway: wet crackles, each a bubble's short ring."""
    out = np.zeros(int(seconds * SR) + SR // 10)
    count = rng.poisson(rate * seconds)
    for at in np.sort(rng.uniform(0, seconds, count)):
        f = rng.uniform(300, 1500)
        tau = rng.uniform(0.002, 0.007)
        u = seconds_axis(6 * tau)
        # A bubble's pitch rises as it closes.
        ring = np.sin(2 * np.pi * f * u * (1 + 8 * u)) * np.exp(-u / tau)
        add(out, rng.lognormal(0, 0.5) * ring, at)
    return level * out[: int(seconds * SR)]


def exhale(rng, seconds, vowel, level, pharynx=0.3):
    """Breath out through a mouth shaped for `vowel`, fading."""
    return voice(rng, seconds, [(0, 80), (seconds, 70)], [(0, 0.0), (seconds, 0.0)],
                 [(0, level), (0.3 * seconds, level * 0.8), (seconds, 0.0)], [(0, vowel), (seconds, vowel)],
                 pharynx=pharynx)


def place(parts, seconds):
    out = np.zeros(int(seconds * SR))
    for x, at in parts:
        add(out, x, at)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# The sets

def moan(rng):
    d = rng.uniform(1.1, 1.9)
    start = rng.uniform(86, 104)
    vowels = [("U", "o", "A"), ("u", "o", "a"), ("o", "A", "e"), ("U", "A", "o")][rng.integers(4)]
    x = voice(rng, d,
              f0=[(0, start), (0.35 * d, start * rng.uniform(1.05, 1.18)), (0.75 * d, start * 0.92),
                  (d, rng.uniform(62, 75))],
              voicing=[(0, 0.0), (0.14 * d, 0.85), (0.42 * d, 1.0), (0.78 * d, 0.65), (d, 0.0)],
              breath=[(0, 0.6), (0.15 * d, 0.3), (d, 0.4)],
              vowels=[(0, vowels[0]), (0.45 * d, vowels[1]), (d, vowels[2])],
              creak=[(0, 0.08), (0.55 * d, 0.15), (0.82 * d, 0.65), (d, 0.95)],
              growl=rng.uniform(0.0, 0.25), rough=rng.uniform(0.25, 0.45), oq=0.66, pharynx=0.35)
    tail = exhale(rng, 0.35, vowels[2], 0.35)
    return place([(x, 0.0), (tail, d - 0.05)], d + 0.35)


def wet_moan(rng):
    out = moan(rng)
    d = len(out) / SR
    crackle = unit(gurgle(rng, d, rng.uniform(12, 22), 1.0))
    crackle *= smooth_track([(0, 0.0), (0.35 * d, 0.5), (0.8 * d, 1.0), (d, 0.0)], seconds_axis(d))[:len(crackle)]
    return out + 0.14 * np.abs(out).max() * crackle


def growl_rumble(rng):
    d = rng.uniform(0.8, 1.3)
    f = rng.uniform(72, 86)
    vowel = ["o", "A", "U"][rng.integers(3)]
    x = voice(rng, d,
              f0=[(0, f), (0.5 * d, f * rng.uniform(1.0, 1.1)), (d, f * 0.9)],
              voicing=[(0, 0.0), (0.12 * d, 0.9), (0.6 * d, 1.0), (d, 0.0)],
              breath=[(0, 0.4), (d, 0.35)],
              vowels=[(0, vowel), (d, vowel)],
              creak=[(0, 0.45), (d, 0.75)],
              growl=rng.uniform(0.6, 0.8), rough=rng.uniform(0.5, 0.7), oq=0.6, pharynx=0.6)
    return place([(x, 0.0), (exhale(rng, 0.3, vowel, 0.3), d - 0.05)], d + 0.3)


def rasp_then_moan(rng):
    """Breath dragged in through a slack larynx (ingressive creak), then the moan."""
    d = rng.uniform(0.3, 0.45)
    inhale = voice(rng, d, f0=[(0, 60), (d, 70)], voicing=[(0, 0.0), (0.5 * d, 0.25), (d, 0.0)],
                   breath=[(0, 0.0), (0.4 * d, 0.9), (d, 0.0)], vowels=[(0, "A"), (d, "e")],
                   creak=[(0, 1.0), (d, 1.0)], rough=0.8, pharynx=0.8)
    groan = moan(rng)
    return place([(0.6 * inhale, 0.0), (groan, d + rng.uniform(0.05, 0.12))], d + 0.12 + len(groan) / SR)


def zombie_groan(rng, take):
    return surroundings(rng, [moan, growl_rumble, wet_moan, rasp_then_moan][take % 4](rng), 0.5, 0.8)


def zombie_attack(rng, take):
    """A growled shout as it lunges: hard onset, pitch thrown up, a wide-open mouth, the larynx narrowed."""
    d = rng.uniform(0.55, 0.85)
    vowels = [("A", "ae", "A"), ("a", "a", "A"), ("ae", "a", "o")][take % 3]
    x = voice(rng, d,
              f0=[(0, rng.uniform(115, 135)), (0.25 * d, rng.uniform(165, 200)), (0.6 * d, rng.uniform(150, 175)),
                  (d, rng.uniform(105, 125))],
              voicing=[(0, 0.0), (0.05, 1.0), (0.7 * d, 0.9), (d, 0.0)],
              breath=[(0, 0.5), (0.06, 0.2), (d, 0.35)],
              vowels=[(0, vowels[0]), (0.4 * d, vowels[1]), (d, vowels[2])],
              creak=[(0, 0.0), (0.8 * d, 0.1), (d, 0.5)],
              growl=rng.uniform(0.55, 0.85), rough=rng.uniform(0.4, 0.6), oq=0.45, pharynx=0.8)
    return surroundings(rng, place([(x, 0.0), (exhale(rng, 0.2, vowels[2], 0.4, 0.8), d - 0.04)], d + 0.2), 0.5, 0.8)


def zombie_pain(rng, take):
    """A grunt: the folds burst apart on a glottal stop, the pitch falls, and it trails into creak and breath."""
    d = rng.uniform(0.22, 0.42)
    vowels = [("A", "e"), ("U", "A"), ("a", "e")][take % 3]
    x = voice(rng, d,
              f0=[(0, rng.uniform(150, 185)), (0.3 * d, rng.uniform(130, 160)), (d, rng.uniform(85, 105))],
              voicing=[(0, 0.0), (0.012, 1.0), (0.5 * d, 0.6), (d, 0.0)],
              breath=[(0, 0.3), (d, 0.45)],
              vowels=[(0, vowels[0]), (d, vowels[1])],
              creak=[(0, 0.0), (0.6 * d, 0.2), (d, 0.8)],
              growl=rng.uniform(0.15, 0.35), rough=0.4, oq=0.5, pharynx=0.5)
    # The glottal stop's release: a short puff.
    puff = band(rng.standard_normal(int(0.02 * SR)), 500, 5000) * np.exp(-seconds_axis(0.02) / 0.005) * 0.6
    return surroundings(rng, place([(puff, 0.0), (x, 0.004), (exhale(rng, 0.18, vowels[1], 0.35), d - 0.03)], d + 0.2),
                        0.5, 0.8)


def zombie_death(rng, take):
    """A falling groan as the breath goes out of it, sinking into creak, then the last breath bubbling out."""
    d = rng.uniform(1.2, 1.8)
    x = voice(rng, d,
              f0=[(0, rng.uniform(125, 145)), (0.2 * d, rng.uniform(130, 150)), (0.6 * d, rng.uniform(85, 95)),
                  (d, rng.uniform(50, 60))],
              voicing=[(0, 0.0), (0.06 * d, 1.0), (0.45 * d, 0.8), (0.85 * d, 0.35), (d, 0.0)],
              breath=[(0, 0.35), (0.6 * d, 0.4), (d, 0.6)],
              vowels=[(0, "A"), (0.5 * d, "o"), (d, "U")],
              creak=[(0, 0.05), (0.4 * d, 0.2), (0.75 * d, 0.7), (d, 1.0)],
              growl=rng.uniform(0.2, 0.4), rough=0.5, oq=0.62, pharynx=0.5)
    last = exhale(rng, 0.45, "U", 0.45)
    total = d + 0.45
    out = place([(x, 0.0), (last, d - 0.05)], total)
    crackle = unit(gurgle(rng, total, rng.uniform(20, 35), 1.0))
    crackle *= smooth_track([(0, 0.0), (0.5 * d, 0.3), (d, 1.0), (total, 0.0)], seconds_axis(total))[:len(crackle)]
    return surroundings(rng, out + 0.16 * np.abs(out).max() * crackle, 0.5, 0.8)


MAKERS = {
    "zombie_groan": zombie_groan,
    "zombie_attack": zombie_attack,
    "zombie_pain": zombie_pain,
    "zombie_death": zombie_death,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", help="write a WAV with every set's takes in a row, levelled per set")
    parser.add_argument("--out", help="write the sounds under this folder instead of Assets")
    args = parser.parse_args()
    folder = os.path.join(args.out or ws.ASSETS, *FOLDER)
    os.makedirs(folder, exist_ok=True)

    preview = []
    for index, (name, (target, count, distance, spread, pitch)) in enumerate(SETS.items()):
        names, takes, volume = build_set(name, MAKERS[name], count, 11000 + 100 * index, target)
        for take_name, x in zip(names, takes):
            ws.write_wav(os.path.join(folder, take_name + ".wav"), x)
        if not ws.write_event(folder, SOUND_PATH, name, names, volume, spread, pitch, distance, REFERENCE):
            print(f"  {name}.sound exists, left as it is")
        describe(name, takes, volume)
        section = []
        for x in takes:
            section += [x * volume, gap(0.6)]
        preview += section + [gap(1.0)]

    if args.preview:
        ws.write_wav(args.preview, unit(np.concatenate(preview)) * 0.8)
        print(f"preview: {args.preview}")


if __name__ == "__main__":
    main()
