"""
Ordnance sounds modelled on the real thing, in place of upstream's recordings: the HE grenade's and the C4's blasts,
each heard near and far, the M84 flashbang's bang, the smoke grenade's ignition and burn, and the ringing in the ears
after a flashbang. They're synthesised from the physics of each event, so there are no samples, and every figure here
can be re-tuned.

    python Tools/ordnance_sounds.py [--preview <wav>] [--out <dir>]

Writes, with a .sound event for each set if it doesn't exist yet (an event may be tuned in the editor, so it isn't
overwritten; delete one to have it rewritten):
- Assets/sounds/weapons/grenade/frag_blast_{near,far}_<n>.wav: an M67 going off ~15 m and ~150 m away;
- Assets/sounds/weapons/bomb/c4_blast_{near,far}_<n>.wav: a 9 kg demolition charge ~40 m and ~400 m away;
- Assets/sounds/weapons/grenade/flashbang_bang_<n>.wav: an M84 ~4 m away;
- Assets/sounds/weapons/grenade/smoke_ignite_<n>.wav and smoke_burn.wav (an 8 s loop);
- Assets/sounds/player/ear_ringing.wav (stereo, played flat).
BlastSound (Code/Weapons/Grenades/BlastSound.cs) plays a blast's near or far set by the listener's distance, when its
sound gets there. --preview writes every take in a row, and the smoke from ignition to burn-out.

The blasts. An explosive's blast wave is a shock: the pressure jumps in microseconds, falls through ambient over the
positive phase and comes back from a weaker, longer suction (the Friedlander waveform). Its peak and the positive phase's
length follow from the charge and the distance, cube-root scaled (Kinney and Graham's fits for TNT in free air, the
charge doubled near enough for a burst on the ground, which reflects the whole hemisphere back up): an M67 (185 g of
Composition B, ~0.25 kg of TNT) 15 m away is ~4.5 kPa (167 dB) for 3.0 ms, so its energy sits round 150 Hz: a sharp crack
on a short, deep thump. A small second shock follows a few ms later (the products re-expanding). The ground's reflection
merges with the direct wave, as both start at the ground. Then:
- the fireball: Composition B and C4 are short of oxygen, so their hot products burn on as they mix with the air, a
  turbulent roar for tens of ms (an M67) to a quarter of a second (the C4);
- the M67's fragments. It throws some 2,000 steel fragments (the body and its notched coil) at ~1,300 m/s, which slow
  fast. At 15 m about one passes within a metre of you, so a few pass within a few metres: each a small supersonic crack,
  arriving before the blast (they outrun it). Those that miss strike the ground and walls round you (thuds, chips and
  the odd ping), and a few slow, tumbling ones whirr past after the bang;
- debris: the crater's soil and grit, thrown a few metres up, rain down for a second or two (a patter and a hiss). The
  C4's are chunks of concrete and earth thrown tens of metres up, clattering down for 2-3 s;
- the surroundings: the walls and buildings round you send back echoes over the first few hundred ms, low-passed by
  the air and spread out by rough surfaces, and the far ones and the terrain make the long rolling rumble an explosion
  has outdoors (an impulse response of filtered noise, its highs dying sooner). s&box plays sounds dry, so this is the
  only room they get.
- far: the blast is weaker and its front no longer as sharp, the air has taken its highs (a 150 m path takes ~3 dB off
  at 4 kHz, more above), the fragments and debris are out of earshot, and the echoes and the rumble are as loud against
  it as the reverberant field is against a direct sound that keeps falling 6 dB a doubling.

The M84 flashbang: 4.5 g of magnesium and potassium perchlorate flash powder, burnt in a perforated steel body that
stays whole. NIJ measured 178 dB at 6 ft, falling ~9 dB a doubling. Its pressure pulse is a fraction of a millisecond, so
it's a bright, splitting crack rather than a boom, with the jets roaring out of the body's ports for a few ms, the
powder's flash burning out, the body kicked into a clattering bounce, and a room's or a street's reflections.

The smoke grenade (an AN-M8 HC type, white): the starter mix lights with a soft pop, and the hiss rises over a second
or so as the composition takes hold. Then the burn: gas and smoke jetting out of the can's emission holes, a broad
breathy hiss (jet noise peaks near a Strouhal number of 0.2: ~40 m/s through holes ~6 mm across gives ~1.3 kHz), the
burning front's flutter, and spitting and pops from the slag. The loop is periodic over its 8 s, so it loops with no
seam. The smoke's own prefab fades it in and out with the emission.

The ringing (a temporary threshold shift's tinnitus): a high, nearly pure tone near 4 kHz, where noise damages the ear
first, slightly different in each ear and drifting a little, with a breathy hiss right after the blast that dies within a
few seconds. FlashbangEffect sets its level as the hearing recovers.

How loud. A blast's bang is a millisecond pulse far over everything after it. The ear overloads on it (and so does any
microphone), so the bang is soft-clipped (`master`, `BANG_DRIVE`), and the rest goes in after at the level it had
against the bang's loudness: the echoes 10-16 dB under it, the rumble 25 dB under it half a second on (far off, 8-12 dB:
there the echoes come from round the listener, nearly as far off as the blast), and the debris and the fragments'
strikes faint, as they really are against a 167 dB bang.

Levels are K-weighted loudness of the loudest 50 ms (ui_sounds.loudness), against the game's mix: anyone else's rifle
shot plays at -6.3 dB at 4 m, falling 6 dB a doubling beyond that. Real figures are squeezed as the rest of the mix is
(foley_voicing: 0.43 times the real difference), which would put the M67 ~13 dB over a rifle at the same distance (a
far higher peak, a pulse six times as long). A file can't hold that much: even squeezed square, a millisecond bang only
reaches -12.3 dB, so every blast plays at full volume and holds its level inside its reference distance. That's 5.5 dB
over a rifle 15 m away for the M67, 12 dB for the C4 at 40 m, and 4.4 dB under the old M84's bang at 4 m (which played
at three times full scale). Each event falls off by the inverse-distance law beyond its reference (GunshotAudio's
falloff), with air absorption and occlusion, and the far set takes over at the same level the near set has there.
The smoke's hiss (~80 dB at 1.6 m) sits 7.5 dB over a walking step on concrete, and the ringing at full strength where
the old ring was.
"""
import argparse
import json
import os
import sys
import uuid
import wave

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_sounds as ws  # noqa: E402
from ui_sounds import loudness  # noqa: E402
from world_sounds import SR, G, add, band, burst, envelope, noise, seconds_axis, unit  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ASSETS = os.path.join(ROOT, "Assets")

