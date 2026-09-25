#!/usr/bin/env python3
"""Generate HC1's main menu music: a dark, cinematic military loop in D minor, synthesised from scratch.

Writes Assets/sounds/music/menu_theme.wav (44.1 kHz, 16-bit stereo, 80 s), which sounds/music/main_menu_loop.sound
plays on a loop in the menu scene.

The 32 bars build from a drone-and-pad intro through taiko drums, a pulsing bass and an arpeggio into a horn theme,
then thin out again so the end runs straight back into the intro. The file loops seamlessly: continuous layers (the
drone and the wind) complete whole cycles over the loop, and every tail that runs past the end (note releases,
reverb) is wrapped round onto the start.

Run: python Tools/menu_music.py [--seed N]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy import ndimage, signal
from scipy.io import wavfile

SR = 44100
BPM = 96
BEAT = 60.0 / BPM
BAR = 4 * BEAT
BARS = 32
LOOP = int(round(BARS * BAR * SR))
LOOP_SECONDS = LOOP / SR
TAIL = 6 * SR  # room for releases and reverb past the loop's end, wrapped onto the start
PRE = SR  # pre-roll that settles the filters of the continuous layers
LIMITER_DRIVE = 4.0  # dB pushed into the peak limiter, trading drum transients for overall loudness
OUT = Path(__file__).resolve().parent.parent / "Assets" / "sounds" / "music" / "menu_theme.wav"

# Two bars per chord: (pad voicing, bass root) as MIDI notes. Dm Bb F C (i VI III VII), then Dm Bb Gm A (i VI iv V).
CHORDS = [
    ((50, 57, 62, 65), 38),
    ((46, 53, 58, 62), 34),
    ((48, 53, 57, 60), 41),
    ((48, 52, 55, 60), 36),
    ((50, 57, 62, 65), 38),
    ((46, 53, 58, 62), 34),
    ((50, 55, 58, 62), 43),
    ((49, 52, 57, 61), 45),
]

# The horn theme over bars 16-31: (MIDI note or None for a rest, beats), two bars per chord.
THEME = [
    (62, 2), (69, 2), (65, 3), (64, 1),
    (62, 3), (65, 1), (70, 2), (69, 2),
    (65, 2), (69, 2), (72, 3), (70, 1),
    (67, 4), (64, 2), (None, 2),
    (62, 2), (69, 2), (74, 3), (72, 1),
    (70, 2), (69, 2), (65, 4),
    (67, 2), (70, 2), (74, 2), (72, 2),
    (73, 4), (69, 4),
]


# --- building blocks -----------------------------------------------------------------------------------------------

def hz(note: float) -> float:
    return 440.0 * 2.0 ** ((note - 69) / 12.0)


def looping_hz(freq: float) -> float:
    """The nearest frequency that completes a whole number of cycles over the loop."""
    return round(freq * LOOP_SECONDS) / LOOP_SECONDS


def at(bar: float, beat: float = 0.0) -> int:
    """Sample index of a bar (0-based) and beat."""
    return int(round((bar * 4 + beat) * BEAT * SR))


def samples(seconds: float) -> int:
    return int(round(seconds * SR))


def _polyblep(phase: np.ndarray, step: np.ndarray) -> np.ndarray:
    """Band-limiting correction for a sawtooth's reset."""
    out = np.zeros_like(phase)
    low = phase < step
    x = phase[low] / step[low]
    out[low] = x + x - x * x - 1.0
    high = phase > 1.0 - step
    x = (phase[high] - 1.0) / step[high]
    out[high] = x * x + x + x + 1.0
    return out


def saw(freq, n: int, phase: float = 0.0) -> np.ndarray:
    """Band-limited sawtooth of n samples; freq may change per sample."""
    step = np.broadcast_to(np.asarray(freq, float) / SR, (n,)).copy()
    ph = (phase + np.cumsum(step)) % 1.0
    return 2.0 * ph - 1.0 - _polyblep(ph, step)


def saw_at(freq: float, t: np.ndarray, phase: float = 0.0) -> np.ndarray:
    """Band-limited sawtooth at fixed freq, sampled at times t (for layers that must repeat exactly)."""
    ph = (phase + freq * t) % 1.0
    return 2.0 * ph - 1.0 - _polyblep(ph, np.full_like(ph, freq / SR))


def _lowpass_coefficients(cutoff: float, q: float):
    w = 2.0 * np.pi * min(max(cutoff, 20.0), 0.45 * SR) / SR
    alpha = np.sin(w) / (2.0 * q)
    cos = np.cos(w)
    b = np.array([(1.0 - cos) / 2.0, 1.0 - cos, (1.0 - cos) / 2.0])
    a = np.array([1.0 + alpha, -2.0 * cos, 1.0 - alpha])
    return b / a[0], a / a[0]


