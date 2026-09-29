"""
Voicing a ripped Call of Duty shot away from CoD's sound design, towards what a shooter hears from the real gun fired
outdoors. Each gun's script (ak105_shot.py, m16_shot.py) holds its Voicing, what its rip gets wrong and where the rip
comes from; this holds the steps they share.

voice() takes one recording (float, turned down to the gun's level, not limited), and:
1. Pitches it (Voicing.pitch), so it's not CoD's shot note for note.
2. Low end: a causal high-pass (for the designed sub "drop" CoD puts under its shots), and after the blast's first few
   tens of ms everything under low_split eases down low_cut_db, so the thump stays but the boom doesn't hang on. A rip
   with a designed tail of its own (rip_tail_db) has all of it eased down after rip_tail_hold: at the shooter, all
   that follows the blast is the surroundings, which step 5 adds.
3. The blast: its presence lifted for its first ~25 ms, the crack at the shooter's ear. The bullet's own supersonic
   crack isn't added: its shock cone runs forward from the muzzle and never reaches the shooter.
4. The ground: the shot off the ground a few ms after the direct sound (muzzle and ear 1.5 m up, the muzzle
   ground_delay's distance ahead), about 18 dB down (the longer path, and grass or dirt reflecting about half) and
   dulled.
5. Surroundings: echoes of the blast from what's further off (trees, walls, the lie of the land), from 35 ms to 1.4 s,
   denser, weaker and duller the further they've come (air takes the top off), and different in each ear.
Each recording makes takes with different echoes (Voicing.takes), so a burst doesn't repeat one sound.

finish() matches loudness to the rip as the gun's assets script levelled it (K-weighted, loudest 100 ms). A voiced
blast is peakier, and the rip's limiter (1 ms attack, 50 ms release) would have to take 9-14 dB off it to get there,
ducking the whole blast. So a soft clipper (4x oversampled, its knee at 70% of -1 dBFS) takes the blast's peaks, a few
dB, before the limiter holds -1 dBFS. What it takes off sits 25 dB under the shot, the kind of edge a close recording of
a gunshot has anyway. Then the echoes go in, tail_at_400ms under the shot.
"""
import argparse
import json
import os
import tempfile
import warnings
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import minimum_filter1d

SR = 44100
CEILING = 0.891
CLIP_KNEE = 0.7


@dataclass(frozen=True)
class Voicing:
    # The takes are <name>_01.wav, <name>_02.wav, ...
    name: str
    pitch: float
    # The sound event's pitch spread per round.
    event_pitch: str
    # Each take: (which recording, from ripped()'s list; the echoes' seed).
    takes: tuple[tuple[int, int], ...]
    # For --preview: the rip's own event pitch spread, the gun's rate, and the bursts it fires (rounds each).
    rip_pitch: tuple[float, float] = (0.96, 1.04)
    rpm: int = 600
    preview_bursts: tuple[int, ...] = (8,)
    high_pass: float = 40.0
    low_split: float = 110.0
    low_cut_db: float = -5.0
    low_hold: float = 0.035
    low_ease: float = 0.035
    # The rip's own sound after the blast, eased down this far from rip_tail_hold after the onset (0: left alone).
    rip_tail_db: float = 0.0
    rip_tail_hold: float = 0.1
    rip_tail_ease: float = 0.1
    presence: tuple[float, float] = (1500.0, 5000.0)
    presence_db: float = 4.0
    presence_hold: float = 0.025
    presence_ease: float = 0.02
    ground_delay: float = 0.0072
    ground_gain: float = 0.12
    ground_dull: float = 2500.0
    echo_start: float = 0.035
    echo_end: float = 1.4
    echo_t60: float = 1.5
    # From each time on, echoes are low-passed at this frequency (Hz).
    echo_dulling: tuple[tuple[float, float], ...] = (
        (0.035, 7000.0), (0.1, 4500.0), (0.2, 3000.0), (0.4, 2000.0), (0.7, 1300.0))
    # The echoes' K-weighted 100 ms level 0.4 s after the shot's loudest 100 ms, relative to it.
    tail_at_400ms: float = -33.0