P0 = 101325.0
C = 343.0
OS = 4                 # the shocks are drawn at 4 x 44.1 kHz and band-limited down, so their fronts don't alias

# Charges in kg of TNT: an M67's 185 g of Composition B (x1.35), an M183 demolition assembly's 9.1 kg of C4 (x1.34),
# an M84's 4.5 g of flash powder, which burns rather than detonates (~0.4 of TNT's blast, an estimate).
FRAG_TNT = 0.25
C4_TNT = 12.2
FLASH_TNT = 0.0018
SURFACE = 1.8          # a burst on the ground: its reflection adds most of a second charge's worth

# How hard each bang is soft-clipped (master), and each part's level against the bang's peak before that.
BANG_DRIVE = {"near": 6.0, "far": 3.0, "flash": 8.0}
FRAG_MIX = {"roar": 0.05, "strikes": 0.006, "whirr": 0.006, "soil": 0.006, "grit": 0.002, "echoes": (0.06, 0.2),
            "rumble": 0.035, "far_echoes": (0.2, 0.45), "far_rumble": 0.15}
C4_MIX = {"roar": 0.08, "chunks": 0.02, "soil": 0.012, "grit": 0.004, "echoes": (0.08, 0.25), "rumble": 0.06,
          "far_echoes": (0.25, 0.5), "far_rumble": 0.2}
FLASH_MIX = {"jets": 0.25, "flash": 0.12, "body": 0.01, "echoes": (0.12, 0.35), "rumble": 0.06}

# Each set: (target loudness in dB, the event's distance in units, the reference distance in units, takes). The blasts'
# targets are over what their files reach, so they play at full volume (see the docstring).
BLASTS = {
    "frag_blast_near": (0.0, 20000, 600, 4),
    "frag_blast_far": (0.0, 20000, 600, 3),
    "c4_blast_near": (0.0, 40000, 1600, 3),
    "c4_blast_far": (0.0, 40000, 1600, 2),
    "flashbang_bang": (0.0, 8000, 160, 4),
}
# Beyond this many units BlastSound plays the far set (BlastSound.FarDistance, keep them together): 40 m for the
# grenade, 100 m for the C4.
FAR_DISTANCES = {"frag": 1600, "c4": 4000}

SMOKE_LOOP_SECONDS = 8.0
SMOKE = {"smoke_ignite": (-28.5, 2500, 64, 2), "smoke_burn": (-28.5, 2500, 64, 1)}
RING = -17.0
RING_SECONDS = 10.0


# ----------------------------------------------------------------------------------------------------------------------
# The blast wave

def kinney(z):
    """Kinney and Graham's free-air blast from TNT at scaled distance `z` (m/kg^(1/3)): the peak overpressure over
    ambient, and the positive phase's length over W^(1/3) in ms."""
    ps = 808 * (1 + (z / 4.5) ** 2) / np.sqrt((1 + (z / 0.048) ** 2) * (1 + (z / 0.32) ** 2) * (1 + (z / 1.35) ** 2))
    td = 980 * (1 + (z / 0.54) ** 10) / ((1 + (z / 0.02) ** 3) * (1 + (z / 0.74) ** 6) * np.sqrt(1 + (z / 6.9) ** 2))
    return float(ps), float(td)


