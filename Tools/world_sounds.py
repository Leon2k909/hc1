"""
World sounds modelled on the real thing, in place of s&box's stock ones: bullet impacts by material, a soldier's boot
footsteps, running steps and landings by floor, and the menus' button press and hover. They're synthesised from the
physics of each event, so there are no samples, and every figure here can be re-tuned.

    python Tools/world_sounds.py [--preview <wav>] [--compare <wav>] [--out <dir>]

Writes, with a .sound event for each set if it doesn't exist yet (an event may be tuned in the editor, so it isn't
overwritten; delete one to have it rewritten):
- Assets/sounds/world/impacts/bullet_<material>_<n>.wav: masonry, tile, metal, sheetmetal, glass, wood, plastic, dirt,
  grass, fabric and flesh;
- Assets/sounds/world/footsteps/{step,run,land}_<floor>_<n>.wav: concrete, tile, wood, metal, dirt and grass;
- Assets/sounds/ui/menu/ui_button_{press,hover}_<n>.wav.
Code/World/WorldSounds.cs picks the impact, step and landing for a surface. --preview writes every take in a row, with
walks, runs and bursts; --compare writes s&box's stock sound, then the new one, for each set (decoded from the s&box
install, each pair at its events' volumes). --out writes the sounds under another folder instead of Assets.

What each is, and why it sounds like it does:

Bullet impacts, heard close by (a 5.56 round at ~800 m/s). Every hard target has the strike (the bullet stops in tens of
microseconds: a pressure spike), the air it and the spray shove aside (a Friedlander pulse a millisecond or two wide), and
the struck body's own low modes, radiated from its whole face: a wall's or a door's thud, 70-500 Hz, which is most of
what makes an impact sound heavy. Then whatever the material does, and the surroundings: the ground's reflection a few ms
later, early reflections and a short diffuse tail, kept low (s&box plays a sound dry).
- masonry (concrete, brick, stone, plaster): the crater's "pock" and brittle fracture, a crackle over ~10 ms; spall
  thrown out, a short hiss; then grit and 10-24 chips falling from wherever the round hit (0.3-1.5 m up) and bouncing
  at a third of their speed, within about half a second. One take in five has a ricochet: a fragment whining off, its
  pitch falling as it recedes and slows (Doppler), buzzing at its tumble rate.
- tile (ceramic, glazed): brighter and more brittle than concrete, with a short ceramic ring and harder chips.
- metal (thick steel): the plate's bending modes from ~120 Hz to 9 kHz, the high ones dying first, and the "ping" of the
  modes round the strike, under a splash of lead and jacket fragments. Two takes in five ricochet.
- sheetmetal (a car panel, a tin roof): the puncture's crack and tear, then a thin sheet's dense modes, a boomy wobble
  that dies in a quarter of a second, and a rattle against its fixings.
- glass (a pane that doesn't give way): the hole's sharp crack, cracks running out across the pane, the pane's thump and
  short ring, and fragments tinkling down.
- wood (a beam, a door, a crate): a hollow "thock" from the member's modes (110-240 Hz up, Q ~ 25), splintering fibres,
  a few splinters landing, soft and dull.
- plastic: a hollow shell's heavily damped modes and a dull crack.
- dirt: no crack: the soil gives, a low thud and the "pfft" of the spray, then soil pattering back down. Most of what's
  thrown up is dust, which lands unheard.
- grass: dirt's thud and spray, with the blades' rustle and a few stems snapping, and less soil in the air.
- fabric (and cardboard, a sandbag): a snap and a flutter as the round goes through, and what's behind it thudding.
- flesh: a bullet into a body, the "thwack" people describe: the uniform's cloth snapping, the skin's slap and the
  tissue's knock with the body's thud under it, with no ring and no debris.
Their octave spectra were compared with s&box's recordings of the same materials (real Foley), which showed the first
version had almost no low end. Most now follow them within about 6 dB from 125 Hz to 4 kHz. Dirt and grass are up to
9 dB brighter at 1-2 kHz, since s&box's are a melee blow's, not a round's spray.

Footsteps of a soldier in combat boots (rubber lug soles, ~95 kg with kit). Each part of the sole that meets the floor
(heel, then forefoot) slaps the rubber on it, the heel's rubber and the leg behind it compress (a 150-650 Hz knock, the
body of a step) and the leg's weight arrives through it (a low thump). The floor adds its own: concrete grit crushed
under the lugs, a glazed tile's click, floorboards' hollow modes on their joists (the odd creak), a steel deck's ring,
soil crunching, turf giving and grass blades swishing. Then the sole scuffs as the foot pushes off.
- step: a walk, heel then forefoot 70-110 ms later, a light push-off.
- run: a sprint, forefoot first and the heel just after, a hard push-off, the trousers and the kit (magazines in their
  pouches, the sling's hardware) rattling as the body comes down.
- land: both feet within 15-45 ms, at several times body weight: a heavy thump through the floor, the kit clattering.
Their levels follow the real ones against each other, not s&box's (which had grass 21 dB under concrete and a metal
deck 15 dB under it): walking on concrete stays where s&box's was, tile +1 dB, floorboards +2, a steel deck +4, dirt
-5, grass -10; a run is 6 dB over a walk (measured footfalls rise 6-10 dB from walking to running), a landing 4 dB over
a run. That landing is a jump's; in the game it's louder the faster you land (PlayerPawn.PlayFallSound).

The menus' clicks (s&box's were Kenney's game sounds): the press is a sealed tactile push-button, its metal dome
snapping through and the plunger bottoming out; the hover is a rotary switch's detent, a tick you barely hear. The press
sits with the header's click (ui_sounds.py), the hover 2 dB over s&box's.

All levels are K-weighted loudness of the loudest 50 ms (ui_sounds.loudness), matched through each event's volume.
Every take in a set is as loud as the others, and the events add a little pitch and level spread of their own.
"""
import argparse
import json
import os
import struct
import sys
import wave

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_sounds import UI_MIXER, loudness  # noqa: E402

SR = 44100
G = 9.81
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ASSETS = os.path.join(ROOT, "Assets")
SBOX_CORE = r"D:/SteamLibrary/steamapps/common/sbox/core"

# Bullet impacts: (target loudness in dB, the event's distance in units, takes). Masonry, what most map surfaces are,
# stays where s&box's "generic" impact was (-14.8); the rest follow how loud each is next to it in real life.
IMPACTS = {
    "masonry": (-15.0, 5000, 5),
    "tile": (-15.0, 5000, 5),
    "metal": (-11.0, 6000, 5),
    "sheetmetal": (-13.0, 5000, 5),
    "glass": (-16.0, 5000, 5),
    "wood": (-18.0, 4000, 5),
    "plastic": (-20.0, 3000, 4),
    "dirt": (-22.0, 3000, 5),
    "grass": (-24.0, 3000, 5),
    "fabric": (-26.0, 2000, 4),
    "flesh": (-21.0, 2500, 5),
}

# Footsteps: the walk's target loudness by floor. s&box's concrete walk measures -36.3 dB at its event's volume.
FLOORS = {
    "concrete": -36.0,
    "tile": -35.0,
    "wood": -34.0,
    "metal": -32.0,
    "dirt": -41.0,
    "grass": -46.0,
}
RUN_OVER_WALK = 6.0
LAND_OVER_RUN = 4.0
STEP_TAKES, RUN_TAKES, LAND_TAKES = 8, 8, 4
STEP_DISTANCE, RUN_DISTANCE, LAND_DISTANCE = 1600, 2400, 2400