def lowpass(x: np.ndarray, cutoff, q: float = 0.707, block: int = 128) -> np.ndarray:
    """Resonant lowpass whose cutoff (Hz, scalar or per sample) is updated every block."""
    cutoff = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    y = np.empty_like(x)
    state = np.zeros(2)
    for start in range(0, len(x), block):
        b, a = _lowpass_coefficients(float(cutoff[start]), q)
        y[start:start + block], state = signal.lfilter(b, a, x[start:start + block], zi=state)
    return y


def butter(kind: str, freq, order: int = 2):
    return signal.butter(order, freq, kind, fs=SR, output="sos")


def envelope(length: float, attack: float, release: float, decay: float = 0.0, sustain: float = 1.0) -> np.ndarray:
    """Attack, optional exponential decay to sustain, hold for length seconds, then release."""
    held, total = samples(length), samples(length + release)
    t = np.arange(total) / SR
    env = np.minimum(t / max(attack, 1e-4), 1.0)
    if decay > 0.0:
        after = t >= attack
        env[after] = sustain + (1.0 - sustain) * np.exp(-(t[after] - attack) / decay)
    level = env[max(held - 1, 0)]
    tail = t >= length
    env[tail] = level * np.clip(1.0 - (t[tail] - length) / release, 0.0, 1.0) ** 2
    return env


def pan(mono: np.ndarray, position: float) -> np.ndarray:
    """Constant-power pan, -1 left to 1 right, unity in each channel at the centre."""
    angle = (position + 1.0) * np.pi / 4.0
    return np.stack([mono * np.cos(angle), mono * np.sin(angle)]) * np.sqrt(2.0)


class Mix:
    """Dry and reverb-send buses, with a separate bus the kick drum ducks."""

    def __init__(self):
        shape = (2, LOOP + TAIL)
        self.dry, self.send = np.zeros(shape), np.zeros(shape)
        self.ducked_dry, self.ducked_send = np.zeros(shape), np.zeros(shape)
        self.kicks: list[int] = []

    def add(self, name: str, sound: np.ndarray, start: int, gain_db: float, send: float = 0.0,
            position: float = 0.0, ducked: bool = False) -> None:
        if sound.ndim == 1:
            sound = pan(sound, position)
        end = min(start + sound.shape[1], LOOP + TAIL)
        piece = sound[:, :end - start] * 10.0 ** (gain_db / 20.0)
        dry, wet = (self.ducked_dry, self.ducked_send) if ducked else (self.dry, self.send)
        dry[:, start:end] += piece
        wet[:, start:end] += piece * send

    def duck(self, depth: float = 0.45, recovery: float = 0.22) -> np.ndarray:
        """Gain curve that dips on every kick (sidechain pumping)."""
        curve = np.zeros(LOOP + TAIL)
        length = samples(recovery * 5)
        shape = depth * np.exp(-np.arange(length) / SR / recovery)
        for kick in self.kicks:
            end = min(kick + length, len(curve))
            curve[kick:end] = np.maximum(curve[kick:end], shape[:end - kick])
        return 1.0 - curve


# --- instruments ---------------------------------------------------------------------------------------------------

def drone(rng) -> np.ndarray:
    """D pedal: sub sine plus a filtered, detuned saw pair and fifth, swelling slowly. Repeats exactly over the loop."""
    t = np.arange(-PRE, LOOP) / SR
    sub = np.sin(2 * np.pi * looping_hz(hz(26)) * t)
    body = (saw_at(looping_hz(hz(38) * 2 ** (-6 / 1200)), t, rng.random())
            + saw_at(looping_hz(hz(38) * 2 ** (6 / 1200)), t, rng.random())
            + 0.5 * saw_at(looping_hz(hz(45)), t, rng.random()))
    sweep = 0.5 + 0.5 * np.sin(2 * np.pi * t / (8 * BAR))
    body = lowpass(body, 130 + 170 * sweep, q=1.1)
    swell = 0.78 + 0.22 * np.sin(2 * np.pi * t / (4 * BAR) + 1.0)
    return ((0.8 * sub + 0.3 * body) * swell)[PRE:]