def blast_at(tnt, r):
    """A surface burst of `tnt` kg seen `r` m away: (peak overpressure in Pa, positive phase in s)."""
    w = SURFACE * tnt
    ps, td = kinney(r / w ** (1 / 3))
    return ps * P0, td * w ** (1 / 3) / 1000


def shock_train(seconds, events):
    """Shock waves drawn at OS times the rate and band-limited down. Each event is (time, kind, amplitude, length,
    shape): "friedlander" (length = positive phase, shape = its decay b) or "n" (an N-wave of that length)."""
    sr = SR * OS
    out = np.zeros(int(round(seconds * sr)))
    rise = 12e-6          # a weak shock's front: a few microseconds thick, molecular relaxation spreads it a little
    for at, kind, amp, length, shape in events:
        start = int(round(at * sr))
        if kind == "friedlander":
            n = int(round(length * (10 + 8 / shape) * sr))
            t = np.arange(n) / sr
            x = (1 - t / length) * np.exp(-shape * t / length)
            x *= 0.5 - 0.5 * np.cos(np.pi * np.clip(t / rise, 0, 1))
            x *= np.clip((t[-1] - t) / (0.3 * t[-1] + 1e-9), 0, 1)         # its long tail eased to rest at the end
        else:
            n = int(round(length * sr)) + 4
            t = np.arange(n) / sr
            x = 1 - 2 * np.clip(t / length, 0, 1)
            x *= 0.5 - 0.5 * np.cos(np.pi * np.clip(t / rise, 0, 1))
            x[t > length] = 0.0
        end = min(len(out), start + n)
        if start < len(out):
            out[start:end] += amp * x[: end - start]
    return signal.resample_poly(out, 1, OS)


def lowpass(x, cutoff, order=1):
    return signal.sosfilt(signal.butter(order, min(cutoff, SR * 0.45), btype="lowpass", fs=SR, output="sos"), x)


def air(x, metres):
    """The air's absorption over `metres`, roughly ISO 9613-1's at 20 C and 70%: ~0.3 dB/100 m at 1 kHz, 2.5 at 4 kHz,
    9 at 8 kHz, as a smooth curve applied in the frequency domain."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    db_per_m = 0.003 * (f / 1000) ** 1.7
    return np.fft.irfft(np.fft.rfft(x) * 10 ** (-db_per_m * metres / 20), n)


# ----------------------------------------------------------------------------------------------------------------------
# The surroundings

def echoes(rng, x, count, delay, gain, cutoff, smear=0.002):
    """Echoes off walls and buildings: each a copy of `x` delayed by a random time in `delay`, scaled by a random gain
    in `gain` (path length and how much of the wave the surface catches), low-passed by the longer path through air
    and partly spread out by the surface's roughness (a short decaying noise)."""
    out = np.zeros(len(x))
    t = seconds_axis(0.03)
    for _ in range(count):
        at = rng.uniform(*delay)
        g = rng.uniform(*gain)
        copy = lowpass(x, rng.uniform(*cutoff), 2)
        rough = rng.standard_normal(len(t)) * np.exp(-t / smear)
        rough /= np.sqrt(np.sum(rough ** 2))
        copy = 0.6 * copy + 0.4 * signal.fftconvolve(copy, rough)[: len(copy)] * 3
        add(out, g * copy, at)
    return out


def rumble(rng, x, seconds, tau, hf_tau, build=0.08, split=600.0):
    """The rolling rumble: `x` convolved with the surroundings' late response, filtered noise building over `build`
    and dying with `tau` below `split` Hz and the faster `hf_tau` above it, slowly pulsing as far reflectors' echoes
    come and go. Returned as a unit peak, for the caller to scale."""
    t = seconds_axis(seconds)
    rise = 1 - np.exp(-t / build)
    low = band(rng.standard_normal(len(t)), 0, split) * rise * np.exp(-t / tau)
    high = band(rng.standard_normal(len(t)), split, 7000) * rise * np.exp(-t / hf_tau)
    pulse = 1 + 0.6 * unit(band(rng.standard_normal(len(t)), 0, 5))        # far echoes coming in waves
    ir = (low + 0.5 * high) * np.clip(pulse, 0.2, None)
    tail = signal.fftconvolve(x, ir)[: len(x)]
    return unit(tail)


# ----------------------------------------------------------------------------------------------------------------------
# The fireball, fragments and debris

def roar(rng, seconds, low, high, attack, tau):
    """The fireball's afterburn: hot, fuel-rich products burning as they mix with the air, a turbulent roar."""
    t = seconds_axis(seconds)
    flicker = 1 + 0.35 * unit(band(rng.standard_normal(len(t)), 8, 60))
    return noise(rng, len(t), low, high) * envelope(t, attack, tau) * flicker