# Menus: the press sits with ui_nav_tab (-31.9); s&box's hover measures -49.9.
UI_TARGETS = {"ui_button_press": -31.9, "ui_button_hover": -47.9}
UI_TAKES = 3

# Where each 3D event holds its full level: impacts are loud up close, footsteps are heard from a pace or two.
IMPACT_REFERENCE = 96

# The soft clipper's drive for impacts (the rest use 1.3): a close impact's strike is a spike far over the rest, and
# at 1.3 tile's came out 1 dB under its level with the event at full volume.
IMPACT_DRIVE = 2.0
STEP_REFERENCE = 64


# ----------------------------------------------------------------------------------------------------------------------
# Building blocks

def seconds_axis(seconds):
    return np.arange(int(round(seconds * SR))) / SR


def envelope(t, attack, tau):
    """A half-cosine rise over `attack` seconds, then an exponential decay with time constant `tau`."""
    rise = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / max(attack, 1e-6), 0.0, 1.0))
    return rise * np.exp(-np.maximum(t - attack, 0.0) / tau)


def band(x, low, high, order=2):
    high = min(high, SR * 0.45)
    if low <= 0:
        sos = signal.butter(order, high, btype="lowpass", fs=SR, output="sos")
    else:
        sos = signal.butter(order, [low, high], btype="bandpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def unit(x):
    peak = np.abs(x).max()
    return x / peak if peak > 0 else x


def noise(rng, n, low, high, order=2):
    return unit(band(rng.standard_normal(n), low, high, order))


def burst(rng, seconds, low, high, attack, tau):
    """Band-passed noise under an envelope: a scrape, a hiss, a slap."""
    t = seconds_axis(seconds)
    return noise(rng, len(t), low, high) * envelope(t, attack, tau)


def modes(seconds, partials, attack=0.0001, rng=None):
    """Damped sines, each (frequency in Hz, amplitude, decay time constant in s), from random phases if given a rng."""
    t = seconds_axis(seconds)
    out = np.zeros(len(t))
    for f, a, tau in partials:
        if f >= SR * 0.45:
            continue
        phase = rng.uniform(0, 2 * np.pi) if rng is not None else 0.0
        out += a * np.sin(2 * np.pi * f * t + phase) * np.exp(-t / tau)
    return out * envelope(t, attack, 1e9)


def add(out, x, at):
    start = int(round(at * SR))
    if start >= len(out) or start < 0:
        return
    end = min(len(out), start + len(x))
    out[start:end] += x[: end - start]


def spike(rng, width=0.00012):
    """The strike itself: a pressure pulse a fraction of a millisecond wide, with a little ringing of the air."""
    t = seconds_axis(0.004)
    pulse = np.exp(-0.5 * ((t - 3 * width) / width) ** 2)
    pulse = np.gradient(pulse)            # radiated pressure goes with the change in force
    return unit(pulse + 0.15 * noise(rng, len(t), 3000, 16000) * envelope(t, 0.00005, 0.0004))


def crackle(rng, seconds, count, low, high, spread, amp_sigma=0.6):
    """Many tiny fractures or grains: `count` clicks, spread exponentially over time with mean `spread`, each the
    band's impulse response, with random sign and size."""
    n = int(round(seconds * SR))
    train = np.zeros(n)
    times = rng.exponential(spread, count)
    amps = rng.lognormal(0.0, amp_sigma, count) * rng.choice([-1.0, 1.0], count)
    for at, a in zip(times, amps):
        i = int(at * SR)
        if i < n:
            train[i] += a * np.exp(-at / (spread * 3))
    return unit(band(train, low, high, 2)) if np.any(train) else train


def fragment(rng, freq, tau, partials=3):
    """A small hard piece striking something: a tick and a few of its modes (plate-like ratios)."""
    ratios = [1.0, rng.uniform(1.5, 1.75), rng.uniform(2.2, 2.6), rng.uniform(3.0, 3.6)][:partials]
    amps = [1.0, 0.6, 0.35, 0.2][:partials]
    seconds = min(0.25, 7 * tau)
    ring = modes(seconds, [(freq * r, a, tau / r ** 0.6) for r, a in zip(ratios, amps)], 0.00008, rng)
    t = seconds_axis(seconds)
    tick = noise(rng, len(t), min(freq * 0.8, 8000), 16000) * envelope(t, 0.00003, 0.00025)
    return unit(ring) * 0.7 + tick * 0.5


def falling(rng, count, height, launch, restitution=0.3, bounces=2, spread=0.0):
    """When and how hard `count` pieces land: each thrown with a vertical speed ~ N(launch) m/s from `height` metres
    (a range), then bouncing at `restitution` of its speed. Returns (time, speed) pairs."""
    hits = []
    for _ in range(count):
        h = rng.uniform(*height)
        vz = rng.normal(*launch)
        v = np.sqrt(vz * vz + 2 * G * h)
        at = (vz + v) / G + rng.uniform(0, 0.004) + rng.uniform(0, spread)
        hits.append((at, v))
        for _ in range(bounces):
            v *= restitution * rng.uniform(0.7, 1.2)
            if v < 0.35:
                break
            at += 2 * v / G
            hits.append((at, v))
    return hits


def debris(rng, seconds, hits, sizes, make, loud):
    """Each landing in `hits` made by make(rng, size): louder the faster and larger the piece."""
    out = np.zeros(int(round(seconds * SR)))
    for (at, v), size in zip(hits, sizes):
        add(out, loud * (v / 5.0) * size ** 1.2 * make(rng, size), at)
    return out


def dust(rng, seconds, hits, low, high, level):
    """Fine grit and dust landing with the pieces: a faint hiss that follows how many land when."""
    n = int(round(seconds * SR))
    density = np.zeros(n)
    for at, v in hits:
        i = int(at * SR)
        if i < n:
            density[i] += v
    width = int(0.03 * SR)
    density = np.convolve(density, np.hanning(width), "same")
    if density.max() > 0:
        density /= density.max()
    return level * noise(rng, n, low, high) * density


def ricochet(rng, seconds):
    """A fragment whining off: its pitch falls as it recedes and slows (Doppler), and it buzzes at its tumble rate."""
    t = seconds_axis(seconds)
    start = rng.uniform(2600, 4300)
    end = start * rng.uniform(0.33, 0.5)
    glide = rng.uniform(0.1, 0.25)
    f = end + (start - end) * np.exp(-t / glide)
    f *= 1 + 0.04 * np.exp(-t / 0.012)                 # a shade higher as it passes closest, just after the strike
    phase = 2 * np.pi * np.cumsum(f) / SR
    tumble = rng.uniform(70, 220) * (1 + 0.15 * np.sin(2 * np.pi * rng.uniform(3, 7) * t))
    am = 1 - 0.55 * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(tumble) / SR + rng.uniform(0, 6)))
    tone = np.sin(phase) + 0.3 * np.sin(2 * phase + 1.1) + 0.12 * np.sin(3 * phase + 2.3)
    rough = 1 + 0.45 * unit(band(rng.standard_normal(len(t)), 0, 400))    # the whine is breathy, not a pure tone
    env = envelope(t, rng.uniform(0.006, 0.015), rng.uniform(0.22, 0.4)) * (1 - np.clip((t - seconds + 0.08) / 0.08, 0, 1))
    return unit(tone * am * rough * env)


