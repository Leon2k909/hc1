"""
Thunder, synthesised from how a lightning channel makes its noise, with no samples.

    python Tools/thunder_sounds.py [--preview <wav>] [--out <dir>]

Writes Assets/sounds/weather/thunder_<near|mid|far>_NN.wav (mono) and an event for each set, if the event doesn't exist
yet (an event may be tuned in the editor, so a rerun keeps it). The takes are seeded, so a rerun writes the same WAVs.

- thunder_near: ground strikes 650-1,400 m off (RainView plays it under 2 km, made for 1 km).
- thunder_mid: ground strikes 2.7-4.4 km off (2-6 km, made for 3.5 km).
- thunder_far: three flashes inside the cloud 9-11 km away (5-7.5 km up) and a ground strike 9 km off (past 6 km,
  made for 9 km). A flash in the cloud is always heard from at least 6 km (RainView.HeardFrom), so it's always this set.

RainView plays a take when the sound gets there (338 m/s, the speed at 11 C), positioned towards the flash with no
distance falloff or occlusion of its own: within its set it's scaled by the distance, squeezed like the rest of the
mix. Each WAV starts 40 ms before the first sound to arrive. The events are 3D (UI false) on the default mixer.

--preview writes each take in turn over the heavy rain loop, at its event's level.

How it's made (Few's model of thunder, 1969 and 1995, with Ribner and Roy's 1982 synthesis):
- The channel. A lightning channel is tortuous at every scale: photographs show straight runs whose direction changes
  ~16 degrees rms from one to the next (Hill 1968). Here it's two scales of that walk: runs of ~80 m homing on the
  flash's waypoints, each made of runs of ~4 m (lognormal lengths), turning 16 degrees rms and pulled back towards
  where they're going.
- A ground flash (a cloud-to-ground strike): the channel from the ground to the cloud base (1.4-2.6 km up, leaning up
  to 20 degrees), 5-11 branches off it pointing down and out (the stepped leader's, 60-700 m), and 2-3 channels on
  inside the cloud to 4.5-7 km up and 1.5-5 km across. Then 2-5 return strokes down the same channel, the later ones
  weaker (0.35-0.75), 30-110 ms apart (Uman's figures).
- A flash in the cloud: 2-4 horizontal channels 2-5 km long from a start 5-7.5 km up, with branches, growing at
  ~200 km/s, then 2-5 recoil leaders re-lighting the outer parts over half a second.
- Each piece of channel is heated in microseconds and blows out a cylindrical shock, which relaxes into an N-wave of
  dominant frequency f = 0.63 c / R0, where R0 = sqrt(E/p0) is its relaxation radius (E the energy per metre). The
  return stroke's main channel has R0 3-4.5 m (40-70 Hz), its branches and the channel in the cloud less (a few
  hundred hertz at their thinnest), and a flash in the cloud 1.8-2.8 m. Amplitudes go as R0 and the piece's length
  over its distance. The N-wave lengthens a little as it travels (weak-shock theory), here (r / 1 km)^0.05.
- What's heard is every piece's N-wave arriving when its sound gets there. A straight run seen side-on arrives all at
  once, a sharp clap; one pointing at the listener is smeared over its length's travel time, and its N-wave (which has
  no net pressure) mostly cancels. So thunder's claps, peals and rolls come from the channel's shape and how it's
  turned against the listener, and its length from the channel's spread of distances: a strike 1 km off rolls on for
  15 s or more as the sound comes from the cloud. Each run is drawn exactly as that smear (a box in time of its
  length's travel time, with its whole weight), then convolved with its N-wave.
- The ground: the listener's ears are 1.7 m up, so every arrival has its reflection off the ground a few
  milliseconds later (0.7 of it), from the image of the ear under the ground.
- The air's absorption over each piece's path, by ISO 9613-1 for 11 C and 95% humidity (rain): 1 km takes ~4 dB off at
  1 kHz and ~18 at 4 kHz, so a near clap cracks and far thunder only rumbles.
- Refraction: the air cools with height (6.5 K/km), so sound bends up away from the ground. A ray grazing the listener
  is an arc of radius ~87 km, and below it (z < x^2 / 2R for a piece x away) there's a shadow, which turbulence and
  diffraction fill only with the lows (down exp(-depth / 250 m), to at most 28 dB, and low-passed at 200 Hz). So the
  lowest 500 m of a strike 9 km off isn't heard directly, and thunder is rarely heard past ~25 km.
- The surroundings: echoes off the hills, buildings and the cloud base, as a rumble 11-13 dB under the thunder.

The levels (K-weighted, loudest 50 ms). Close thunder is ~120 dB at 100 m and falls about 6 dB a doubling; it's
~100-105 dB(A) for its loudest moment at 1 km, ~90 at 3.5 km and ~80 at 9 km, against ~63 for a footstep. Squeezed 0.43
times like the rest of the mix (foley_voicing's docstring has why), against the walk on concrete (-36): near -18,
mid -23.5 and far -28 at their sets' distances. The near takes are soft-clipped harder: the ear overloads on a clap.
"""
import argparse
import json
import os
import sys
import wave