def wind(rng) -> np.ndarray:
    """Stereo band of wind noise, drifting in pitch and level. Repeats exactly over the loop."""
    t = np.arange(-PRE, LOOP) / SR
    channels = []
    for side in range(2):
        noise = rng.standard_normal(LOOP)[np.arange(-PRE, LOOP) % LOOP]
        drift = 0.5 + 0.5 * np.sin(2 * np.pi * t / (8 * BAR) + 1.7 * side)
        band = signal.sosfilt(butter("high", 160), lowpass(noise, 320 + 900 * drift, q=2.2, block=256))
        level = 0.65 + 0.35 * np.sin(2 * np.pi * t / (4 * BAR) + side)
        channels.append((band * level)[PRE:])
    return np.stack(channels) * 0.5


def pad_cutoff(seconds: np.ndarray) -> np.ndarray:
    """The pad's filter over the loop: dark intro, opening for the theme, closing again to meet the intro."""
    bars = seconds / BAR
    points = ([0, 8, 16, 17, 28, 32], [600, 1000, 1500, 2300, 2000, 600])
    lfo = 1.0 + 0.15 * np.sin(2 * np.pi * bars / 8)
    return np.interp(bars, *points) * lfo


def pad_chord(notes, start: int, length: float, rng) -> np.ndarray:
    """Detuned saw strings, three voices per note spread across the stereo field."""
    release = 2.5
    n = samples(length + release)
    out = np.zeros((2, n))
    for note in notes:
        for cents, position in ((-8, -0.7), (0, 0.0), (8, 0.7)):
            out += pan(saw(hz(note) * 2 ** (cents / 1200), n, rng.random()), position)
    cutoff = pad_cutoff((start + np.arange(n)) / SR)
    out = np.stack([lowpass(channel, cutoff, q=0.9) for channel in out])
    return out * envelope(length, 1.4, release) / (3 * len(notes))


def bass_note(note: int, length: float, bright: float) -> np.ndarray:
    """Saw plus sub-octave sine with a snappy filter envelope."""
    release = 0.05
    n = samples(length + release)
    t = np.arange(n) / SR
    x = 0.7 * saw(hz(note), n) + 0.6 * np.sin(2 * np.pi * hz(note) / 2 * t)
    y = lowpass(x, 110 + bright * 1300 * np.exp(-t / 0.09), q=1.4, block=64)
    return np.tanh(1.6 * y * envelope(length, 0.004, release, decay=0.15, sustain=0.55))


def pluck(note: int, rng) -> np.ndarray:
    n = samples(0.45)
    t = np.arange(n) / SR
    y = lowpass(saw(hz(note), n, rng.random()), 260 + 2600 * np.exp(-t / 0.06), q=1.2, block=64)
    return y * np.exp(-t / 0.2) * np.minimum(t / 0.002, 1.0)


def horn(note: int, length: float, rng) -> np.ndarray:
    """Brass-like lead: detuned saws with a swelling filter and delayed vibrato."""
    release = 0.5
    n = samples(length + release)
    t = np.arange(n) / SR
    vibrato = 1.0 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.35) / 0.4, 0.0, 1.0)
    f = hz(note) * vibrato
    x = (saw(f * 2 ** (-4 / 1200), n, rng.random()) + saw(f * 2 ** (4 / 1200), n, rng.random())
         + 0.5 * saw(f / 2, n, rng.random()))
    y = lowpass(x, 480 + 1700 * (1.0 - np.exp(-t / 0.18)), q=0.8, block=64)
    return y * envelope(length, 0.09, release, decay=0.6, sustain=0.8) / 2.5


def braam(rng) -> np.ndarray:
    """Low brass cluster that swells open and closes (the hit that starts the theme)."""
    length, release = 3.0, 1.5
    n = samples(length + release)
    t = np.arange(n) / SR
    cutoff = 170 + 1400 * np.exp(-((t - 0.35) / 0.45) ** 2) + 240 * np.exp(-t / 2.0)
    channels = []
    for _ in range(2):
        x = sum(saw(hz(note) * 2 ** (cents / 1200), n, rng.random())
                for note in (38, 45, 50, 53) for cents in (-12, -4, 4, 12)) / 16
        channels.append(lowpass(x, cutoff, q=1.2))
    return np.tanh(2.2 * np.stack(channels) * envelope(length, 0.04, release, decay=1.4, sustain=0.35))


def taiko(rng, pitch: float = 1.0, decay: float = 0.45) -> np.ndarray:
    n = samples(1.8)
    t = np.arange(n) / SR
    f = (46 + 110 * np.exp(-t / 0.035)) * pitch
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / decay)
    skin = signal.sosfilt(butter("band", [150, 900]), rng.standard_normal(n)) * np.exp(-t / 0.06) * 0.6
    # Stick click: band-limited and faded in over half a millisecond, so it stays a knock rather than a hiss spike.
    click = (signal.sosfilt(butter("band", [1500, 5000]), rng.standard_normal(n))
             * np.minimum(t / 0.0005, 1.0) * np.exp(-t / 0.004) * 0.3)
    return np.tanh(1.8 * (body + skin + click)) / np.tanh(1.8)