# ----------------------------------------------------------------------------------------------------------------------
# Bullet impacts

def blast(rng, width):
    """The air the strike and its spray shove aside: a Friedlander pulse whose positive phase lasts `width` s, so its
    energy sits around 1 / (2 width), with the spray's turbulence on it."""
    t = seconds_axis(width * 10)
    x = (1 - t / width) * np.exp(-2.0 * t / width)
    x = x - np.mean(x)
    x = unit(x) + 0.25 * noise(rng, len(t), 300, 5000) * envelope(t, width * 0.1, width)
    return unit(x)


def structure(rng, low, high, count, tau, seconds=0.4):
    """The struck body's low modes: a wall, a door or a pane radiating the blow from its whole face, which a large face
    does well at low frequencies. `tau` is the lowest mode's decay; the higher ones die sooner."""
    freqs = np.exp(rng.uniform(np.log(low), np.log(high), count))
    partials = [(f, rng.lognormal(0, 0.3) * (f / low) ** -0.3, tau * (low / f) ** 0.4) for f in freqs]
    return unit(modes(seconds, partials, 0.0004, rng))


def patter(rng, seconds, hits, low, high, sigma=0.7):
    """Grit, fine fragments or soil landing at the times and speeds in `hits`: a patter of tiny grains."""
    n = int(round(seconds * SR))
    train = np.zeros(n)
    for at, v in hits:
        i = int(at * SR)
        if i < n:
            train[i] += rng.lognormal(0, sigma) * v * rng.choice([-1.0, 1.0])
    return unit(band(train, low, high)) if np.any(train) else train


def surroundings(rng, x, early=1.0, tail=1.0):
    """What's round the impact joins in: the ground's reflection a few ms later, early reflections off nearby surfaces
    and a short diffuse tail, all kept low. s&box plays a sound dry, and a dry impact sounds pasted on."""
    out = x.copy()
    add(out, 0.4 * early * band(x, 0, 5000), rng.uniform(0.003, 0.007))
    for _ in range(8):
        add(out, rng.uniform(0.05, 0.16) * early * rng.choice([-1.0, 1.0]) * band(x, 150, 6000),
            rng.uniform(0.012, 0.09))
    t = seconds_axis(0.6)
    response = rng.standard_normal(len(t)) * np.exp(-t / 0.07) * envelope(t, 0.01, 1e9)
    diffuse = signal.fftconvolve(band(x, 200, 5000), band(response, 200, 5000))[: len(x)]
    return out + 0.035 * tail * unit(diffuse) * np.abs(x).max()


def stone_chip(rng, size):
    """A concrete or brick chip, `size` mm across, landing on hard ground."""
    return fragment(rng, float(np.clip(6500 * (5.0 / size) ** 0.7 * rng.uniform(0.8, 1.25), 2200, 11000)),
                    rng.uniform(0.0012, 0.003), 3)


def bullet_masonry(rng, take):
    seconds = 1.5
    out = np.zeros(int(seconds * SR))
    add(out, 0.8 * spike(rng), 0.0)
    # The air shoved aside by the strike and the spall, and the wall's face thumping with the blow.
    add(out, 0.9 * blast(rng, rng.uniform(0.0008, 0.0014)), 0.0001)
    add(out, 0.7 * structure(rng, 70, 450, 10, 0.03), 0.0003)
    # The crater: its "pock" and its brittle fracture, and the spall thrown out.
    pock = [(rng.uniform(380, 600), 1.0, 0.004), (rng.uniform(900, 1300), 0.6, 0.003),
            (rng.uniform(1900, 2800), 0.45, 0.002)]
    add(out, 0.45 * unit(modes(0.05, pock, 0.0002, rng)), 0.0002)
    add(out, 0.45 * crackle(rng, 0.05, int(rng.integers(40, 80)), 1500, 11000, 0.003), 0.0003)
    add(out, 0.4 * burst(rng, 0.2, 800, 8000, 0.001, 0.025), 0.0005)
    # Grit and chips raining down from where it hit (0.3-1.5 m up), bouncing at a third of their speed.
    grit = falling(rng, int(rng.integers(200, 400)), (0.3, 1.5), (0.3, 1.0), 0.25, 1)
    add(out, 0.08 * patter(rng, seconds, grit, 2500, 10000), 0.0)
    hits = falling(rng, int(rng.integers(10, 24)), (0.3, 1.5), (0.5, 2.5), 0.3, 2)
    sizes = rng.lognormal(np.log(4.0), 0.5, len(hits))
    add(out, debris(rng, seconds, hits, sizes / 8.0, lambda r, s: stone_chip(r, s * 8.0), 0.16), 0.0)
    if take == 3:
        add(out, 0.4 * ricochet(rng, 0.9), rng.uniform(0.002, 0.006))
    return surroundings(rng, out)


def bullet_tile(rng, take):
    seconds = 1.3
    out = np.zeros(int(seconds * SR))
    add(out, 0.9 * spike(rng, 0.00008), 0.0)
    add(out, 0.7 * blast(rng, rng.uniform(0.0006, 0.001)), 0.0001)
    add(out, 0.5 * structure(rng, 90, 500, 10, 0.025), 0.0003)
    ring = [(rng.uniform(2100, 2700), 1.0, 0.006), (rng.uniform(3300, 3900), 0.6, 0.004),
            (rng.uniform(4800, 5600), 0.4, 0.003), (rng.uniform(700, 1000), 0.5, 0.003)]
    add(out, 0.4 * unit(modes(0.05, ring, 0.0001, rng)), 0.0002)
    add(out, 0.6 * crackle(rng, 0.04, int(rng.integers(40, 70)), 2500, 14000, 0.002), 0.0002)
    add(out, 0.3 * burst(rng, 0.15, 1500, 10000, 0.0008, 0.018), 0.0004)
    grit = falling(rng, int(rng.integers(100, 200)), (0.3, 1.4), (0.3, 1.0), 0.3, 1)
    add(out, 0.08 * patter(rng, seconds, grit, 3500, 12000), 0.0)
    hits = falling(rng, int(rng.integers(14, 30)), (0.3, 1.4), (0.5, 2.5), 0.35, 2)
    sizes = rng.lognormal(np.log(5.0), 0.5, len(hits))
    chip = lambda r, s: fragment(r, float(np.clip(5200 * (5.0 / s) ** 0.7 * r.uniform(0.85, 1.2), 2500, 12000)),
                                 r.uniform(0.002, 0.006), 3)
    add(out, debris(rng, seconds, hits, sizes / 8.0, lambda r, s: chip(r, s * 8.0), 0.2), 0.0)
    return surroundings(rng, out)