import numpy as np
from scipy import fft as sfft
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_sounds as ws  # noqa: E402
from ordnance_sounds import rumble, write_stereo  # noqa: E402
from ui_sounds import loudness  # noqa: E402
from world_sounds import SR  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "Assets")
SOUND_PATH = "sounds/weather"

AIR_C = 11.0                                         # rain-cooled air
HUMIDITY = 95.0
C = 331.3 * np.sqrt(1 + AIR_C / 273.15)              # 338 m/s: RainView.SoundSpeed
LAPSE = 6.5e-3                                       # K/m
RAY_RADIUS = 1 / (0.5 * LAPSE / (273.15 + AIR_C))    # ~87 km
EAR = 1.7
GROUND_REFLECTION = 0.7
SHADOW_SCALE = 250.0
SHADOW_FLOOR = 0.04
SHADOW_CUTOFF = 200.0
LEAD = 0.04

# Each set: its targets, cap on its takes' length, soft clipping, echoes, and its takes (kind, horizontal distance m).
SETS = {
    "thunder_near": {"target": -18.0, "seconds": 16.0, "drive": 1.8, "echo_db": -11.0,
                     "takes": [("ground", 650), ("ground", 1000), ("ground", 1400)]},
    "thunder_mid": {"target": -23.5, "seconds": 19.0, "drive": 1.3, "echo_db": -12.0,
                    "takes": [("ground", 2700), ("ground", 3500), ("ground", 4400)]},
    "thunder_far": {"target": -28.0, "seconds": 24.0, "drive": 1.1, "echo_db": -13.0,
                    "takes": [("cloud", 6800), ("cloud", 8000), ("cloud", 9500), ("ground", 9000)]},
}


# ----------------------------------------------------------------------------------------------------------------------
# The air

def absorption(f):
    """ISO 9613-1's pure-tone absorption, dB per metre, at AIR_C, HUMIDITY and sea-level pressure."""
    t = 273.15 + AIR_C
    t0, t01 = 293.15, 273.16
    psat = 10 ** (-6.8346 * (t01 / t) ** 1.261 + 4.6151)
    h = HUMIDITY * psat
    fro = 24 + 4.04e4 * h * (0.02 + h) / (0.391 + h)
    frn = (t / t0) ** -0.5 * (9 + 280 * h * np.exp(-4.170 * ((t / t0) ** (-1 / 3) - 1)))
    f2 = np.asarray(f, float) ** 2
    return 8.686 * f2 * (1.84e-11 * (t / t0) ** 0.5 + (t / t0) ** -2.5 * (
        0.01275 * np.exp(-2239.1 / t) / (fro + f2 / fro) + 0.1068 * np.exp(-3352.0 / t) / (frn + f2 / frn)))


# ----------------------------------------------------------------------------------------------------------------------
# The N-wave

def nwave_peak():
    """Where an N-wave's spectrum peaks, as f times its length."""
    n = 1 << 16
    x = np.zeros(n * 8)
    x[:n] = 1 - 2 * np.arange(n) / n
    spectrum = np.abs(np.fft.rfft(x))
    return (np.argmax(spectrum[1:]) + 1) / 8          # bin k is k / 8 cycles over the N-wave's length


NWAVE_FT = nwave_peak()
T_BASE, T_RATIO = 0.001, 1.15
D_BASE, D_RATIO = 50.0, 1.12