def whirr(rng, seconds):
    """A slow, tumbling fragment passing: a breathy buzz whose pitch drops as it goes by (Doppler), chopped at its
    tumble rate, loudest as it passes closest."""
    t = seconds_axis(seconds)
    centre = rng.uniform(0.3, 0.6) * seconds
    width = rng.uniform(0.03, 0.07)
    f = rng.uniform(1100, 2200) * (1 + rng.uniform(0.12, 0.22) * np.tanh(-(t - centre) / width))
    phase = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(phase) + 0.35 * np.sin(2 * phase + 1.1) + 0.15 * np.sin(3 * phase + 2.3)
    rough = 1 + 0.6 * unit(band(rng.standard_normal(len(t)), 0, 500))
    tumble = rng.uniform(90, 260)
    chop = 1 - 0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * tumble * t + rng.uniform(0, 6)))
    near = 1 / (1 + ((t - centre) / width) ** 2)
    return unit(tone * rough * chop * near)


def clod(rng, size):
    """A clod of soil, `size` cm across, landing: a short low thud and a little grit."""
    t = seconds_axis(0.06)
    body = noise(rng, len(t), 120, 900 / max(size, 0.5) ** 0.3) * envelope(t, 0.001, 0.006 * size ** 0.3)
    grit = noise(rng, len(t), 1500, 7000) * envelope(t, 0.0005, 0.004) * 0.3
    return unit(body + grit)


def chunk(rng, size):
    """A chunk of concrete, `size` cm across, landing on hard ground: its knock and the chips it throws."""
    t = seconds_axis(0.12)
    f = float(np.clip(1800 / size ** 0.6, 250, 2500)) * rng.uniform(0.8, 1.2)
    knock = ws.modes(0.12, [(f, 1.0, 0.012), (f * 1.6, 0.6, 0.008), (f * 2.4, 0.35, 0.005)], 0.0003, rng)
    crack = noise(rng, len(t), 1200, 9000) * envelope(t, 0.0002, 0.003)
    return unit(unit(knock) + 0.6 * crack)


def rain(rng, seconds, start, count, height, launch, sizes, make, level, restitution=0.25):
    """Debris thrown up at `start` s and landing: `count` pieces from `height` m with launch speeds N(launch) m/s, made
    by make(rng, size), louder the faster and larger, with the dust and grit coming down among them."""
    hits = [(at + start, v) for at, v in ws.falling(rng, count, height, launch, restitution, bounces=1)]
    size_list = [float(rng.choice(sizes)) for _ in hits]
    out = ws.debris(rng, seconds, hits, size_list, make, 1.0)
    out = unit(out) if np.any(out) else out
    out += 0.35 * ws.dust(rng, seconds, hits, 800, 6000, 1.0)
    return level * out


def fragment_strikes(rng, seconds, start, spread, count, level):
    """Fragments that missed you striking what's round you: thuds into soil, chips off stone, a ping off steel."""
    out = np.zeros(int(round(seconds * SR)))
    for _ in range(count):
        kind = rng.choice(["soil", "stone", "metal"], p=[0.5, 0.38, 0.12])
        if kind == "soil":
            t = seconds_axis(0.04)
            x = noise(rng, len(t), 150, 2500) * envelope(t, 0.0003, 0.005)
        elif kind == "stone":
            x = ws.stone_chip(rng, rng.uniform(3, 9))
        else:
            x = ws.fragment(rng, rng.uniform(2200, 5200), rng.uniform(0.01, 0.03), 4)
        add(out, level * rng.lognormal(0, 0.5) * unit(x), start + rng.exponential(spread))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# The blasts

def master(bang, rest, drive):
    """At these levels the ear overloads (and so does any microphone): the bang (the direct wave, the fragments' cracks,
    the fireball) is soft-clipped by `drive`, which squeezes its millisecond peak into a heavier thump. The rest (the
    surroundings, the debris) goes in after, at the level it had against the bang's loudness, so squeezing the bang's
    peak doesn't bring the tail up with it. The sum is ready for world_sounds.finish at a light drive."""
    peak = np.abs(bang).max()
    unshaped = bang / peak
    shaped = np.tanh(drive * unshaped) / np.tanh(drive)
    gain = 10 ** ((loudness(shaped) - loudness(unshaped)) / 20)
    return shaped + gain * rest / peak


def after(seconds, t0):
    """1 from `t0` on, 0 before: for what starts with the blast's arrival."""
    return (seconds_axis(seconds) >= t0).astype(float)