def bullet_metal(rng, take):
    seconds = 1.3
    out = np.zeros(int(seconds * SR))
    add(out, 0.9 * spike(rng, 0.00007), 0.0)
    add(out, 0.6 * blast(rng, rng.uniform(0.0005, 0.0009)), 0.0001)
    # A heavy steel plate or body: its bending modes from the low hundreds up, the high ones dying first, and the
    # strong "ping" of the modes round the strike.
    freqs = np.exp(rng.uniform(np.log(120), np.log(9000), 26))
    plate = [(f, (f / 1000) ** -0.15 * rng.lognormal(0, 0.35), float(np.clip(0.18 * (500 / f) ** 0.6, 0.02, 0.28)))
             for f in freqs]
    add(out, 0.75 * unit(modes(1.0, plate, 0.00005, rng)), 0.0001)
    base = rng.uniform(1100, 1700)
    ping = [(base * r * rng.uniform(0.98, 1.02), r ** -0.5, 0.25 * r ** -0.8) for r in (1.0, 1.58, 2.13, 2.71, 3.4)]
    add(out, 0.55 * unit(modes(1.0, ping, 0.00005, rng)), 0.0001)
    # Lead and jacket splashing off it, and a few fragments ticking off whatever is nearby.
    add(out, 0.4 * crackle(rng, 0.05, int(rng.integers(30, 60)), 2500, 13000, 0.004), 0.0003)
    ticks = falling(rng, int(rng.integers(3, 8)), (0.2, 1.2), (0.5, 2.0), 0.4, 1, 0.05)
    lead = lambda r, s: fragment(r, r.uniform(2500, 6000), r.uniform(0.001, 0.003), 2)
    add(out, debris(rng, seconds, ticks, np.ones(len(ticks)), lead, 0.1), 0.0)
    if take in (1, 4):
        add(out, 0.45 * ricochet(rng, 0.9), rng.uniform(0.002, 0.005))
    return surroundings(rng, out, 0.8, 0.8)


def bullet_sheetmetal(rng, take):
    seconds = 0.9
    out = np.zeros(int(seconds * SR))
    add(out, 0.9 * spike(rng, 0.00008), 0.0)
    add(out, 0.5 * blast(rng, rng.uniform(0.0006, 0.001)), 0.0001)
    # The puncture tearing through, then the thin sheet's dense modes.
    add(out, 0.7 * crackle(rng, 0.03, int(rng.integers(20, 40)), 2000, 12000, 0.0015), 0.0002)
    freqs = np.exp(rng.uniform(np.log(90), np.log(7000), 40))
    sheet = [(f, (f / 300) ** -0.3 * rng.lognormal(0, 0.4), float(np.clip(0.2 * (300 / f) ** 0.5, 0.02, 0.3)))
             for f in freqs]
    add(out, 0.75 * unit(modes(0.8, sheet, 0.0002, rng)), 0.0002)
    # The panel's lowest modes beating (the wobble), and its rattle against its fixings.
    low = rng.uniform(60, 110)
    add(out, 0.2 * unit(modes(0.6, [(low, 1.0, 0.18), (low * rng.uniform(1.04, 1.09), 0.8, 0.15)], 0.002, rng)),
        0.001)
    rattle_t = seconds_axis(0.25)
    gate = (np.sin(2 * np.pi * rng.uniform(55, 90) * rattle_t) > 0.6).astype(float)
    rattle = noise(rng, len(rattle_t), 1500, 6000) * gate * envelope(rattle_t, 0.01, 0.07)
    add(out, 0.12 * rattle, 0.005)
    return surroundings(rng, out, 0.8, 0.8)


def glass_fragment(rng, size):
    f = float(np.clip(9000 * (5.0 / size) ** 0.8 * rng.uniform(0.8, 1.25), 3000, 15000))
    return fragment(rng, f, 0.04 * (4000 / f) ** 0.5, 4)


def bullet_glass(rng, take):
    seconds = 1.3
    out = np.zeros(int(seconds * SR))
    add(out, 1.0 * spike(rng, 0.00006), 0.0)
    add(out, 0.5 * blast(rng, rng.uniform(0.0005, 0.0008)), 0.0001)
    add(out, 0.7 * burst(rng, 0.04, 2000, 16000, 0.0001, 0.0008), 0.0)
    # Cracks running out from the hole at ~1500 m/s, a burst of tiny fractures over a few ms. The pane thumps and
    # rings, and fragments fall out of the hole.
    add(out, 0.55 * crackle(rng, 0.03, int(rng.integers(50, 90)), 3000, 15000, 0.0025), 0.0002)
    add(out, 0.45 * structure(rng, 80, 600, 10, 0.03), 0.0003)
    pane = [(rng.uniform(1800, 2600), 1.0, 0.03), (rng.uniform(3500, 4500), 0.7, 0.02),
            (rng.uniform(5500, 6800), 0.45, 0.015)]
    add(out, 0.3 * unit(modes(0.2, pane, 0.0001, rng)), 0.0002)
    grit = falling(rng, int(rng.integers(80, 160)), (0.4, 1.2), (0.0, 1.2), 0.3, 1)
    add(out, 0.06 * patter(rng, seconds, grit, 5000, 15000), 0.0)
    hits = falling(rng, int(rng.integers(25, 50)), (0.4, 1.2), (0.0, 1.5), 0.3, 2)
    sizes = rng.lognormal(np.log(4.0), 0.6, len(hits))
    add(out, debris(rng, seconds, hits, sizes / 8.0, lambda r, s: glass_fragment(r, s * 8.0), 0.22), 0.0)
    return surroundings(rng, out)


def bullet_wood(rng, take):
    seconds = 1.0
    out = np.zeros(int(seconds * SR))
    add(out, 0.7 * spike(rng, 0.00012), 0.0)
    add(out, 0.7 * blast(rng, rng.uniform(0.0008, 0.0014)), 0.0001)
    # The member's modes (a beam's ratios), damped as wood is (Q ~ 25), and the face of a door or a wall of boards.
    f1 = rng.uniform(110, 240)
    ratios = [1.0, 2.76, 5.4, 8.9, 13.3]
    member = [(f1 * r * rng.uniform(0.95, 1.05), r ** -0.35, 25 / (np.pi * f1 * r)) for r in ratios]
    add(out, 0.7 * unit(modes(0.4, member, 0.0003, rng)), 0.0002)
    add(out, 0.5 * burst(rng, 0.05, 300, 4000, 0.0003, 0.003), 0.0)
    # Fibres splintering, then a few splinters landing: soft and dull.
    add(out, 0.55 * crackle(rng, 0.04, int(rng.integers(20, 45)), 1500, 10000, 0.004), 0.0005)
    hits = falling(rng, int(rng.integers(4, 11)), (0.3, 1.4), (0.5, 2.0), 0.25, 1)
    splinter = lambda r, s: fragment(r, r.uniform(1500, 4000), r.uniform(0.0006, 0.0015), 2)
    add(out, debris(rng, seconds, hits, np.ones(len(hits)), splinter, 0.08), 0.0)
    return surroundings(rng, out, 0.9, 0.9)


def bullet_plastic(rng, take):
    seconds = 0.7
    out = np.zeros(int(seconds * SR))
    add(out, 0.5 * spike(rng, 0.00012), 0.0)
    add(out, 0.5 * blast(rng, rng.uniform(0.0008, 0.0012)), 0.0001)
    f1 = rng.uniform(100, 220)
    shell = [(f1 * r * rng.uniform(0.95, 1.05), r ** -0.4, 0.03 / r ** 0.7) for r in (1.0, 1.9, 2.8, 4.1, 5.5)]
    add(out, 0.8 * unit(modes(0.3, shell, 0.0004, rng)), 0.0002)
    add(out, 0.7 * burst(rng, 0.03, 1000, 9000, 0.0002, 0.0015), 0.0)
    add(out, 0.35 * crackle(rng, 0.02, int(rng.integers(8, 20)), 1500, 9000, 0.002), 0.0003)
    hits = falling(rng, int(rng.integers(1, 4)), (0.3, 1.0), (0.5, 1.5), 0.3, 1)
    chip = lambda r, s: fragment(r, r.uniform(1500, 4000), r.uniform(0.001, 0.002), 2)
    add(out, debris(rng, seconds, hits, np.ones(len(hits)), chip, 0.08), 0.0)
    return surroundings(rng, out, 0.8, 0.8)