def nwave_length(r0, r):
    """An N-wave's length (s) for a channel of relaxation radius r0 m heard r m away."""
    return NWAVE_FT / (0.63 * C / r0) * (np.maximum(r, 100.0) / 1000.0) ** 0.05


def nwave(length):
    """An N-wave `length` s long, its two shocks rising over 30 us, drawn 8 times over and band-limited down."""
    os_ = 8
    sr = SR * os_
    n = int(round(length * sr)) + 8
    t = np.arange(n) / sr
    x = np.where(t <= length, 1 - 2 * t / length, 0.0)
    rise = 30e-6
    x *= 0.5 - 0.5 * np.cos(np.pi * np.clip(t / rise, 0, 1))
    x[t > length] = 0.0
    return signal.resample_poly(x, 1, os_)


# ----------------------------------------------------------------------------------------------------------------------
# The channel

def unit_vec(v):
    return v / np.linalg.norm(v)


def perpendicular(rng, d):
    r = rng.standard_normal(3)
    r -= r.dot(d) * d
    return r / np.linalg.norm(r)


def walk(rng, start, goal, step, turn_deg, pull):
    """Points from `start` to `goal`: straight runs of lognormal length (median `step`), each turned a normal angle of
    `turn_deg` rms from the last and pulled `pull` of the way back towards the goal."""
    p = np.array(start, float)
    goal = np.array(goal, float)
    pts = [p.copy()]
    d = unit_vec(goal - p)
    turn = np.radians(turn_deg)
    while True:
        to_goal = goal - p
        dist = np.linalg.norm(to_goal)
        if dist < step:
            pts.append(goal.copy())
            break
        a = rng.normal(0, turn)
        d = d * np.cos(a) + perpendicular(rng, d) * np.sin(a)
        d = unit_vec(d + pull * (to_goal / dist - d))
        length = min(step * np.exp(rng.normal(0, 0.6)), dist)
        p = p + d * length
        pts.append(p.copy())
    return np.array(pts)


def channel(rng, start, goal):
    """A channel at two scales: ~80 m runs homing on the goal, each walked in ~4 m runs."""
    macro = walk(rng, start, goal, 80.0, 16.0, 0.12)
    pts = [macro[:1]]
    for a, b in zip(macro[:-1], macro[1:]):
        pts.append(walk(rng, a, b, 4.0, 16.0, 0.3)[1:])
    return np.concatenate(pts)


class Flash:
    """A flash's pieces of channel, each a run of points with its relaxation radius at the start and end, a gain, and
    when its sound left (each point's own time, from a stroke's or a leader's start)."""

    def __init__(self):
        self.pieces = []

    def add(self, points, r0_start, r0_end, gain=1.0, start=0.0, speed=None):
        along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])
        share = along / max(along[-1], 1e-6)
        r0 = r0_start + (r0_end - r0_start) * share
        when = start + (along / speed if speed else np.zeros_like(along))
        self.pieces.append((points, r0, gain, when))


def ground_flash(rng, distance):
    flash = Flash()
    base = np.array([distance, 0.0, 0.0])
    cloud_base = rng.uniform(1400, 2600)
    lean = rng.uniform(0, 0.35)
    heading = rng.uniform(0, 2 * np.pi)
    top = base + np.array([lean * cloud_base * np.cos(heading), lean * cloud_base * np.sin(heading), cloud_base])
    main = channel(rng, base, top)
    r0 = rng.uniform(3.0, 4.5)

    inside = []
    for _ in range(rng.integers(2, 4)):
        a = rng.uniform(0, 2 * np.pi)
        reach = rng.uniform(1500, 5000)
        goal = top + np.array([reach * np.cos(a), reach * np.sin(a), rng.uniform(4500, 7000) - top[2]])
        inside.append(channel(rng, top, goal))

    branches = []
    for _ in range(rng.integers(5, 12)):
        p = main[rng.integers(int(len(main) * 0.25), int(len(main) * 0.95))]
        a = rng.uniform(0, 2 * np.pi)
        length = min(60 + rng.exponential(250), p[2] - 20, 700)
        if length < 40:
            continue
        goal = p + unit_vec(np.array([np.cos(a), np.sin(a), -rng.uniform(0.4, 1.4)])) * length
        goal[2] = max(goal[2], 15.0)
        branches.append(channel(rng, p, goal))

    # The first return stroke lights the whole of it: the main channel, its branches and the channel in the cloud.
    flash.add(main, r0, r0)
    for piece in inside:
        flash.add(piece, 0.6 * r0, 0.35 * r0)
    for piece in branches:
        flash.add(piece, 0.55 * r0, 0.25 * r0)

    # The later strokes go down the main channel, weaker, each from part of the cloud's channel.
    at = 0.0
    for _ in range(rng.integers(1, 5)):
        at += np.exp(rng.normal(np.log(0.055), 0.4))
        g = rng.uniform(0.35, 0.75)
        flash.add(main, r0 * np.sqrt(g), r0 * np.sqrt(g), g, at)
        piece = inside[rng.integers(len(inside))]
        flash.add(piece, 0.5 * r0 * np.sqrt(g), 0.3 * r0 * np.sqrt(g), g, at)
    return flash