def read_wav(path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", wavfile.WavFileWarning)
        sr, x = wavfile.read(path)
    assert sr == SR, (path, sr)
    x = x.astype(np.float64) / 32768.0
    return x if x.ndim == 2 else np.stack([x, x], axis=1)


def write_wav(path, x):
    pcm = np.round(np.clip(x, -1.0, 32767 / 32768) * 32768).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def k_weight(x):
    """BS.1770's K-weighting (its high shelf and high-pass), designed for SR."""
    def biquad(kind, fc, q, gain_db=0.0):
        a_ = 10 ** (gain_db / 40)
        w0 = 2 * np.pi * fc / SR
        alpha = np.sin(w0) / (2 * q)
        c = np.cos(w0)
        if kind == "shelf":
            b = [a_ * ((a_ + 1) + (a_ - 1) * c + 2 * np.sqrt(a_) * alpha), -2 * a_ * ((a_ - 1) + (a_ + 1) * c),
                 a_ * ((a_ + 1) + (a_ - 1) * c - 2 * np.sqrt(a_) * alpha)]
            a = [(a_ + 1) - (a_ - 1) * c + 2 * np.sqrt(a_) * alpha, 2 * ((a_ - 1) - (a_ + 1) * c),
                 (a_ + 1) - (a_ - 1) * c - 2 * np.sqrt(a_) * alpha]
        else:
            b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
            a = [1 + alpha, -2 * c, 1 - alpha]
        return np.array(b) / a[0], np.array(a) / a[0]

    b, a = biquad("shelf", 1681.974450955533, 0.7071752369554193, 3.99984385397)
    x = signal.lfilter(b, a, x, axis=0)
    b, a = biquad("hp", 38.13547087613982, 0.5003270373253953)
    return signal.lfilter(b, a, x, axis=0)


def windowed_levels(x, seconds=0.1):
    """Each 100 ms window's K-weighted level (dB), by where the window starts."""
    power = (k_weight(x) ** 2).sum(axis=1)
    n = int(seconds * SR)
    mean = np.convolve(power, np.ones(n) / n, mode="valid")
    return -0.691 + 10 * np.log10(mean + 1e-15)


def loudest(x):
    levels = windowed_levels(x)
    return levels.max(), int(levels.argmax())


def sos(order, cutoff, kind):
    return signal.butter(order, cutoff, kind, fs=SR, output="sos")


def ramp(n, start, hold, ease, value):
    """1 until start, `value` from start + hold, easing between over `ease` seconds (a raised cosine)."""
    t = (np.arange(n) - start) / SR
    k = np.clip((t - hold) / ease, 0.0, 1.0)
    return 1.0 + (value - 1.0) * (0.5 - 0.5 * np.cos(np.pi * k))


def onset(x):
    mono = x.mean(axis=1)
    return int(np.argmax(np.abs(mono) > 0.2 * np.abs(mono).max()))


def surroundings(v, rng):
    """One ear's echoes: sparse early, denser later, decaying to -60 dB over echo_t60 and duller with distance."""
    n = int(v.echo_end * SR)
    times, t = [], v.echo_start
    while True:
        t += rng.exponential(1 / (30 + 500 * (t / v.echo_end) ** 1.5))
        if t >= v.echo_end:
            break
        times.append(t)
    times = np.array(times)
    amps = rng.uniform(0.25, 1.0, len(times)) * rng.choice([-1.0, 1.0], len(times)) * 10 ** (-3 * times / v.echo_t60)
    ir = np.zeros(n)
    for i, (start, cutoff) in enumerate(v.echo_dulling):
        end = v.echo_dulling[i + 1][0] if i + 1 < len(v.echo_dulling) else v.echo_end
        pick = (times >= start) & (times < end)
        part = np.zeros(n)
        np.add.at(part, (times[pick] * SR).astype(int), amps[pick])
        ir += signal.sosfilt(sos(2, cutoff, "lowpass"), part)
    # Leaves, rough walls and uneven ground don't mirror the blast: each echo is smeared over a few ms.
    m = int(0.003 * SR)
    smear = rng.standard_normal(m) * np.exp(-np.arange(m) / (0.0008 * SR))
    return signal.fftconvolve(ir, smear / np.sqrt((smear ** 2).sum()))[:n]


def limit(x, ceiling=CEILING):
    """A peak limiter: 1 ms lookahead, 50 ms release."""
    a = int(0.001 * SR)
    need = np.minimum(1.0, ceiling / np.maximum(np.abs(x).max(axis=1), 1e-12))
    target = minimum_filter1d(need, 2 * a + 1)
    coef = np.exp(-1 / (0.05 * SR))
    gain = np.empty_like(target)
    level = 1.0
    for i, v in enumerate(target):
        level = v if v < level else v + (level - v) * coef
        gain[i] = level
    gain = np.convolve(np.pad(gain, (a // 2, a - 1 - a // 2), mode="edge"), np.ones(a) / a, mode="valid")
    return np.clip(x * gain[:, None], -ceiling, ceiling)


def soft_clip(x, ceiling=CEILING):
    """Linear up to CLIP_KNEE of the ceiling, then bending smoothly towards it; run at 4x so it doesn't alias."""
    up = signal.resample_poly(x, 4, 1, axis=0)
    knee = CLIP_KNEE * ceiling
    room = ceiling - knee
    over = np.abs(up) > knee
    up[over] = np.sign(up[over]) * (knee + room * np.tanh((np.abs(up[over]) - knee) / room))
    return signal.resample_poly(up, 1, 4, axis=0)


def master(x):
    return limit(soft_clip(x))


def voice(v, recording, seed):
    """One take of the voiced shot, from a recording (stereo, SR): the shot and its echoes, apart."""
    rng = np.random.default_rng(seed)
    x = signal.resample_poly(recording, 100, round(100 * v.pitch), axis=0)
    n = len(x)
    at = onset(x)

    # 2. Low end.
    # Causal, as a microphone's roll-off is: run both ways, it rang out ahead of the blast, back to the file's start.
    x = signal.sosfilt(sos(4, v.high_pass, "highpass"), x, axis=0)
    low = signal.sosfiltfilt(sos(2, v.low_split, "lowpass"), x, axis=0)
    x = x + (ramp(n, at, v.low_hold, v.low_ease, 10 ** (v.low_cut_db / 20)) - 1)[:, None] * low
    if v.rip_tail_db:
        x = x * ramp(n, at, v.rip_tail_hold, v.rip_tail_ease, 10 ** (v.rip_tail_db / 20))[:, None]

    # 3. The blast: its presence up for the first presence_hold (from 2 ms before the onset).
    band = signal.sosfiltfilt(sos(2, v.presence, "bandpass"), x, axis=0)
    boost = 10 ** (v.presence_db / 20)
    lift = np.where(np.arange(n) < at - int(0.002 * SR), 1.0,
                    ramp(n, at, v.presence_hold, v.presence_ease, 1 / boost) * boost)
    x = x + (lift - 1)[:, None] * band

    # 4. The ground.
    d = int(v.ground_delay * SR)
    ground = signal.sosfilt(sos(1, v.ground_dull, "lowpass"), x, axis=0)
    x[d:] += v.ground_gain * ground[:-d]

    # 5. Surroundings: the echoes of the blast (its first 60 ms, without the designed sub).
    blast = x.mean(axis=1) * ramp(n, at, 0.045, 0.015, 0.0)
    blast = signal.sosfilt(sos(2, 90, "highpass"), blast)
    tail = np.stack([signal.fftconvolve(blast, surroundings(v, rng))[:n] for _ in range(2)], axis=1)
    return x, tail


def finish(v, x, tail, target):
    """The shot at the target's loudest 100 ms through master(), then its echoes tail_at_400ms under it."""
    gain = 0.0
    for _ in range(12):
        y = master(x * 10 ** (gain / 20))
        miss = target - loudest(y)[0]
        if abs(miss) < 0.02:
            break
        gain += miss
    level, top = loudest(y)
    tail_level = windowed_levels(tail)[top + int(0.4 * SR)]
    y = master(y + tail * 10 ** ((v.tail_at_400ms - (tail_level - level)) / 20))
    # The presence band rings a little ahead of the onset, back to the first sample: fade it in over 0.5 ms.
    fade = int(0.0005 * SR)
    y[:fade] *= np.linspace(0.0, 1.0, fade)[:, None]
    fade = int(0.05 * SR)
    y[-fade:] *= np.linspace(1.0, 0.0, fade)[:, None]
    return y


def describe(name, x):
    level, top = loudest(x)
    levels = windowed_levels(x)
    after = " ".join(f"{levels[min(len(levels) - 1, top + int(s * SR))] - level:6.1f}" for s in (0.2, 0.4, 0.7, 1.0))
    head = x[:int(0.15 * SR)].mean(axis=1)
    f, p = signal.welch(head, SR, nperseg=2048)
    edges = [20, 60, 120, 300, 800, 2000, 5000, 10000, 20000]
    bands = [10 * np.log10(p[(f >= lo) & (f < hi)].sum() + 1e-20) for lo, hi in zip(edges, edges[1:])]
    print(f"{name}: loudest 100 ms {level:5.1f} dB, then +0.2/0.4/0.7/1.0 s {after} dB; peak "
          f"{20 * np.log10(np.abs(x).max()):5.1f} dBFS; first 150 ms by band "
          + " ".join(f"{lo}:{b - max(bands):.0f}" for lo, b in zip(edges, bands)))


def decode(files, gain_db):
    """Each recording as float stereo at SR, turned down gain_db and not limited."""
    from ks74u_assets import ffmpeg
    recordings = []
    with tempfile.TemporaryDirectory() as temp:
        for file in files:
            wav = os.path.join(temp, "raw.wav")
            ffmpeg(["-i", str(file), "-af", f"volume={gain_db}dB", "-ar", str(SR), "-ac", "2", "-c:a", "pcm_f32le",
                    wav])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", wavfile.WavFileWarning)
                recordings.append(wavfile.read(wav)[1].astype(np.float64))
    return recordings


def takes(v, raw, levelled):
    return [finish(v, *voice(v, raw[which], seed), loudest(levelled[which])[0]) for which, seed in v.takes]


def build(v, out, ripped):
    """Writes the takes into `out` (a Path) and returns their WAV paths. ripped() gives the recordings as decode()
    does, and as the gun's assets script levels them (limited to -1 dBFS), whose loudness the takes match."""
    paths = []
    for index, x in enumerate(takes(v, *ripped()), start=1):
        path = out / f"{v.name}_{index:02d}.wav"
        write_wav(str(path), x)
        describe(path.name, x)
        paths.append(path)
    return paths


def repitch(x, ratio):
    return signal.resample_poly(x, 1000, round(1000 * ratio), axis=0)


def burst(shots, pitches, rng, rounds, rpm):
    step = int(60 / rpm * SR)
    picks = [repitch(shots[rng.integers(len(shots))], rng.uniform(*pitches)) for _ in range(rounds)]
    out = np.zeros((step * (rounds - 1) + max(len(p) for p in picks), 2))
    for i, p in enumerate(picks):
        out[i * step:i * step + len(p)] += p
    return out


def bursts(v, shots, pitches, rng):
    """The gun's preview_bursts at its rate, a trigger pull every 0.4 s after the last round."""
    out, at = np.zeros((0, 2)), 0
    for rounds in v.preview_bursts:
        one = burst(shots, pitches, rng, rounds, v.rpm)
        grown = np.zeros((max(len(out), at + len(one)), 2))
        grown[:len(out)] += out
        grown[at:at + len(one)] += one
        out = grown
        at += int((rounds - 1) * 60 / v.rpm * SR) + int(0.4 * SR)
    return out


def main(v, ripped, out_dir, fire_event):
    """The gun script's command line: rewrites its takes and its fire event's list and pitch, or --preview."""
    from ks74u_assets import asset_path
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", help="write a before/after demo WAV here instead of the assets")
    args = parser.parse_args()

    if args.preview:
        raw, recordings = ripped()
        voiced = takes(v, raw, recordings)
        for name, x in [(f"ripped {i}", x) for i, x in enumerate(recordings, start=1)] + \
                [(f"take {i}", x) for i, x in enumerate(voiced, start=1)]:
            describe(name, x)
        rng = np.random.default_rng(1)
        pitches = tuple(float(p) for p in v.event_pitch.split())
        gap = np.zeros((int(0.6 * SR), 2))
        demo = np.concatenate([recordings[0], gap, voiced[0], gap, bursts(v, recordings, v.rip_pitch, rng), gap,
                               bursts(v, voiced, pitches, rng)])
        # Overlapping rounds add up: the same 6 dB down for both, so they compare fairly, or further if that clips.
        write_wav(args.preview, demo * min(0.5, CEILING / np.abs(demo).max()))
        print(f"preview: {args.preview}")
        return

    paths = build(v, Path(out_dir), ripped)
    with open(fire_event, encoding="utf-8") as f:
        event = json.load(f)
    event["Pitch"] = v.event_pitch
    event["Sounds"] = [asset_path(p.with_suffix(".vsnd")) for p in paths]
    with open(fire_event, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(event, indent=2) + "\n")
    print(f"{len(paths)} takes -> {out_dir}")