def bullet_dirt(rng, take):
    seconds = 1.0
    out = np.zeros(int(seconds * SR))
    # The soil gives: a thud and the air pushed out with the spray, no crack.
    t = seconds_axis(0.08)
    add(out, 0.8 * np.sin(2 * np.pi * rng.uniform(110, 190) * t) * envelope(t, 0.0015, 0.012), 0.0)
    add(out, 0.8 * blast(rng, rng.uniform(0.0015, 0.0025)), 0.0)
    add(out, 0.8 * burst(rng, 0.25, 200, 2500, 0.002, 0.04), 0.001)
    # Soil thrown up raining back down (from the ground, so it falls for twice its rise), and a pebble or two.
    soil = falling(rng, int(rng.integers(150, 300)), (0.0, 0.1), (1.3, 0.7), 0.0, 0)
    add(out, 0.08 * patter(rng, seconds, soil, 1000, 6000, 0.8), 0.0)
    add(out, dust(rng, seconds, soil, 1000, 5000, 0.04), 0.0)
    pebbles = falling(rng, int(rng.integers(2, 6)), (0.0, 0.1), (2.0, 1.0), 0.3, 1)
    pebble = lambda r, s: fragment(r, r.uniform(2500, 5500), r.uniform(0.001, 0.002), 2)
    add(out, debris(rng, seconds, pebbles, np.ones(len(pebbles)), pebble, 0.1), 0.0)
    return surroundings(rng, out, 0.7, 0.6)


def bullet_grass(rng, take):
    seconds = 0.9
    out = np.zeros(int(seconds * SR))
    t = seconds_axis(0.08)
    add(out, 0.7 * np.sin(2 * np.pi * rng.uniform(100, 170) * t) * envelope(t, 0.002, 0.012), 0.0)
    add(out, 0.7 * blast(rng, rng.uniform(0.0015, 0.0025)), 0.0)
    add(out, 0.6 * burst(rng, 0.25, 200, 2500, 0.002, 0.035), 0.001)
    # The blades flicking and a few stems snapping.
    rustle_t = seconds_axis(0.3)
    flicks = unit(band(rng.standard_normal(len(rustle_t)), 0, 60)) ** 2
    add(out, 0.35 * noise(rng, len(rustle_t), 1500, 10000) * (0.4 + flicks) * envelope(rustle_t, 0.004, 0.05), 0.0)
    add(out, 0.25 * crackle(rng, 0.05, int(rng.integers(3, 9)), 2000, 7000, 0.01), 0.0)
    soil = falling(rng, int(rng.integers(60, 150)), (0.0, 0.1), (1.2, 0.6), 0.0, 0)
    add(out, 0.07 * patter(rng, seconds, soil, 1000, 6000, 0.8), 0.0)
    return surroundings(rng, out, 0.7, 0.6)


def bullet_fabric(rng, take):
    """Cloth, a cushion, a sandbag, cardboard: the round snaps through the face, and what's behind it thuds."""
    seconds = 0.5
    out = np.zeros(int(seconds * SR))
    add(out, 0.7 * burst(rng, 0.03, 1000, 6000, 0.0001, 0.0015), 0.0)
    add(out, 0.7 * blast(rng, rng.uniform(0.0012, 0.002)), 0.0001)
    t = seconds_axis(0.1)
    add(out, 0.35 * np.sin(2 * np.pi * rng.uniform(120, 200) * t) * envelope(t, 0.0015, 0.012), 0.0003)
    add(out, 0.6 * burst(rng, 0.08, 150, 700, 0.001, 0.01), 0.0003)
    flutter_t = seconds_axis(0.06)
    flutter = noise(rng, len(flutter_t), 400, 3000) * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(60, 130) * flutter_t))
    add(out, 0.45 * flutter * envelope(flutter_t, 0.001, 0.012), 0.001)
    add(out, 0.4 * burst(rng, 0.15, 300, 3000, 0.002, 0.03), 0.002)
    return surroundings(rng, out, 0.6, 0.5)


def bullet_flesh(rng, take):
    """A bullet into a body: the "thwack" people describe. The uniform's cloth snaps, the skin slaps, and the body
    thuds under it; there's no ring and no debris."""
    seconds = 0.4
    out = np.zeros(int(seconds * SR))
    add(out, 0.4 * burst(rng, 0.02, 2000, 7000, 0.00005, 0.0008), 0.0)
    add(out, 1.0 * burst(rng, 0.08, 400, 4000, 0.0002, 0.007), 0.0002)
    add(out, 0.5 * burst(rng, 0.03, 800, 2500, 0.0001, 0.003), 0.0004)
    add(out, 0.6 * blast(rng, rng.uniform(0.0012, 0.002)), 0.0002)
    t = seconds_axis(0.15)
    f = rng.uniform(150, 260)
    add(out, 0.45 * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2.1 * f * t)) * envelope(t, 0.001, 0.014),
        0.0005)
    add(out, 0.7 * burst(rng, 0.08, 300, 1000, 0.0008, 0.01), 0.0004)
    add(out, 0.4 * np.sin(2 * np.pi * rng.uniform(70, 110) * t) * envelope(t, 0.002, 0.025), 0.001)
    add(out, 0.35 * burst(rng, 0.1, 200, 1200, 0.002, 0.015), 0.003)
    return surroundings(rng, out, 0.5, 0.4)


BULLETS = {
    "masonry": bullet_masonry,
    "tile": bullet_tile,
    "metal": bullet_metal,
    "sheetmetal": bullet_sheetmetal,
    "glass": bullet_glass,
    "wood": bullet_wood,
    "plastic": bullet_plastic,
    "dirt": bullet_dirt,
    "grass": bullet_grass,
    "fabric": bullet_fabric,
    "flesh": bullet_flesh,
}


# ----------------------------------------------------------------------------------------------------------------------
# Footsteps

def slap(rng, low, high, tau, brightness=1.0):
    """The rubber sole slapping the floor: a noise burst, brighter the harder it comes down."""
    return burst(rng, 0.06, low, high * brightness, 0.0004, tau)


def knock(rng, low, high, tau):
    """The heel's rubber and the leg behind it compressing: a short, damped low-mid knock, the body of a footstep."""
    return burst(rng, 0.08, low, high, 0.0008, tau)


def thump(rng, low, high, tau):
    """The leg's weight arriving through the sole: a damped low sine."""
    t = seconds_axis(0.12)
    return np.sin(2 * np.pi * rng.uniform(low, high) * t) * envelope(t, 0.0012, tau)