def cloud_flash(rng, distance):
    flash = Flash()
    origin = np.array([distance, 0.0, rng.uniform(5000, 7500)])
    r0 = rng.uniform(1.8, 2.8)
    count = int(rng.integers(2, 5))
    first = rng.uniform(0, 2 * np.pi)
    channels = []
    for k in range(count):
        a = first + 2 * np.pi * k / count + rng.normal(0, 0.4)
        reach = rng.uniform(2000, 5000)
        goal = origin + np.array([reach * np.cos(a), reach * np.sin(a), rng.uniform(-900, 700)])
        ch = channel(rng, origin, goal)
        channels.append(ch)
        flash.add(ch, r0, 0.6 * r0, speed=2e5)
        for _ in range(rng.integers(1, 4)):
            i = rng.integers(len(ch) // 5, len(ch))
            b = a + rng.normal(0, 0.9)
            length = rng.uniform(300, 1200)
            goal = ch[i] + np.array([length * np.cos(b), length * np.sin(b), rng.uniform(-300, 300)])
            along = np.sum(np.linalg.norm(np.diff(ch[: i + 1], axis=0), axis=1))
            flash.add(channel(rng, ch[i], goal), 0.6 * r0, 0.35 * r0, start=along / 2e5, speed=2e5)

    # Recoil leaders: the outer part of a channel lit again, fast, later in the flash.
    for _ in range(rng.integers(2, 6)):
        ch = channels[rng.integers(len(channels))]
        cut = rng.integers(int(len(ch) * 0.3), int(len(ch) * 0.7))
        g = rng.uniform(0.3, 0.6)
        flash.add(ch[cut:][::-1], 0.8 * r0 * np.sqrt(g), 0.7 * r0 * np.sqrt(g), g, rng.uniform(0.08, 0.5), speed=3e6)
    return flash


# ----------------------------------------------------------------------------------------------------------------------
# What's heard

def runs(flash):
    """Every straight run, as arrays: arrival start and end (s) at the ear and at its image under the ground, weight
    (R0 times length over distance, times the shadow's loss), N-wave length, distance and whether it's in shadow."""
    ear = np.array([0.0, 0.0, EAR])
    image = np.array([0.0, 0.0, -EAR])
    out = []
    for points, r0, gain, when in flash.pieces:
        a, b = points[:-1], points[1:]
        mid = 0.5 * (a + b)
        length = np.linalg.norm(b - a, axis=1)
        keep = length > 1e-3
        a, b, mid, length = a[keep], b[keep], mid[keep], length[keep]
        r0m = 0.5 * (r0[:-1] + r0[1:])[keep]
        t_a, t_b = when[:-1][keep], when[1:][keep]
        r_mid = np.linalg.norm(mid - ear, axis=1)

        x = np.hypot(mid[:, 0], mid[:, 1])
        depth = x ** 2 / (2 * RAY_RADIUS) - mid[:, 2]
        shadow = depth > 0
        loss = np.where(shadow, np.maximum(np.exp(-np.maximum(depth, 0) / SHADOW_SCALE), SHADOW_FLOOR), 1.0)
        weight = gain * r0m * length / r_mid * loss
        lengths = nwave_length(r0m, r_mid)

        for listener, share in ((ear, 1.0), (image, GROUND_REFLECTION)):
            start = t_a + np.linalg.norm(a - listener, axis=1) / C
            end = t_b + np.linalg.norm(b - listener, axis=1) / C
            out.append((np.minimum(start, end), np.maximum(start, end), weight * share, lengths, r_mid, shadow))
    return [np.concatenate(column) for column in zip(*out)]


def deposit(n, t1, t2, area):
    """Boxes from t1 to t2 (samples) with these areas, integrated over each sample."""
    width = np.maximum(t2 - t1, 1e-3)
    t2 = t1 + width
    h = area / width
    k1 = np.floor(t1).astype(int)
    k2 = np.floor(t2).astype(int)
    f1, f2 = t1 - k1, t2 - k2
    d = np.zeros(n + 2)
    np.add.at(d, k1, h * (1 - f1))
    np.add.at(d, k1 + 1, h * f1)
    np.add.at(d, k2, -h * (1 - f2))
    np.add.at(d, k2 + 1, -h * f2)
    return np.cumsum(d)[:n]


def render(flash, seconds):
    """The flash heard at the ear: the runs grouped by N-wave length, distance and shadow, each group drawn as boxes,
    convolved with its N-wave and filtered by its path's air, and summed."""
    start, end, weight, lengths, distance, shadow = runs(flash)
    first = start.min()
    start = (start - first + LEAD) * SR
    end = (end - first + LEAD) * SR
    total = int(seconds * SR)
    out = np.zeros(total + SR)
    keep = start < total
    start, end, weight, lengths, distance, shadow = (v[keep] for v in (start, end, weight, lengths, distance, shadow))

    t_bin = np.round(np.log(lengths / T_BASE) / np.log(T_RATIO)).astype(int)
    d_bin = np.round(np.log(distance / D_BASE) / np.log(D_RATIO)).astype(int)
    keys = np.stack([t_bin, d_bin, shadow.astype(int)], axis=1)
    groups, inverse = np.unique(keys, axis=0, return_inverse=True)
    inverse = inverse.ravel()
    order = np.argsort(inverse, kind="stable")
    bounds = np.searchsorted(inverse[order], np.arange(len(groups) + 1))
    pad = int(0.25 * SR)
    for g, (tb, db, sh) in enumerate(groups):
        idx = order[bounds[g]:bounds[g + 1]]
        wave_ = nwave(T_BASE * T_RATIO ** tb)
        lo = int(np.floor(start[idx].min())) - pad
        hi = int(np.ceil(end[idx].max())) + pad + len(wave_)
        n = sfft.next_fast_len(hi - lo)
        train = deposit(n, start[idx] - lo, end[idx] - lo, weight[idx])
        f = np.fft.rfftfreq(n, 1 / SR)
        spectrum = sfft.rfft(train, n, workers=-1) * sfft.rfft(wave_, n, workers=-1)
        spectrum *= 10 ** (-absorption(f) * D_BASE * D_RATIO ** db / 20)
        if sh:
            spectrum /= np.sqrt(1 + (f / SHADOW_CUTOFF) ** 2)
        piece = sfft.irfft(spectrum, n, workers=-1)
        a, b = max(lo, 0), min(lo + n, len(out))
        out[a:b] += piece[a - lo:b - lo]
    return out[:total]


def trim(x, seconds):
    """Cut where it's fallen 50 dB under its loudest 200 ms and fade the last 1.5 s out. A take still sounding at
    `seconds` is cut there and faded over its last 4 s instead, as the far rumble dies away."""
    window = int(0.2 * SR)
    total = np.concatenate([[0.0], np.cumsum(x ** 2)])
    env = np.sqrt((total[window:] - total[:-window]) / window)
    above = np.nonzero(env > env.max() * 10 ** (-50 / 20))[0]
    natural = above[-1] + window + int(0.3 * SR)
    end = min(len(x), int(seconds * SR), natural)
    x = x[:end].copy()
    fade = min(int((1.5 if end == natural else 4.0) * SR), end // 3)
    x[-fade:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, fade))
    return x


def take(seed, kind, distance, spec):
    rng = np.random.default_rng(seed)
    flash = ground_flash(rng, distance) if kind == "ground" else cloud_flash(rng, distance)
    x = render(flash, spec["seconds"] + 4)
    echo = rumble(rng, x, 4.0, 1.4, 0.35, build=0.15, split=500.0)
    x = x + 10 ** (spec["echo_db"] / 20) * np.sqrt(np.mean(x ** 2) / np.mean(echo ** 2)) * echo
    return ws.finish(trim(x, spec["seconds"]), spec["drive"])


def build():
    out = {}
    for s, (name, spec) in enumerate(SETS.items()):
        takes = [take(60000 + 100 * s + i, kind, distance, spec) for i, (kind, distance) in enumerate(spec["takes"])]
        takes, volume = ws.level(takes, spec["target"])
        out[name] = ([f"{name}_{i + 1:02d}" for i in range(len(takes))], takes, volume)
    return out


def write_event(folder, name, takes, volume):
    """A 3D event on the default mixer with no falloff, occlusion or air absorption of its own (the takes have the
    air's; RainView places it and scales it)."""
    path = os.path.join(folder, name + ".sound")
    if os.path.exists(path):
        return False
    low = volume * 10 ** (-1.5 / 20)
    event = {
        "UI": False,
        "Volume": f"{low:.4f} {volume:.4f}",
        "Pitch": "0.96 1.04",
        "Decibels": 70,
        "SelectionMode": "Random",
        "Sounds": [f"{SOUND_PATH}/{t}.vsnd" for t in takes],
        "Occlusion": False,
        "AirAbsorption": False,
        "Transmission": False,
        "OcclusionRadius": 32,
        "DistanceAttenuation": False,
        "Distance": 20000,
        "__references": [],
        "__version": 1,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(event, f, indent=2)
        f.write("\n")
    return True


def read_rain():
    """The heavy rain loop and its event's volume, for the preview."""
    folder = os.path.join(ASSETS, *SOUND_PATH.split("/"))
    try:
        with wave.open(os.path.join(folder, "rain_heavy.wav")) as w:
            pcm = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, w.getnchannels())
        with open(os.path.join(folder, "rain_heavy.sound"), encoding="utf-8-sig") as f:
            volume = float(str(json.load(f)["Volume"]).split()[-1])
        return pcm / 32767.0, volume
    except (OSError, KeyError, ValueError):
        return None, 0.0


def preview(sets, path):
    clips = [(takes[i] * volume) for _, (names, takes, volume) in sets.items() for i in range(len(takes))]
    n = sum(len(c) for c in clips) + SR * (2 * len(clips) + 2)
    out = np.zeros((n, 2))
    rain, rain_volume = read_rain()
    if rain is not None:
        idx = np.arange(n) % len(rain)
        out += rain[idx] * rain_volume
    at = SR
    for clip in clips:
        out[at:at + len(clip)] += clip[:, None]
        at += len(clip) + 2 * SR
    write_stereo(path, out / max(1.0, np.abs(out).max()))
    print(f"preview: {path} ({n / SR:.0f} s)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", help="write every take in turn over the heavy rain")
    parser.add_argument("--out", help="write under this folder instead of Assets (to try changes)")
    args = parser.parse_args()

    sets = build()
    folder = os.path.join(args.out or ASSETS, *SOUND_PATH.split("/"))
    os.makedirs(folder, exist_ok=True)
    for name, (names, takes, volume) in sets.items():
        for take_name, x in zip(names, takes):
            ws.write_wav(os.path.join(folder, take_name + ".wav"), x)
            spectrum = np.abs(np.fft.rfft(x)) ** 2
            f = np.fft.rfftfreq(len(x), 1 / SR)
            smooth = np.convolve(spectrum, np.ones(64) / 64, "same")
            first = x[: SR] if len(x) > SR else x
            print(f"{take_name}: {len(x) / SR:.1f} s, loudness {loudness(x * volume):.1f} dB "
                  f"(first second {loudness(first * volume):.1f}), centroid {np.sum(spectrum * f) / np.sum(spectrum):.0f} Hz, "
                  f"peak {f[np.argmax(smooth)]:.0f} Hz")
        written = write_event(folder, name, names, volume)
        print(f"{name}: volume {volume:.4f} (target {SETS[name]['target']})"
              + ("" if written else f"; {name}.sound exists, left as it is"))
    if args.preview:
        preview(sets, args.preview)


if __name__ == "__main__":
    main()