def frag_blast(rng, take, far):
    """An M67 surface burst, 15 m away or (far) 150 m."""
    seconds = 5.0 if far else 3.6
    r = rng.uniform(130, 170) if far else rng.uniform(13, 17)
    ps, td = blast_at(FRAG_TNT, r)
    if far:
        td *= 1.25            # the positive phase stretches as the weak shock runs on
    t0 = 0.045                # the fragments outrun the blast: they're heard from ~30 ms before it
    events = [(t0, "friedlander", 1.0, td, rng.uniform(0.55, 0.75)),
              (t0 + td * rng.uniform(1.2, 1.6), "friedlander", rng.uniform(0.06, 0.1), td * 0.5, 0.8)]
    if not far:
        # Supersonic fragments passing within a few metres, ahead of the blast: each an N-wave of ~0.1-0.2 ms whose
        # peak falls as the miss distance to the 3/4 (Whitham), ~1 kPa at 1 m for a 4 mm fragment at Mach 2.5.
        for _ in range(rng.integers(4, 9)):
            miss = rng.uniform(0.6, 5.0)
            amp = (1000 / ps) * miss ** -0.75 * rng.lognormal(0, 0.3) * rng.uniform(0.7, 1.0)
            length = 1.1e-4 * miss ** 0.25 * rng.uniform(0.8, 1.3)
            events.append((t0 - rng.uniform(0.006, 0.022), "n", amp, length, 0))
    direct = shock_train(seconds, events)
    if far:
        direct = air(direct, r)
    fireball = roar(rng, seconds, 70, 900, 0.004, 0.05) * after(seconds, t0)
    bang = direct + FRAG_MIX["roar"] * fireball * (0.5 if far else 1.0)

    rest = np.zeros(len(direct))
    if far:
        rest += echoes(rng, direct, 7, (0.12, 1.6), FRAG_MIX["far_echoes"], (1500, 3500))
        rest += FRAG_MIX["far_rumble"] * rumble(rng, direct + rest, seconds, 1.3, 0.5, build=0.25)
    else:
        rest += fragment_strikes(rng, seconds, t0 - 0.028, 0.025, rng.integers(10, 18), FRAG_MIX["strikes"])
        for _ in range(rng.integers(1, 4)):
            add(rest, FRAG_MIX["whirr"] * rng.uniform(0.6, 1.0) * whirr(rng, rng.uniform(0.25, 0.45)),
                t0 + rng.uniform(0.02, 0.35))
        rest += rain(rng, seconds, t0, 70, (0.0, 0.3), (5.0, 2.5), [0.5, 1, 2, 3], clod, FRAG_MIX["soil"])
        rest += rain(rng, seconds, t0, 30, (0.0, 0.3), (6.0, 3.0), [1, 2, 3], ws.stone_chip, FRAG_MIX["grit"])
        # Echoes off buildings 10-50 m off, then the rolling rumble.
        rest += echoes(rng, direct, 7, (0.03, 0.3), FRAG_MIX["echoes"], (2500, 6000))
        rest += FRAG_MIX["rumble"] * rumble(rng, direct, seconds, 0.75, 0.25, build=0.12)
    return master(bang, rest, BANG_DRIVE["far" if far else "near"])


def c4_blast(rng, take, far):
    """A 9 kg C4 demolition charge on the ground, 40 m away or (far) 400 m."""
    seconds = 7.5 if far else 6.0
    r = rng.uniform(340, 460) if far else rng.uniform(35, 45)
    ps, td = blast_at(C4_TNT, r)
    if far:
        td *= 1.3
    t0 = 0.03
    events = [(t0, "friedlander", 1.0, td, rng.uniform(0.45, 0.6)),
              (t0 + td * rng.uniform(1.3, 1.7), "friedlander", rng.uniform(0.07, 0.11), td * 0.5, 0.8)]
    direct = shock_train(seconds, events)
    if far:
        direct = air(direct, r)
    fireball = roar(rng, seconds, 40, 600, 0.01, 0.16) * after(seconds, t0)
    bang = direct + C4_MIX["roar"] * fireball * (0.5 if far else 1.0)

    rest = np.zeros(len(direct))
    if far:
        rest += echoes(rng, direct, 8, (0.3, 2.5), C4_MIX["far_echoes"], (900, 2500))
        rest += C4_MIX["far_rumble"] * rumble(rng, direct + rest, seconds, 1.8, 0.6, build=0.35)
    else:
        # Concrete and earth thrown up to ~25 m, landing for 2-3 s; the heavier pieces first, the dust last.
        rest += rain(rng, seconds, t0, 60, (0.0, 1.0), (14.0, 6.0), [3, 5, 8, 12, 20], chunk, C4_MIX["chunks"])
        rest += rain(rng, seconds, t0, 120, (0.0, 1.0), (10.0, 5.0), [0.5, 1, 2, 4], clod, C4_MIX["soil"])
        rest += rain(rng, seconds, t0, 60, (0.0, 1.0), (12.0, 6.0), [2, 4, 6], ws.stone_chip, C4_MIX["grit"])
        rest += echoes(rng, direct, 8, (0.06, 0.6), C4_MIX["echoes"], (1500, 4000))
        rest += C4_MIX["rumble"] * rumble(rng, direct, seconds, 1.1, 0.35, build=0.15)
    return master(bang, rest, BANG_DRIVE["far" if far else "near"])