def floor_contact(rng, floor, force, brightness):
    """One part of the sole meeting `floor`, with `force` against a walk's heel strike."""
    parts = np.zeros(int(0.5 * SR))
    if floor == "concrete":
        add(parts, 0.75 * slap(rng, 120, 1500, 0.0035, brightness), 0.0)
        add(parts, 0.85 * knock(rng, 150, 650, 0.007), 0.0)
        add(parts, 0.4 * thump(rng, 110, 170, 0.008), 0.0)
        add(parts, 0.12 * burst(rng, 0.01, 2000, 6000, 0.0001, 0.0007), 0.0)
        add(parts, 0.1 * crackle(rng, 0.05, int(rng.integers(6, 15)), 3000, 9000, 0.008), 0.0005)
    elif floor == "tile":
        add(parts, 0.8 * slap(rng, 150, 2500, 0.003, brightness), 0.0)
        add(parts, 0.65 * knock(rng, 180, 750, 0.006), 0.0)
        add(parts, 0.25 * burst(rng, 0.01, 2500, 8000, 0.0001, 0.0006), 0.0)
        ring = [(rng.uniform(2000, 2600), 1.0, 0.006), (rng.uniform(3200, 3800), 0.5, 0.004)]
        add(parts, 0.12 * unit(modes(0.05, ring, 0.0002, rng)), 0.0)
        add(parts, 0.3 * thump(rng, 120, 180, 0.008), 0.0)
        add(parts, 0.06 * crackle(rng, 0.03, int(rng.integers(3, 8)), 3500, 10000, 0.006), 0.0005)
    elif floor == "wood":
        add(parts, 0.7 * slap(rng, 120, 1500, 0.004, brightness), 0.0)
        # Floorboards over joists: the board's modes, hollow and short.
        f1 = rng.uniform(95, 140)
        board = [(f1, 1.0, 0.07), (f1 * rng.uniform(2.2, 2.5), 0.8, 0.05), (f1 * rng.uniform(3.9, 4.4), 0.6, 0.03),
                 (f1 * rng.uniform(6.5, 7.2), 0.35, 0.018), (f1 * rng.uniform(10, 11.5), 0.15, 0.01)]
        add(parts, 0.75 * unit(modes(0.4, board, 0.002, rng)), 0.0)
        add(parts, 0.45 * knock(rng, 150, 600, 0.008), 0.0)
        add(parts, 0.3 * thump(rng, 100, 150, 0.012), 0.0)
    elif floor == "metal":
        add(parts, 0.75 * slap(rng, 150, 2000, 0.003, brightness), 0.0)
        # A steel deck plate: its modes ring on under the boot, which damps them a little.
        freqs = np.exp(rng.uniform(np.log(70), np.log(4000), 16))
        plate = [(f, (f / 300) ** -0.4 * rng.lognormal(0, 0.3), float(np.clip(0.18 * (300 / f) ** 0.5, 0.03, 0.25)))
                 for f in freqs]
        add(parts, 0.55 * unit(modes(0.5, plate, 0.0005, rng)), 0.0)
        add(parts, 0.5 * knock(rng, 150, 650, 0.006), 0.0)
        add(parts, 0.35 * thump(rng, 110, 160, 0.01), 0.0)
        add(parts, 0.06 * crackle(rng, 0.03, int(rng.integers(4, 10)), 3000, 9000, 0.006), 0.0005)
    elif floor == "dirt":
        add(parts, 0.5 * slap(rng, 100, 900, 0.006, 1.0), 0.0)
        add(parts, 0.65 * knock(rng, 150, 550, 0.01), 0.0)
        add(parts, 0.35 * thump(rng, 100, 140, 0.012), 0.0)
        # The soil's grains shifting and crushing under the lugs, and a pebble or two.
        add(parts, 0.45 * crackle(rng, 0.15, int(rng.integers(25, 60)), 400, 5000, 0.025, 0.8), 0.001)
        for _ in range(int(rng.integers(0, 3))):
            add(parts, 0.12 * fragment(rng, rng.uniform(2500, 5000), rng.uniform(0.001, 0.002), 2),
                rng.uniform(0.0, 0.03))
    elif floor == "grass":
        add(parts, 0.35 * slap(rng, 80, 600, 0.008, 1.0), 0.0)
        # The turf giving under the heel: a soft, low-mid thud.
        add(parts, 0.7 * knock(rng, 150, 900, 0.012), 0.0)
        add(parts, 0.35 * thump(rng, 100, 140, 0.014), 0.0)
        # The blades swishing as the boot pushes through them, and a few stems snapping.
        t = seconds_axis(0.3)
        flicks = unit(band(rng.standard_normal(len(t)), 0, 80)) ** 2
        add(parts, 0.55 * noise(rng, len(t), 1500, 11000) * (0.35 + flicks) * envelope(t, 0.015, 0.06), 0.0)
        add(parts, 0.08 * crackle(rng, 0.06, int(rng.integers(2, 7)), 2000, 6000, 0.015), 0.002)
    return parts * force


SCUFF_BANDS = {"concrete": (600, 4000), "tile": (800, 5000), "wood": (400, 3000), "metal": (700, 4500),
               "dirt": (500, 4500), "grass": (1000, 6000)}


def scuff(rng, floor, force, seconds):
    """The sole twisting and pushing off: friction noise, gritty on hard floors."""
    t = seconds_axis(seconds + 0.05)
    low, high = SCUFF_BANDS[floor]
    grit = 0.5 + unit(np.abs(band(rng.standard_normal(len(t)), 0, 300)))
    return force * noise(rng, len(t), low, high) * grit * envelope(t, seconds * 0.4, seconds * 0.35)


def rattle(rng, count, spread):
    """Kit on the move: magazines knocking in their pouches, the sling's swivels and clips."""
    out = np.zeros(int((spread + 0.1) * SR))
    for _ in range(count):
        piece = fragment(rng, rng.uniform(1800, 5500), rng.uniform(0.002, 0.006), 2)
        add(out, rng.lognormal(-0.3, 0.4) * piece, rng.uniform(0, spread))
    return out


def rustle(rng, seconds, level):
    """Trouser legs and sleeves brushing."""
    t = seconds_axis(seconds)
    return level * noise(rng, len(t), 600, 5000) * envelope(t, seconds * 0.3, seconds * 0.35)


def footstep(rng, floor, kind):
    seconds = {"step": 0.5, "run": 0.45, "land": 0.8}[kind]
    out = np.zeros(int(seconds * SR))
    if kind == "step":
        add(out, floor_contact(rng, floor, 1.0, 1.0), 0.0)
        add(out, floor_contact(rng, floor, 0.5, 0.9), rng.uniform(0.07, 0.11))
        add(out, scuff(rng, floor, 0.1, rng.uniform(0.04, 0.07)), rng.uniform(0.16, 0.22))
        add(out, rustle(rng, 0.15, 0.03), 0.0)
        if floor == "wood" and rng.random() < 0.3:
            add(out, 0.12 * creak(rng, rng.uniform(0.1, 0.2)), rng.uniform(0.03, 0.08))
    elif kind == "run":
        add(out, floor_contact(rng, floor, 1.0, 1.25), 0.0)
        add(out, floor_contact(rng, floor, 0.55, 1.1), rng.uniform(0.012, 0.03))
        add(out, scuff(rng, floor, 0.22, rng.uniform(0.05, 0.08)), rng.uniform(0.08, 0.12))
        add(out, 0.12 * rattle(rng, int(rng.integers(2, 5)), 0.07), 0.02)
        add(out, rustle(rng, 0.2, 0.06), 0.0)
    else:
        second = rng.uniform(0.015, 0.045)
        for at, force in ((0.0, 1.0), (second, 0.85)):
            add(out, floor_contact(rng, floor, force, 1.2), at)
            add(out, floor_contact(rng, floor, force * 0.5, 1.1), at + rng.uniform(0.01, 0.02))
        # The body's weight coming down through both legs: a low thump, which a hollow floor carries most.
        body = {"wood": 0.8, "metal": 0.6, "tile": 0.35, "concrete": 0.3, "dirt": 0.45, "grass": 0.4}[floor]
        t = seconds_axis(0.2)
        add(out, body * np.sin(2 * np.pi * rng.uniform(70, 110) * t) * envelope(t, 0.004, 0.025), 0.008)
        add(out, scuff(rng, floor, 0.15, rng.uniform(0.04, 0.06)), rng.uniform(0.06, 0.1))
        add(out, 0.1 * rattle(rng, int(rng.integers(4, 9)), 0.14), 0.01)
        add(out, rustle(rng, 0.25, 0.1), 0.0)
    return out