def snare(rng) -> np.ndarray:
    """Military field snare: rattly noise over two drum-head tones."""
    n = samples(0.5)
    t = np.arange(n) / SR
    noise = signal.sosfilt(butter("band", [1200, 7000]), rng.standard_normal(n)) * np.exp(-t / 0.12)
    tone = 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) + 0.3 * np.sin(2 * np.pi * 330 * t) * np.exp(-t / 0.03)
    return 1.2 * noise + tone


def tick(rng) -> np.ndarray:
    n = samples(0.08)
    t = np.arange(n) / SR
    return signal.sosfilt(butter("high", 7000, 4), rng.standard_normal(n)) * np.exp(-t / 0.018)


def riser(bars: float, rng) -> np.ndarray:
    """Noise swell that opens up into the next section."""
    n = samples(bars * BAR)
    ramp = np.linspace(0.0, 1.0, n)
    channels = [lowpass(signal.sosfilt(butter("high", 700), rng.standard_normal(n)), 900 + 8000 * ramp ** 2, q=1.5)
                for _ in range(2)]
    return np.stack(channels) * ramp ** 2.5


# --- arrangement ---------------------------------------------------------------------------------------------------

def arrange(mix: Mix, rng) -> None:
    sixteenth = BEAT / 4

    # Continuous layers.
    mix.add("drone", drone(rng), 0, -8, send=0.1)
    mix.add("wind", wind(rng), 0, -18, send=0.25)

    # Pad: every chord, the filter following pad_cutoff.
    for index in range(BARS // 2):
        notes, _ = CHORDS[index % len(CHORDS)]
        mix.add("pad", pad_chord(notes, at(2 * index), 2 * BAR, rng), at(2 * index), -6, send=0.35, ducked=True)

    # Drums. Taiko pattern per bar (beats) and the bars each one covers.
    def hit(name, sound, bar, beat, gain_db, send, position=0.0, kick=False):
        start = at(bar, beat)
        mix.add(name, sound, start, gain_db, send=send, position=position)
        if kick:
            mix.kicks.append(start)

    for bar in range(8, 30):
        pattern = [0.0, 2.5] if bar < 16 or bar >= 28 else [0.0, 1.5, 2.5]
        for beat in pattern:
            hit("taiko", taiko(rng), bar, beat, 0 if beat == 0 else -3, 0.15, kick=True)
        if bar % 2 == 1:
            hit("taiko", taiko(rng, pitch=1.6, decay=0.25), bar, 3.5, -7, 0.2, position=0.3)
    hit("taiko", taiko(rng, decay=0.8), 30, 0.0, -4, 0.3, kick=True)

    for bar in range(16, 28):
        for beat in (1.0, 3.0):
            hit("snare", snare(rng), bar, beat, -15, 0.3, position=-0.1)
        hit("snare", snare(rng), bar, 3.75, -25, 0.3, position=-0.1)  # ghost note
    for bar, loudness in ((15, 0.0), (23, -6.0)):  # rolls into the theme's two halves
        for step in range(16):
            level = loudness - 28 + 12 * step / 15
            hit("snare", snare(rng), bar, step / 4, level, 0.35, position=-0.1)
            if step >= 8:
                hit("snare", snare(rng), bar, step / 4 + 0.125, level - 2, 0.35, position=-0.1)

    for bar in range(8, 30):
        fade = min(1.0, bar - 7.0) if bar < 28 else (30 - bar) / 3
        for step in range(16):
            accent = (1.0, 0.35, 0.6, 0.35)[step % 4]
            hit("ticks", tick(rng) * accent * fade, bar, step / 4, -17, 0.2, position=0.35 if step % 2 else -0.35)

    mix.add("riser", riser(2, rng), at(14), -18, send=0.4)
    mix.add("riser", riser(1, rng), at(23), -22, send=0.4)
    for bar in (16, 24):
        mix.add("braam", braam(rng), at(bar), -3, send=0.3)
        hit("taiko", taiko(rng, pitch=0.7, decay=1.2), bar, 0.0, 0, 0.25)

    # Bass: soft quarters in the intro, eighths, a galloping ostinato under the theme, then eighths fading out.
    for bar in range(4, 32):
        _, root = CHORDS[(bar // 2) % len(CHORDS)]
        if bar < 8:
            steps, length, level, bright = range(0, 16, 4), 3.4, -12.0 + (bar - 4) * 1.5, 0.15
        elif bar < 16:
            steps, length, level, bright = range(0, 16, 2), 1.8, -6.0, 0.45
        elif bar < 28:
            steps, length, level, bright = (0, 2, 3, 4, 6, 7, 8, 10, 11, 12, 14, 15), 0.9, -5.0, 0.7
        else:
            steps, length, level, bright = range(0, 16, 2), 1.8, -6.0 - (bar - 27) * 4.0, 0.4 - (bar - 27) * 0.08
        for step in steps:
            accent = 0.0 if step % 4 == 0 else -2.5
            mix.add("bass", bass_note(root, length * sixteenth, bright), at(bar, step / 4), level + accent,
                    send=0.05, ducked=True)

    # Arpeggio: chord tones an octave up in sixteenths, ping-ponging across the stereo field.
    for bar in range(12, 28):
        notes, _ = CHORDS[(bar // 2) % len(CHORDS)]
        fade = min(1.0, (bar - 11) / 4)
        for step in range(16):
            note = notes[(0, 2, 1, 3)[step % 4]] + 12
            accent = 1.0 if step % 4 == 0 else 0.7
            mix.add("arp", pluck(note, rng) * accent * fade, at(bar, step / 4), -18, send=0.5,
                    position=0.45 if step % 2 else -0.45, ducked=True)

    # Horn theme with an octave-down double, easing off over its last two bars into the quiet intro.
    beat = 0.0
    for note, beats in THEME:
        if note is not None:
            start = at(16, beat)
            taper = -5.0 if beat >= 60 else -2.5 if beat >= 56 else 0.0
            mix.add("horn", horn(note, beats * BEAT * 0.95, rng), start, -9 + taper, send=0.45)
            mix.add("horn", horn(note - 12, beats * BEAT * 0.95, rng), start, -17 + taper, send=0.45)
        beat += beats


def reverb(send: np.ndarray, rng, seconds: float = 3.2, predelay: float = 0.025) -> np.ndarray:
    """Hall reverb: convolution with decaying, darkened stereo noise."""
    n = samples(seconds)
    t = np.arange(n) / SR
    ir = rng.standard_normal((2, n)) * np.exp(-6.9 * t / seconds)
    ir = signal.sosfilt(butter("low", 5500), ir, axis=1)
    ir = np.pad(ir, ((0, 0), (samples(predelay), 0)))
    ir /= np.sqrt(np.sum(ir ** 2, axis=1, keepdims=True))
    return np.stack([signal.fftconvolve(send[side], ir[side])[:send.shape[1]] for side in range(2)])


def limit(x: np.ndarray, ceiling_db: float = -1.0, window: float = 0.01) -> np.ndarray:
    """Look-ahead peak limiter holding the loop under the ceiling. Its gain curve wraps round the loop, so the seam
    stays seamless."""
    ceiling = 10 ** (ceiling_db / 20)
    size = samples(window)
    peak = ndimage.maximum_filter1d(np.max(np.abs(x), axis=0), size, mode="wrap")
    gain = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    gain = ndimage.uniform_filter1d(ndimage.minimum_filter1d(gain, size, mode="wrap"), size, mode="wrap")
    return np.clip(x * gain, -ceiling, ceiling)


def render(seed: int) -> tuple[np.ndarray, dict[str, float]]:
    rng = np.random.default_rng(seed)
    mix = Mix()
    arrange(mix, rng)
    duck = mix.duck()
    dry = mix.dry + mix.ducked_dry * duck
    send = mix.send + mix.ducked_send * duck
    out = dry + 0.5 * reverb(send, rng)
    out = signal.sosfilt(butter("high", 28), out, axis=1)
    # Wrap everything that ran past the end onto the start, making the loop seamless.
    out[:, :TAIL] += out[:, LOOP:]
    out = out[:, :LOOP]
    out /= np.max(np.abs(out))
    return limit(out * 10 ** (LIMITER_DRIVE / 20))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=1, help="noise and oscillator phase seed")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = render(args.seed)
    dither = (np.random.default_rng(0).random(out.shape) - np.random.default_rng(1).random(out.shape)) / 32768
    pcm = np.clip(np.round((out + dither) * 32767), -32768, 32767).astype(np.int16)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(args.out, SR, pcm.T)
    rms = 20 * np.log10(np.sqrt(np.mean(out ** 2)))
    peak = 20 * np.log10(np.max(np.abs(out)))
    print(f"wrote {args.out} ({LOOP_SECONDS:.1f} s, {BARS} bars at {BPM} BPM, RMS {rms:.1f} dBFS, peak {peak:.1f} dBFS)")


if __name__ == "__main__":
    main()