def flashbang_bang(rng, take):
    """An M84 going off ~4 m away, on a floor."""
    seconds = 2.6
    r = rng.uniform(3.5, 4.5)
    ps, td = blast_at(FLASH_TNT, r)
    t0 = 0.01
    events = [(t0, "friedlander", 1.0, td, rng.uniform(0.9, 1.3)),
              # The ports' jets and the flash burning out keep the pressure up for a few ms after the shock.
              (t0 + td * rng.uniform(2.0, 3.0), "friedlander", rng.uniform(0.12, 0.2), td * 1.5, 1.0)]
    direct = shock_train(seconds, events)
    t = seconds_axis(seconds)
    since = np.maximum(t - t0, 0)
    jets = noise(rng, len(t), 1500, 9000) * envelope(since, 0.0003, 0.004) * (t >= t0)
    flash = noise(rng, len(t), 300, 4000) * envelope(since, 0.001, 0.02) * (t >= t0)
    bang = direct + FLASH_MIX["jets"] * jets + FLASH_MIX["flash"] * flash

    rest = np.zeros(len(t))
    # The body kicked up and coming down: a steel tube's clank and a bounce or two.
    land = t0 + rng.uniform(0.18, 0.4)
    speed = rng.uniform(2.5, 4.0)
    for _ in range(3):
        f = rng.uniform(1100, 1500)
        clank = ws.modes(0.3, [(f, 1.0, 0.05), (f * 2.7, 0.6, 0.03), (f * 5.1, 0.35, 0.015)], 0.0001, rng)
        add(rest, FLASH_MIX["body"] * (speed / 3) ** 1.2 * unit(clank), land)
        land += 2 * speed * 0.35 / G
        speed *= 0.35
        if speed < 0.5:
            break
    # A room's or a street's walls: strong early reflections, a short tail.
    rest += echoes(rng, direct, 8, (0.005, 0.08), FLASH_MIX["echoes"], (4000, 9000), smear=0.001)
    rest += FLASH_MIX["rumble"] * rumble(rng, direct, seconds, 0.45, 0.2, build=0.03, split=900)
    return master(bang, rest, BANG_DRIVE["flash"])


# ----------------------------------------------------------------------------------------------------------------------
# The smoke grenade

def periodic_noise(rng, n, low, high, order=2):
    """Unit-RMS noise band-passed in the frequency domain, so it's periodic over its n samples."""
    spectrum = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    gain = np.ones_like(f)
    if low:
        gain /= np.sqrt(1.0 + (low / np.maximum(f, 1e-6)) ** (2 * order))
    if high:
        gain /= np.sqrt(1.0 + (f / high) ** (2 * order))
    x = np.fft.irfft(spectrum * gain, n)
    return x / np.sqrt(np.mean(x ** 2))


def periodic_wander(rng, n, rate, depth):
    """A slow random wander, periodic over n samples: 1 +- `depth`, changing at about `rate` Hz."""
    return 1 + depth * unit(periodic_noise(rng, n, 0, rate, 2))


def add_wrapped(track, x, at):
    """x added into the loop from sample `at`, wrapping round the end."""
    start = int(at) % len(track)
    end = start + len(x)
    if end <= len(track):
        track[start:end] += x
    else:
        split = len(track) - start
        track[start:] += x[:split]
        track[: end - len(track)] += x[split:]


def spit(rng):
    """A spit or pop from the burning composition: a crack of slag bursting, 0.2-3 ms."""
    t = seconds_axis(0.012)
    length = rng.uniform(0.0002, 0.003)
    return noise(rng, len(t), rng.uniform(600, 2500), 11000) * envelope(t, 0.00005, length)


def smoke_burn(rng):
    n = int(SMOKE_LOOP_SECONDS * SR)
    # The jets: a broad breathy hiss round 1-2 kHz, swelling and easing as the burning rate wanders.
    hiss = periodic_noise(rng, n, 450, 5500, 2) * periodic_wander(rng, n, 1.5, 0.25)
    air_rush = periodic_noise(rng, n, 2500, 9000, 2) * periodic_wander(rng, n, 2.5, 0.3) * 0.35
    # The burning front's flutter, under it: the combustion pulsing at 6-12 Hz.
    flutter = periodic_noise(rng, n, 120, 900, 2) * periodic_wander(rng, n, 10, 0.5) * 0.45
    out = hiss + air_rush + flutter
    # Spitting and the odd sputter.
    for _ in range(int(SMOKE_LOOP_SECONDS * 9)):
        add_wrapped(out, 2.2 * rng.lognormal(0, 0.8) * spit(rng), rng.integers(n))
    for _ in range(2):
        at = rng.integers(n)
        for _ in range(rng.integers(6, 16)):
            add_wrapped(out, 2.5 * rng.lognormal(0, 0.6) * spit(rng), at + rng.integers(int(0.35 * SR)))
    return out