def creak(rng, seconds):
    """A floorboard creaking under the weight: wood sliding on a nail, stick-slip at a wandering rate."""
    t = seconds_axis(seconds)
    rate = rng.uniform(180, 320) * (1 + 0.25 * np.sin(2 * np.pi * rng.uniform(2, 5) * t))
    train = np.zeros(len(t))
    phase = np.cumsum(rate) / SR
    train[np.nonzero(np.diff(np.floor(phase)) > 0)[0]] = 1.0
    body = band(train, 400, 2400)
    return unit(body) * envelope(t, seconds * 0.3, seconds * 0.4)


# ----------------------------------------------------------------------------------------------------------------------
# Menus

def ui_button_press(rng):
    """A sealed tactile push-button: the steel dome snapping through, the plunger bottoming out a few ms later, and the
    housing's small thump."""
    seconds = 0.12
    out = np.zeros(int(seconds * SR))
    add(out, 1.2 * burst(rng, 0.01, 3500, 11000, 0.0001, 0.0006), 0.0)
    dome = [(rng.uniform(3900, 4400), 1.0, 0.004), (rng.uniform(6200, 6900), 0.5, 0.0025),
            (rng.uniform(8800, 9600), 0.25, 0.0015)]
    add(out, 0.6 * unit(modes(0.03, dome, 0.0001, rng)), 0.0002)
    bottom = [(rng.uniform(1300, 1600), 1.0, 0.006), (rng.uniform(2700, 3100), 0.5, 0.004)]
    at = rng.uniform(0.004, 0.006)
    add(out, 0.35 * burst(rng, 0.01, 1500, 6000, 0.0001, 0.0008), at)
    add(out, 0.45 * unit(modes(0.04, bottom, 0.0002, rng)), at)
    t = seconds_axis(0.05)
    add(out, 0.15 * np.tanh(2 * np.sin(2 * np.pi * rng.uniform(180, 240) * t) * envelope(t, 0.0008, 0.006)), at)
    return out


def ui_button_hover(rng):
    """A rotary switch's detent: a single faint tick of its spring and ball."""
    seconds = 0.05
    out = np.zeros(int(seconds * SR))
    add(out, 1.0 * burst(rng, 0.01, 4000, 12000, 0.00005, 0.0003), 0.0)
    detent = [(rng.uniform(2600, 3000), 1.0, 0.0025), (rng.uniform(5200, 5800), 0.4, 0.0015)]
    add(out, 0.5 * unit(modes(0.02, detent, 0.0001, rng)), 0.0001)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# Output

def finish(x, drive=1.3):
    """No rumble under 35 Hz, soft clipping (`drive`) so the strike's peak doesn't set the level, -1 dBFS peaks, the
    silent tail cut and faded so it can't click."""
    x = signal.sosfilt(signal.butter(2, 35, btype="highpass", fs=SR, output="sos"), x)
    x = np.tanh(drive * unit(x)) / np.tanh(drive)
    x = unit(x) * 10 ** (-1 / 20)
    audible = np.nonzero(np.abs(x) > 10 ** (-66 / 20))[0]
    end = min(len(x), audible[-1] + int(0.01 * SR))
    x = x[:end].copy()
    fade = min(int(0.015 * SR), len(x) // 4)
    x[-fade:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, fade))
    return x


def write_wav(path, x):
    pcm = np.round(np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def falloff(distance, reference):
    """The inverse-distance law over the event's distance, as GunshotAudio.FalloffFor makes it: full level out to
    `reference` units, then reference / r in linear steps half an octave apart, easing to silence over the last tenth."""
    frames = [{"x": 0.0, "y": 1.0, "in": 0, "out": 0, "mode": "Linear"}]
    r = float(reference)
    while r < distance * 0.9:
        frames.append({"x": round(r / distance, 5), "y": round(reference / r, 5), "in": 0, "out": 0, "mode": "Linear"})
        r *= np.sqrt(2.0)
    frames.append({"x": 0.9, "y": round(reference / (distance * 0.9), 5), "in": 0, "out": 0, "mode": "Linear"})
    frames.append({"x": 1.0, "y": 0.0, "in": 0, "out": 0, "mode": "Linear"})
    return frames


def write_event(folder, sound_path, name, takes, volume, spread_db, pitch, distance=None, reference=None):
    """A .sound event picking one take at random: 2D on the UI mixer when there's no distance, else 3D with the
    inverse-distance falloff, air absorption and occlusion. `spread_db` is how much quieter a play may come out."""
    path = os.path.join(folder, name + ".sound")
    if os.path.exists(path):
        return False
    low = volume * 10 ** (-spread_db / 20)
    event = {
        "UI": distance is None,
        "Volume": f"{low:.4f} {volume:.4f}" if spread_db > 0 else f"{volume:.4f}",
        "Pitch": pitch,
        "Decibels": 70,
        "SelectionMode": "Random",
        "Sounds": [f"{sound_path}/{take}.vsnd" for take in takes],
        "Occlusion": distance is not None,
        "AirAbsorption": distance is not None,
        "Transmission": distance is not None,
        "OcclusionRadius": 64 if distance is None else 32,
        "DistanceAttenuation": distance is not None,
    }
    if distance is None:
        event["DefaultMixer"] = UI_MIXER
    else:
        event["Distance"] = distance
        event["Falloff"] = falloff(distance, reference)
    event["__references"] = []
    event["__version"] = 1
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(event, f, indent=2)
        f.write("\n")
    return True


def level(takes, target):
    """Every take as loud as the quietest, and the event volume that puts them at `target`."""
    quietest = min(loudness(x) for x in takes)
    takes = [x * 10 ** ((quietest - loudness(x)) / 20) for x in takes]
    return takes, min(1.0, 10 ** ((target - quietest) / 20))


def build_set(name, make, count, seed, target, drive=1.3):
    takes = [finish(make(np.random.default_rng(seed + i), i), drive) for i in range(count)]
    takes, volume = level(takes, target)
    names = [f"{name}_{i + 1:02d}" for i in range(count)]
    return names, takes, volume


def sets():
    """Every set: (folder, sound path, event name, take names, takes, volume, volume spread in dB, pitch, distance,
    reference)."""
    out = []
    folder = os.path.join(ASSETS, "sounds", "world", "impacts")
    for index, (material, (target, distance, count)) in enumerate(IMPACTS.items()):
        names, takes, volume = build_set(f"bullet_{material}", BULLETS[material], count, 1000 + 100 * index, target,
                                         IMPACT_DRIVE)
        out.append((folder, "sounds/world/impacts", f"bullet_{material}", names, takes, volume, 1.5, "0.95 1.05",
                    distance, IMPACT_REFERENCE))
    folder = os.path.join(ASSETS, "sounds", "world", "footsteps")
    for index, (floor, walk) in enumerate(FLOORS.items()):
        for kind, count, target, distance, offset in (
                ("step", STEP_TAKES, walk, STEP_DISTANCE, 0),
                ("run", RUN_TAKES, walk + RUN_OVER_WALK, RUN_DISTANCE, 30),
                ("land", LAND_TAKES, walk + RUN_OVER_WALK + LAND_OVER_RUN, LAND_DISTANCE, 60)):
            make = lambda rng, i, floor=floor, kind=kind: footstep(rng, floor, kind)
            names, takes, volume = build_set(f"{kind}_{floor}", make, count, 5000 + 100 * index + offset, target)
            out.append((folder, "sounds/world/footsteps", f"{kind}_{floor}", names, takes, volume, 2.0, "0.96 1.04",
                        distance, STEP_REFERENCE))
    folder = os.path.join(ASSETS, "sounds", "ui", "menu")
    for index, (name, target) in enumerate(UI_TARGETS.items()):
        make = ui_button_press if name == "ui_button_press" else ui_button_hover
        names, takes, volume = build_set(name, lambda rng, i, make=make: make(rng), UI_TAKES, 9000 + 100 * index,
                                         target)
        out.append((folder, "sounds/ui/menu", name, names, takes, volume, 0.0, "0.98 1.02", None, None))
    return out


def describe(name, takes, volume):
    lengths = [len(x) / SR for x in takes]
    spectrum = sum(np.abs(np.fft.rfft(x, 1 << 16)) for x in takes)
    freqs = np.fft.rfftfreq(1 << 16, 1 / SR)
    centroid = np.sum(spectrum * freqs) / np.sum(spectrum)
    print(f"{name}: {len(takes)} takes, {min(lengths):.2f}-{max(lengths):.2f} s, loudness {loudness(takes[0]):.1f} dB, "
          f"volume {volume:.4f} ({loudness(takes[0] * volume):.1f} dB), centroid {centroid:.0f} Hz")


# ----------------------------------------------------------------------------------------------------------------------
# s&box's stock sounds, for --compare

STOCK = {
    "bullet_masonry": "sounds/impacts/bullets/impact-bullet-generic.sound",
    "bullet_tile": "sounds/impacts/bullets/impact-bullet-glass.sound",
    "bullet_metal": "sounds/impacts/bullets/impact-bullet-metal.sound",
    "bullet_sheetmetal": "sounds/impacts/bullets/impact-bullet-metal.sound",
    "bullet_glass": "sounds/impacts/bullets/impact-bullet-glass.sound",
    "bullet_wood": "sounds/impacts/bullets/impact-bullet-wood.sound",
    "bullet_plastic": "sounds/impacts/bullets/impact-bullet-plastic.sound",
    "bullet_dirt": "sounds/impacts/melee/impact-melee-dirt.sound",
    "bullet_grass": "sounds/impacts/melee/impact-melee-grass.sound",
    "bullet_fabric": "sounds/impacts/bullets/impact-bullet-plaster.sound",
    "bullet_flesh": "sounds/impacts/melee/impact-melee-flesh.sound",
    "step_concrete": "sounds/footsteps/footstep-concrete.sound",
    "step_tile": "sounds/footsteps/footstep-concrete.sound",
    "step_wood": "sounds/footsteps/footstep-wood.sound",
    "step_metal": "sounds/footsteps/footstep-metal.sound",
    "step_dirt": "sounds/footsteps/footstep-dirt.sound",
    "step_grass": "sounds/footsteps/footstep-grass.sound",
    "land_concrete": "sounds/footsteps/footstep-concrete-land.sound",
    "ui_button_press": "sounds/kenney/ui/ui.button.press.sound",
    "ui_button_hover": "sounds/kenney/ui/ui.button.over.sound",
}


def stock_event(path):
    """A compiled core event's takes and volume: its source JSON is kept in the _c."""
    import re
    data = open(os.path.join(SBOX_CORE, path + "_c"), "rb").read()
    source = json.loads(re.search(rb"\{.*\}", data, re.S).group().decode("utf-8", "replace"))
    volume = source.get("Volume", source.get("volume", 1))
    volume = float(str(volume).replace(",", " ").split()[0])
    return source.get("Sounds") or source.get("sounds"), volume


def stock_audio(vsnd):
    """A compiled vsnd's samples: the DATA block holds the rate, format and channels, and 16-bit PCM follows the
    header. None for other formats."""
    data = open(os.path.join(SBOX_CORE, vsnd + "_c"), "rb").read()
    head = struct.unpack("<I", data[:4])[0]
    block = data.find(b"DATA")
    offset = struct.unpack("<I", data[block + 4:block + 8])[0]
    info = data[block + 4 + offset:]
    rate, fmt, channels = struct.unpack("<HBB", info[:4])
    samples = struct.unpack("<I", info[8:12])[0]
    if fmt != 0:
        return None
    x = np.frombuffer(data[head:head + samples * 2 * channels], "<i2").astype(np.float64) / 32768
    x = x.reshape(-1, channels).mean(axis=1)
    if rate != SR:
        x = signal.resample_poly(x, SR, rate)
    return x


def gap(seconds):
    return np.zeros(int(seconds * SR))


def sequence(takes, volume, interval, count, rng):
    out = np.zeros(int((interval * count + 1.0) * SR))
    for i in range(count):
        add(out, takes[rng.integers(len(takes))] * volume, i * interval)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", help="write a WAV with every set's takes, walks, runs and bursts, levelled per set")
    parser.add_argument("--compare", help="write a WAV with s&box's stock sound, then the new one, for each set")
    parser.add_argument("--out", help="write the sounds under this folder instead of Assets (to try changes)")
    args = parser.parse_args()
    if args.out:
        global ASSETS
        ASSETS = args.out

    all_sets = sets()
    for folder, sound_path, name, names, takes, volume, spread, pitch, distance, reference in all_sets:
        os.makedirs(folder, exist_ok=True)
        for take_name, x in zip(names, takes):
            write_wav(os.path.join(folder, take_name + ".wav"), x)
        written = write_event(folder, sound_path, name, names, volume, spread, pitch, distance, reference)
        describe(name, takes, volume)
        if not written:
            print(f"  {name}.sound exists, left as it is")

    rng = np.random.default_rng(7)
    by_name = {s[2]: s for s in all_sets}

    if args.preview:
        parts = []
        for folder, sound_path, name, names, takes, volume, *_ in all_sets:
            section = []
            for x in takes:
                section += [x, gap(0.5)]
            if name.startswith("step_"):
                section += [sequence(takes, 1.0, 0.35, 8, rng)]
            elif name.startswith("run_"):
                section += [sequence(takes, 1.0, 0.25, 10, rng)]
            elif name.startswith("bullet_"):
                section += [sequence(takes, 1.0, 60 / 800, 5, rng)]
            parts += [unit(np.concatenate(section)) * 0.7, gap(1.0)]
        write_wav(args.preview, np.concatenate(parts))
        print(f"preview: {args.preview}")

    if args.compare:
        parts = []
        for name, stock in STOCK.items():
            sounds, stock_volume = stock_event(stock)
            old = [x for x in (stock_audio(s) for s in sounds[:2]) if x is not None]
            new = by_name[name]
            pair = [x * stock_volume for x in old] + [gap(0.6)] + [x * new[5] for x in new[4][:2]]
            spaced = []
            for x in pair:
                spaced += [x, gap(0.45)]
            parts += [unit(np.concatenate(spaced)) * 0.7, gap(1.2)]
            print(f"compare {name}: stock {stock} ({len(old)} takes) then new")
        write_wav(args.compare, np.concatenate(parts))
        print(f"compare: {args.compare}")


if __name__ == "__main__":
    main()