def smoke_ignite(rng, take):
    """The starter mix lighting: a soft pop, then the hiss rising over ~1.2 s as the composition takes hold, eased out
    by 2.5 s as the loop (faded in by the smoke prefab over the same time) takes over."""
    seconds = 2.8
    t = seconds_axis(seconds)
    pop = noise(rng, len(t), 120, 2500) * envelope(t, 0.0008, 0.012)
    pop += 0.6 * noise(rng, len(t), 2000, 9000) * envelope(t, 0.0002, 0.002)
    grow = np.clip((t - 0.03) / 1.2, 0, 1) ** 1.5
    fade = np.clip((2.6 - t) / 1.2, 0, 1)
    hiss = noise(rng, len(t), 450, 6000) * grow * fade * (1 + 0.3 * unit(band(rng.standard_normal(len(t)), 0, 3)))
    sputter = np.zeros(len(t))
    for _ in range(rng.integers(10, 18)):
        add(sputter, rng.lognormal(0, 0.7) * spit(rng), rng.uniform(0.1, 1.6))
    return 1.4 * pop + 0.5 * hiss + 0.4 * unit(sputter)


# ----------------------------------------------------------------------------------------------------------------------
# The ringing

def ear_ringing(rng):
    """Stereo: each ear's tone near 4.2 kHz (a little apart), drifting by a few tenths of a percent, a fainter second
    tone in one ear, and the breathy hiss of the first seconds."""
    t = seconds_axis(RING_SECONDS)
    ears = []
    base = rng.uniform(4000, 4300)
    for ear in range(2):
        f = base * (1 + (0.004 if ear else -0.003)) * (1 + 0.003 * unit(band(rng.standard_normal(len(t)), 0, 0.6)))
        tone = np.sin(2 * np.pi * np.cumsum(f) / SR + rng.uniform(0, 6))
        tone *= 1 + 0.08 * unit(band(rng.standard_normal(len(t)), 0, 3))
        if ear == 1:
            f2 = base * 1.47 * (1 + 0.002 * unit(band(rng.standard_normal(len(t)), 0, 0.4)))
            tone += 0.22 * np.sin(2 * np.pi * np.cumsum(f2) / SR)
        hiss = noise(rng, len(t), 3000, 8000) * np.exp(-t / 1.4) * 0.35
        x = (tone + hiss) * envelope(t, 0.015, 1e9)
        fade = np.clip((RING_SECONDS - t) / 0.4, 0, 1)
        ears.append(x * fade)
    return np.stack(ears, axis=1)


# ----------------------------------------------------------------------------------------------------------------------
# Writing

def finish_blast(x, drive):
    """world_sounds.finish, after bringing the bang's first ms in from the file's start (a leading silence would delay it)."""
    return ws.finish(x, drive)


def write_stereo(path, x):
    pcm = np.round(np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def write_loop_meta(folder, name):
    """The loop's import settings (thermite_sounds.write_loop_meta's): written before the WAV so the editor's first
    import loops it."""
    path = os.path.join(folder, name + ".wav.meta")
    meta = {"loop": True, "start": 0, "end": 0, "rate": SR, "compress": False, "bitrate": 256}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            meta = {**json.load(f), "loop": True}
    meta.setdefault("guid", str(uuid.uuid4()))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, indent=2)


def write_flat_event(folder, sound_path, name, take, volume):
    """A flat (2D) event on the default mixer, for a sound inside the head."""
    path = os.path.join(folder, name + ".sound")
    if os.path.exists(path):
        return False
    event = {
        "UI": True,
        "Volume": f"{volume:.4f}",
        "Pitch": "1",
        "Decibels": 70,
        "SelectionMode": "Random",
        "Sounds": [f"{sound_path}/{take}.vsnd"],
        "Occlusion": False,
        "AirAbsorption": False,
        "Transmission": False,
        "OcclusionRadius": 64,
        "DistanceAttenuation": False,
        "__references": [],
        "__version": 1,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(event, f, indent=2)
        f.write("\n")
    return True


MAKERS = {
    "frag_blast_near": (lambda rng, i: frag_blast(rng, i, False), 1.0),
    "frag_blast_far": (lambda rng, i: frag_blast(rng, i, True), 1.0),
    "c4_blast_near": (lambda rng, i: c4_blast(rng, i, False), 1.0),
    "c4_blast_far": (lambda rng, i: c4_blast(rng, i, True), 1.0),
    "flashbang_bang": (flashbang_bang, 1.0),
}
FOLDERS = {
    "frag_blast_near": "sounds/weapons/grenade",
    "frag_blast_far": "sounds/weapons/grenade",
    "c4_blast_near": "sounds/weapons/bomb",
    "c4_blast_far": "sounds/weapons/bomb",
    "flashbang_bang": "sounds/weapons/grenade",
    "smoke_ignite": "sounds/weapons/grenade",
    "smoke_burn": "sounds/weapons/grenade",
    "ear_ringing": "sounds/player",
}


def loudest_set(name, make, count, seed, target, drive):
    """world_sounds.build_set, keeping the loudest `count` of twice as many takes: the takes are levelled to the
    quietest, and a blast's loudness varies a few dB from take to take."""
    takes = [ws.finish(make(np.random.default_rng(seed + i), i), drive) for i in range(2 * count)]
    takes.sort(key=loudness, reverse=True)
    takes, volume = ws.level(takes[:count], target)
    return [f"{name}_{i + 1:02d}" for i in range(count)], takes, volume


def build():
    """Every set: name -> (takes, volume, distance, reference)."""
    out = {}
    for index, (name, (target, distance, reference, count)) in enumerate(BLASTS.items()):
        make, drive = MAKERS[name]
        names, takes, volume = loudest_set(name, make, count, 21000 + 100 * index, target, drive)
        out[name] = (names, takes, volume, distance, reference)
    target, distance, reference, count = SMOKE["smoke_ignite"]
    names, takes, volume = ws.build_set("smoke_ignite", smoke_ignite, count, 22000, target, 1.2)
    out["smoke_ignite"] = (names, takes, volume, distance, reference)
    loop = smoke_burn(np.random.default_rng(22100))
    loop = loop / np.abs(loop).max() * 10 ** (-1 / 20)
    target, distance, reference, _ = SMOKE["smoke_burn"]
    volume = min(1.0, 10 ** ((target - loudness(loop)) / 20))
    out["smoke_burn"] = (["smoke_burn"], [loop], volume, distance, reference)
    ring = ear_ringing(np.random.default_rng(23000))
    # FlashbangEffect sets the handle's volume as the hearing recovers, so the level goes in the file.
    ring = ring * 10 ** ((RING - loudness(ring.mean(axis=1))) / 20)
    out["ear_ringing"] = (["ear_ringing"], [ring], 1.0, None, None)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", help="write a WAV with every take, and the smoke from ignition to burn-out")
    parser.add_argument("--out", help="write the sounds under this folder instead of Assets (to try changes)")
    args = parser.parse_args()
    assets = args.out or ASSETS

    sets = build()
    for name, (names, takes, volume, distance, reference) in sets.items():
        sound_path = FOLDERS[name]
        folder = os.path.join(assets, *sound_path.split("/"))
        os.makedirs(folder, exist_ok=True)
        if name == "smoke_burn":
            write_loop_meta(folder, name)
        for take_name, x in zip(names, takes):
            (write_stereo if x.ndim == 2 else ws.write_wav)(os.path.join(folder, take_name + ".wav"), x)
        if name == "ear_ringing":
            written = write_flat_event(folder, sound_path, name, names[0], volume)
        else:
            written = ws.write_event(folder, sound_path, name, names, volume, 1.0 if len(names) > 1 else 0.0,
                                     "0.97 1.03" if len(names) > 1 else "1", distance, reference)
        mono = [x.mean(axis=1) if x.ndim == 2 else x for x in takes]
        ws.describe(name, mono, volume)
        if not written:
            print(f"  {name}.sound exists, left as it is")

    if args.preview:
        gap = ws.gap
        parts = []
        for name in BLASTS:
            names, takes, volume, *_ = sets[name]
            for x in takes:
                parts += [x * volume, gap(0.8)]
            parts.append(gap(0.7))
        # The smoke as the prefab plays it: the ignition, the loop fading in over 1.4 s, 20 s of it, then the fade.
        loop = sets["smoke_burn"][1][0] * sets["smoke_burn"][2]
        body = np.tile(loop, 3)[: int(22 * SR)]
        t = np.arange(len(body)) / SR
        body *= np.clip(t / 1.4, 0, 1) * np.clip((22 - t) / 4.0, 0, 1)
        ignite = sets["smoke_ignite"][1][0] * sets["smoke_ignite"][2]
        body[: len(ignite)] += ignite
        parts += [body, gap(1.0)]
        ring = sets["ear_ringing"][1][0] * sets["ear_ringing"][2]
        mono_parts = [p if p.ndim == 1 else p for p in parts]
        mono = np.concatenate(mono_parts)
        stereo = np.concatenate([np.stack([mono, mono], axis=1), ring])
        write_stereo(args.preview, stereo / max(1.0, np.abs(stereo).max()))
        print(f"preview: {args.preview}")


if __name__ == "__main__":
    main()
