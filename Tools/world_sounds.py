"""
World sounds modelled on the real thing, in place of s&box's stock ones: bullet impacts by material, a knife's strikes
by material and its swing, grenades' bounces by floor, a soldier's boot footsteps, running steps and landings by floor,
and the menus' button press and hover. They're synthesised from the physics of each event, so there are no samples, and
every figure here can be re-tuned.

    python Tools/world_sounds.py [--preview <wav>] [--compare <wav>] [--out <dir>]

Writes, with a .sound event for each set if it doesn't exist yet (an event may be tuned in the editor, so it isn't
overwritten; delete one to have it rewritten):
- Assets/sounds/world/impacts/bullet_<material>_<n>.wav: masonry, tile, metal, sheetmetal, glass, wood, plastic, dirt,
  grass, fabric and flesh;
- Assets/sounds/world/knife/knife_<material>_<n>.wav (the impacts' materials) and knife_swing_<n>.wav;
- Assets/sounds/world/grenades/{frag,can}_<floor>_<n>.wav: concrete, tile, wood, metal, dirt, grass and soft;
- Assets/sounds/world/footsteps/{step,run,land}_<floor>_<n>.wav: concrete, tile, wood, metal, dirt and grass;
- Assets/sounds/ui/menu/ui_button_{press,hover}_<n>.wav.
Code/World/WorldSounds.cs picks the impact, knife strike, bounce, step and landing for a surface. --preview writes every
take in a row, with walks, runs, bursts and bouncing grenades; --compare writes s&box's stock sound, then the new one,
for each set (decoded from the s&box install or the project's Assets, each pair at its events' volumes). --out writes
the sounds under another folder instead of Assets.

What each is, and why it sounds like it does:

Bullet impacts, heard close by (a 5.56 round at ~800 m/s). Every hard target has the strike (the bullet stops in tens of
microseconds: a pressure spike), the air it and the spray shove aside (a Friedlander pulse a millisecond or two wide), and
the struck body's own low modes, radiated from its whole face: a wall's or a door's thud, 70-500 Hz, which is most of
what makes an impact sound heavy. Then whatever the material does, and the surroundings: the ground's reflection a few ms
later, early reflections and a short diffuse tail, kept low (s&box plays a sound dry).
- masonry (concrete, brick, stone, plaster): the crater's "pock" and brittle fracture, a crackle over ~10 ms; spall
  thrown out, a short hiss; then grit and 10-24 chips falling from wherever the round hit (0.3-1.5 m up) and bouncing
  at a third of their speed, within about half a second.
- tile (ceramic, glazed): brighter and more brittle than concrete, with a short ceramic ring and harder chips.
- metal (steelwork: a deck, a bulkhead, a beam): a bright crack and a short clank. The plate's bending modes are dense
  and pitchless, and built into a structure they die fast (a loss factor of 1-2.5%, T60 ~0.1 s at 2 kHz), under a
  splash of lead and jacket fragments and the frame's brief thud. It used to ring like a
  steel target hung on chains (70% of its sound after the first 50 ms, a pitched ~1.4 kHz "ping" 0.25 s long), which
  in a steel hall under automatic fire sounded like table tennis.
- sheetmetal (a car panel, a tin roof): the puncture's crack and tear, then a thin sheet's dense modes, damped by the
  air, its fixings and its seams (a loss factor of 2-6%), a short wobble and a rattle against its fixings.
- glass (a pane that doesn't give way): the hole's sharp crack, cracks running out across the pane, the pane's thump and
  short ring, and fragments tinkling down.
- wood (a beam, a door, a crate): a hollow "thock" from the member's modes (110-240 Hz up, Q ~ 25), splintering fibres,
  a few splinters landing, soft and dull.
- plastic: a hollow shell's heavily damped modes and a dull crack.
- ricochet (not a material): a round glancing off a hard face, deformed and tumbling, flying away. Its wake buzzes at
  the tumble rate, Doppler-shifted down from the first moment as it recedes, and fades within ~0.15-0.2 s as it flies
  off and slows. WorldSounds.BulletRicochet plays it beside the impact only for a grazing hit (under ~15 degrees on
  steel, 10 on stone or tile), heard from tens of metres at most, 15 dB under the strike. One masonry take and one metal
  take in five used to carry a whine instead, a scream gliding down an octave over half a second (the movie "pyeeow",
  which needs the round to come at you and pass close), on any hit and wherever the impact carried: under fire it was
  heard as "pews" from across a hall.
- dirt: no crack: the soil gives, a low thud and the "pfft" of the spray, then soil pattering back down. Most of what's
  thrown up is dust, which lands unheard.
- grass: dirt's thud and spray, with the blades' rustle and a few stems snapping, and less soil in the air.
- fabric (and cardboard, a sandbag): a snap and a flutter as the round goes through, and what's behind it thudding.
- flesh: a bullet into a body, the "thwack" people describe: the uniform's cloth snapping, the skin's slap and the
  tissue's knock with the body's thud under it, with no ring and no debris.
Their octave spectra were compared with s&box's recordings of the same materials (real Foley), which showed the first
version had almost no low end. Most now follow them within about 6 dB from 125 Hz to 4 kHz. Dirt and grass are up to
9 dB brighter at 1-2 kHz, since s&box's are a melee blow's, not a round's spray.

A knife's strike (a slash or thrust lands with a few tens of joules, a bullet with over a thousand, so it barely moves a
wall): the steel tip's click, the blade's own ring (a ~17 cm blade's bending modes at a cantilever's ratios over
~110 Hz, damped by the fist within tens of ms, so only the upper ones carry: the "tink" of steel), the fist and handle
jolting to a stop, and what the tip does to the face: skating over stone or tile, a thick plate's "tang" ringing on, a
sheet booming and sometimes punched through, a pane's "tink" and short ring, the tip biting into wood (which grips the
blade, so it barely rings), soil and turf giving, cloth tearing. Into a body: the uniform punctured, the fist and guard
slapping it and its dull thud, far quieter than a round's hit (PlayerPawn plays it for a knifed player). They sit 9-12 dB
under the bullet impacts, and are heard by everyone nearby (Melee broadcasts them).
The swing: vortices shed off the blade's spine as it cuts the air at 12-18 m/s (Strouhal, 0.2 v / 4 mm: ~750 Hz at
15 m/s), a band of noise whose pitch follows the blade's speed and whose pressure goes as its cube (aeolian dipole
sound), the edge's finer vortices two octaves up, the arm's low whump and the sleeve and kit. It's about as loud as a
walking step on concrete. The old swing was 19 dB louder, a bullet impact's level, heard to 5000 units.

Grenade bounces, at ~6 m/s (a harder landing plays louder, WorldSounds.BounceVolume, as speed^1.2: Hertz contact):
- frag: an M67, a 64 mm steel sphere filled with Composition B, which damps its shell modes to a dull clunk, and its
  fuze's striker ticking.
- can: smoke, stun and thermite grenades, a thin sheet-steel can: a hollow tonk (modes from 700-1000 Hz) that rings a
  little longer, and its lid and fuze rattling.
Then the floor: on concrete a click from the ~0.2 ms steel-on-stone contact and the slab's dull knock, on tile its
glazed ring, a steel deck's bright clank (the loudest, damped within ~0.1 s by the structure it's built into: it
used to ring on like a hung plate), floorboards' hollow modes, soil and turf giving with a thud (and grass's blades), a body's or a cushion's dull thump. The frag on concrete's octave spectrum was compared with s&box's
metal-on-hard-surface Foley: within 6 dB of it from 250 Hz up, but for the click's 2 kHz band, 8 dB brighter.

Footsteps of a soldier in combat boots (rubber lug soles, ~95 kg with kit). Each part of the sole that meets the floor
(heel, then forefoot) slaps the rubber on it, the heel's rubber and the leg behind it compress (a 150-650 Hz knock, the
body of a step) and the leg's weight arrives through it (a low thump). The floor adds its own: concrete grit crushed
under the lugs, a glazed tile's click, floorboards' hollow modes on their joists (the odd creak), a steel deck's
hollow clank, soil crunching, turf giving and grass blades swishing. Then the sole scuffs as the foot pushes off.
- step: a walk, heel then forefoot 70-110 ms later, a light push-off.
- run: a sprint, forefoot first and the heel just after, a hard push-off, the trousers and the kit (magazines in their
  pouches, the sling's hardware) rattling as the body comes down.
- land: both feet within 15-45 ms, at several times body weight: a heavy thump through the floor, the kit clattering.
Their levels follow the real ones against each other, not s&box's (which had grass 21 dB under concrete and a metal
deck 15 dB under it): walking on concrete stays where s&box's was, tile +1 dB, floorboards +2, a steel deck +2, dirt
-5, grass -10; a run is 6 dB over a walk (measured footfalls rise 6-10 dB from walking to running), a landing 4 dB over
a run. That landing is a jump's; in the game it's louder the faster you land (PlayerPawn.PlayFallSound).
A steel deck under a boot doesn't ping: the rubber heel's few ms of contact barely reach the plate's upper modes (a
hard object's sub-millisecond contact is what pings a plate), and a plate built into a frame or laid on a slab, with
the boot standing on it, damps the rest (loss 2.5-5%): a hollow clank, 20 dB down by 60-100 ms in its own band. It
used to ring on 16 sparse modes for up to a second, so a sprint's steps (every 0.25 s) overlapped into constant pinging,
and it was 4 dB over concrete (now 2).

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
    "metal": (-13.0, 6000, 5),
    "sheetmetal": (-13.0, 5000, 5),
    "glass": (-16.0, 5000, 5),
    "wood": (-18.0, 4000, 5),
    "plastic": (-20.0, 3000, 4),
    "dirt": (-22.0, 3000, 5),
    "grass": (-24.0, 3000, 5),
    "fabric": (-26.0, 2000, 4),
    "flesh": (-21.0, 2500, 5),
    # Not a material: the whir of a round glancing off a hard face, beside its impact (WorldSounds.BulletRicochet). A
    # tumbling slug's flow noise, heard from tens of metres at most, ~35 dB under a round's strike, squeezed to 15.
    "ricochet": (-30.0, 1500, 5),
}

# Knife strikes: (target loudness in dB, the event's distance in units). A thrust lands with a few tens of joules
# against a round's ~1,700, so a knife on a wall is ~25 dB under a bullet's strike in real life, squeezed here as the
# game squeezes a shot against a footstep (foley_voicing): ~12 dB under the bullet impacts. s&box played the surface's
# bullet impact for it, at a bullet's level.
KNIVES = {
    "masonry": (-27.0, 2000),
    "tile": (-27.0, 2000),
    "metal": (-23.0, 2500),
    "sheetmetal": (-24.0, 2500),
    "glass": (-27.0, 2000),
    "wood": (-29.0, 1800),
    "plastic": (-31.0, 1500),
    "dirt": (-34.0, 1200),
    "grass": (-36.0, 1200),
    "fabric": (-35.0, 1200),
    "flesh": (-30.0, 1500),
}
KNIFE_TAKES = 4
KNIFE_REFERENCE = 48
# The slash's whoosh is faint (aeolian sound off a blade at 15 m/s, 55-65 dB at the ear), about a walking step's
# level. The old one was upstream's -15.3 dB, a bullet impact's, heard to 5000 units with no occlusion.
KNIFE_SWING = (-34.0, 800, 4)

# Grenade bounces: (target loudness, distance) by floor, for a frag at ~6 m/s. A steel grenade on concrete at 1 m is
# about as loud as a hammer's light tap, 85-90 dB, ~25 dB over a walking step (-36 here): squeezed, about 8 dB over it.
# Harder bounces are louder in the game (WorldSounds.GrenadeBounce). A can rings a little more on a hard floor.
BOUNCE_FLOORS = {
    "concrete": (-28.0, 2500),
    "tile": (-27.0, 2500),
    "wood": (-26.0, 2500),
    "metal": (-23.0, 3000),
    "dirt": (-37.0, 1500),
    "grass": (-40.0, 1500),
    "soft": (-38.0, 1500),
}
BOUNCE_BODIES = {"frag": 0.0, "can": 0.5}
BOUNCE_TAKES = 4
BOUNCE_REFERENCE = 64

# Footsteps: the walk's target loudness by floor. s&box's concrete walk measures -36.3 dB at its event's volume.
FLOORS = {
    "concrete": -36.0,
    "tile": -35.0,
    "wood": -34.0,
    "metal": -34.0,
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
    """A round glancing off a hard face, deformed and tumbling, flying away. Its wake buzzes at the tumble rate: noise
    round the flow's shedding pitch, chopped a few hundred times a second, with a faint tone where the vortices lock
    to the tumble. It leaves at 250-500 m/s straight away from where it struck, so to anyone not on its new path it's
    Doppler-shifted down from the first moment and stays there, falling a little as it slows. The movie "pyeeow", a
    scream gliding down an octave, needs it to come at you and pass close. It fades as it flies off (its distance
    doubling every few tens of ms) and as it slows."""
    t = seconds_axis(seconds)
    speed = rng.uniform(250, 500) * np.exp(-t / rng.uniform(0.3, 0.6))      # m/s, drag slowing a tumbling slug
    receding = speed * rng.uniform(0.5, 0.95)                               # its speed away from the listener
    doppler = 343.0 / (343.0 + receding)
    shed = rng.uniform(6.0, 12.0) * speed * doppler                         # the wake's pitch, with its speed
    tumble = rng.uniform(1.0, 3.0) * speed * doppler                        # tumbles a second, heard shifted
    chop = 1 - rng.uniform(0.5, 0.8) * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(tumble) / SR + rng.uniform(0, 6)))
    # The wake's noise, swept with its pitch: a narrow band of noise, by ring modulation of a lowpassed noise.
    base = band(rng.standard_normal(len(t)), 0, 350)
    carrier = np.sin(2 * np.pi * np.cumsum(shed) / SR + rng.uniform(0, 6))
    wake = unit(base) * carrier + 0.35 * noise(rng, len(t), 1500, 7000)
    harmonic = np.round(shed / np.maximum(tumble, 1.0))
    tone = 0.2 * np.sin(2 * np.pi * np.cumsum(harmonic * tumble) / SR)      # the vortices locking to the tumble
    near = rng.uniform(3.0, 10.0)                                           # m, the listener off its path
    away = near / np.sqrt(near ** 2 + (np.cumsum(receding) / SR) ** 2)      # inverse distance as it flies off
    env = envelope(t, rng.uniform(0.002, 0.005), 1e9) * away * (speed / speed[0]) ** 3
    env *= 1 - np.clip((t - seconds + 0.04) / 0.04, 0, 1)
    return unit((wake + tone) * chop * env)


def bullet_ricochet(rng, take):
    """A round's ricochet off a glancing hit on a hard face, played beside its impact (WorldSounds.BulletRicochet)."""
    seconds = 0.45
    out = np.zeros(int(seconds * SR))
    add(out, ricochet(rng, 0.4), 0.0)
    return surroundings(rng, out, 0.5, 0.3)


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


def structural_modes(rng, count, low, high, loss, coincidence, sigma=0.25):
    """A plate built into a structure, struck: `count` bending modes between `low` and `high` Hz, at random (a plate's
    modes are dense and evenly spread, so there's no note to them). Each dies in T60 = 2.2 / (f loss), the higher ones
    sooner. The plate radiates well only above its coincidence frequency, so the modes under it are weak."""
    freqs = np.exp(rng.uniform(np.log(low), np.log(high), count))
    partials = [(f, rng.lognormal(0, sigma) / np.sqrt(1.0 + (coincidence / f) ** 4), 2.2 / (f * loss) / 6.91)
                for f in freqs]
    return unit(modes(min(0.8, 2.2 / (low * loss)), partials, 0.00003, rng))


def soft_strike_modes(rng, count, low, high, loss, contact, radiation):
    """structural_modes struck by something soft and slow, a boot's rubber heel. A strike that lasts a few ms puts
    little force into the modes above about 1 / its length (`contact` Hz), which is why a hard object pings a plate
    and a boot doesn't. A deck panel on its frame radiates its low modes poorly (under `radiation` Hz)."""
    freqs = np.exp(rng.uniform(np.log(low), np.log(high), count))
    partials = [(f, rng.lognormal(0, 0.3) / (1.0 + (f / contact) ** 2) / np.sqrt(1.0 + (radiation / f) ** 4),
                 2.2 / (f * loss) / 6.91) for f in freqs]
    return unit(modes(min(0.5, 2.2 / (low * loss)), partials, 0.0004, rng))


def bullet_metal(rng, take):
    seconds = 0.9
    out = np.zeros(int(seconds * SR))
    add(out, 1.0 * spike(rng, 0.00006), 0.0)
    add(out, 0.6 * blast(rng, rng.uniform(0.0005, 0.0009)), 0.0001)
    # Steelwork: a deck, a bulkhead, a beam or a wall's plating, welded or bolted into the structure round it. The
    # joints and the plates beyond carry the blow's energy off, so a built-up structure's loss factor is 1-2.5%
    # (measured on ships' and buildings' steelwork), against well under 0.1% for a steel target hung on chains. So it
    # clanks, a bright crack with a short metallic smear (T60 ~0.1 s at 2 kHz), where a hung plate rings on ("ding").
    # Its plating, 10-20 mm thick, radiates well above ~1 kHz, its coincidence frequency.
    add(out, 0.8 * structural_modes(rng, 64, 250, 11000, rng.uniform(0.01, 0.025), rng.uniform(800, 1400)), 0.0001)
    # The structure round it thudding with the blow, briefly.
    add(out, 0.3 * structure(rng, 90, 400, 8, 0.045, 0.4), 0.0003)
    # Lead and jacket splashing off it, and a few fragments ticking off whatever is nearby.
    add(out, 0.5 * crackle(rng, 0.04, int(rng.integers(40, 80)), 2500, 14000, 0.003), 0.0002)
    add(out, 0.25 * burst(rng, 0.06, 2000, 12000, 0.0003, 0.008), 0.0002)
    ticks = falling(rng, int(rng.integers(3, 8)), (0.2, 1.2), (0.5, 2.0), 0.4, 1, 0.05)
    lead = lambda r, s: fragment(r, r.uniform(2500, 6000), r.uniform(0.001, 0.003), 2)
    add(out, debris(rng, seconds, ticks, np.ones(len(ticks)), lead, 0.08), 0.0)
    return surroundings(rng, out, 0.8, 0.6)


def bullet_sheetmetal(rng, take):
    seconds = 0.6
    out = np.zeros(int(seconds * SR))
    add(out, 0.9 * spike(rng, 0.00008), 0.0)
    add(out, 0.5 * blast(rng, rng.uniform(0.0006, 0.001)), 0.0001)
    # The puncture tearing through, then the thin sheet's dense modes. A panel loses far more to the air it pumps,
    # its fixings and its seams (and a car's to its sound deadening) than a thick plate: a loss factor of 2-6%, so
    # it's a short "pank", not a ring. Its coincidence frequency is high (~8 kHz at 1.5 mm), but a panel radiates
    # from its edges and fixings well below it.
    add(out, 0.7 * crackle(rng, 0.03, int(rng.integers(20, 40)), 2000, 12000, 0.0015), 0.0002)
    add(out, 0.75 * structural_modes(rng, 48, 90, 7000, rng.uniform(0.02, 0.06), rng.uniform(150, 300), 0.35),
        0.0002)
    # The panel's lowest modes beating (the wobble), and its rattle against its fixings.
    low = rng.uniform(60, 110)
    add(out, 0.2 * unit(modes(0.4, [(low, 1.0, 0.07), (low * rng.uniform(1.04, 1.09), 0.8, 0.06)], 0.002, rng)),
        0.001)
    rattle_t = seconds_axis(0.2)
    gate = (np.sin(2 * np.pi * rng.uniform(55, 90) * rattle_t) > 0.6).astype(float)
    rattle = noise(rng, len(rattle_t), 1500, 6000) * gate * envelope(rattle_t, 0.008, 0.04)
    add(out, 0.12 * rattle, 0.005)
    return surroundings(rng, out, 0.8, 0.6)


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
    "ricochet": bullet_ricochet,
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
        # A steel deck or floor plate under a boot. The rubber heel's few ms of contact barely reach the plate's
        # upper modes, and a plate bolted to its frame or laid on a slab, with the boot standing on it, damps the rest
        # within a tenth of a second (loss factor 2.5-5%): a hollow clank with no note to it. Grit and the lugs' edges
        # tick on the bare steel.
        add(parts, 0.75 * slap(rng, 150, 2200, 0.003, brightness), 0.0)
        add(parts, 0.6 * soft_strike_modes(rng, 40, 120, 3000, rng.uniform(0.025, 0.05), rng.uniform(400, 600),
                                           rng.uniform(300, 450)), 0.0)
        add(parts, 0.55 * knock(rng, 150, 650, 0.006), 0.0)
        add(parts, 0.35 * thump(rng, 110, 160, 0.01), 0.0)
        add(parts, 0.08 * crackle(rng, 0.02, int(rng.integers(4, 10)), 3000, 10000, 0.004), 0.0005)
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
# The knife

def blade(rng):
    """The knife's own ring: a ~17 cm blade, 4 mm at the spine, gripped in the fist. Its flat bending modes stand at a
    cantilever's ratios over a fundamental of ~110 Hz (6.27, 17.5, 34.4, 56.8 and 85 times it), its edgewise ones about
    7.5 times higher, and the hand damps them within tens of ms. So thin a blade only radiates the upper ones: the
    "tink" of steel."""
    f1 = rng.uniform(100, 135)
    freqs = [f1 * r * rng.uniform(0.96, 1.04) for r in (6.27, 17.55, 34.39, 56.84, 84.9)]
    freqs += [f1 * 7.5 * r * rng.uniform(0.95, 1.05) for r in (1.0, 6.27)]
    partials = [(f, min(1.0, (f / 3000) ** 0.6) * rng.lognormal(0, 0.25), float(np.clip(0.05 * (2000 / f) ** 0.5,
                                                                                            0.008, 0.06)))
                for f in freqs]
    return unit(modes(0.3, partials, 0.00005, rng))


def skid(rng, seconds, low, high):
    """The tip skating over a hard face it can't bite: stick-slip friction, a gritty scrape."""
    t = seconds_axis(seconds)
    grit = 0.4 + unit(np.abs(band(rng.standard_normal(len(t)), 0, 600)))
    return noise(rng, len(t), low, high) * grit * envelope(t, 0.002, seconds * 0.3)


def rip(rng, seconds, low, high):
    """Cloth tearing: its threads parting one after another, a train of tiny snaps at a wavering rate."""
    t = seconds_axis(seconds)
    rate = rng.uniform(250, 600) * (1 + 0.3 * np.sin(2 * np.pi * rng.uniform(8, 20) * t))
    train = np.zeros(len(t))
    phase = np.cumsum(rate) / SR
    at = np.nonzero(np.diff(np.floor(phase)) > 0)[0]
    train[at] = rng.lognormal(0, 0.6, len(at)) * rng.choice([-1.0, 1.0], len(at))
    snaps = unit(band(train, low, high)) if np.any(train) else train
    return unit(0.7 * snaps + 0.4 * noise(rng, len(t), low, high)) * envelope(t, 0.002, seconds * 0.4)


# A thrust or a slash lands with a few tens of joules, a bullet with over a thousand, so the knife barely moves a wall:
# what's heard is the steel tip, the blade's ring and whatever the tip does to the face.

def knife_masonry(rng, take):
    out = np.zeros(int(0.5 * SR))
    add(out, 0.8 * spike(rng, 0.00005), 0.0)
    add(out, 0.55 * blade(rng), 0.0001)
    add(out, 0.35 * crackle(rng, 0.02, int(rng.integers(8, 20)), 2000, 10000, 0.002), 0.0002)
    add(out, 0.3 * knock(rng, 200, 1200, 0.004), 0.0)       # the fist and the handle jolting to a stop
    add(out, 0.12 * structure(rng, 120, 500, 6, 0.01, 0.2), 0.0003)
    if take != 2:
        add(out, 0.3 * skid(rng, rng.uniform(0.03, 0.08), 2500, 9000), rng.uniform(0.002, 0.006))
    grit = falling(rng, int(rng.integers(10, 30)), (0.5, 1.4), (0.0, 0.5), 0.2, 0)
    add(out, 0.04 * patter(rng, 0.5, grit, 3000, 10000), 0.0)
    return surroundings(rng, out, 0.6, 0.4)


def knife_tile(rng, take):
    out = np.zeros(int(0.5 * SR))
    add(out, 0.9 * spike(rng, 0.00004), 0.0)
    add(out, 0.6 * blade(rng), 0.0001)
    ring = [(rng.uniform(2100, 2700), 1.0, 0.006), (rng.uniform(3300, 3900), 0.6, 0.004),
            (rng.uniform(4800, 5600), 0.4, 0.003)]
    add(out, 0.3 * unit(modes(0.05, ring, 0.0001, rng)), 0.0001)
    add(out, 0.1 * structure(rng, 150, 600, 6, 0.008, 0.2), 0.0003)
    if take != 1:
        add(out, 0.25 * skid(rng, rng.uniform(0.03, 0.07), 3000, 10000), rng.uniform(0.002, 0.005))
    return surroundings(rng, out, 0.6, 0.4)


def knife_metal(rng, take):
    """Steel on thick steel: the tip's "tang", and the plate ringing on."""
    out = np.zeros(int(0.9 * SR))
    add(out, 0.9 * spike(rng, 0.00004), 0.0)
    add(out, 0.55 * blade(rng), 0.0001)
    freqs = np.exp(rng.uniform(np.log(300), np.log(9000), 18))
    plate = [(f, (f / 1000) ** -0.1 * rng.lognormal(0, 0.35), float(np.clip(0.15 * (500 / f) ** 0.6, 0.02, 0.2)))
             for f in freqs]
    add(out, 0.6 * unit(modes(0.8, plate, 0.00005, rng)), 0.0001)
    base = rng.uniform(1300, 2000)
    ping = [(base * r * rng.uniform(0.98, 1.02), r ** -0.5, 0.2 * r ** -0.8) for r in (1.0, 1.58, 2.13, 2.71)]
    add(out, 0.4 * unit(modes(0.8, ping, 0.00005, rng)), 0.0001)
    if take % 2 == 0:
        add(out, 0.2 * skid(rng, rng.uniform(0.03, 0.06), 3500, 11000), rng.uniform(0.002, 0.005))
    return surroundings(rng, out, 0.7, 0.6)


def knife_sheetmetal(rng, take):
    """A car door or a tin roof: the thin sheet booms and wobbles, and half the time the tip punches through."""
    out = np.zeros(int(0.7 * SR))
    add(out, 0.8 * spike(rng, 0.00008), 0.0)
    add(out, 0.45 * blade(rng), 0.0001)
    freqs = np.exp(rng.uniform(np.log(90), np.log(6000), 32))
    sheet = [(f, (f / 300) ** -0.3 * rng.lognormal(0, 0.4), float(np.clip(0.18 * (300 / f) ** 0.5, 0.02, 0.25)))
             for f in freqs]
    add(out, 0.7 * unit(modes(0.6, sheet, 0.0002, rng)), 0.0002)
    low = rng.uniform(60, 110)
    add(out, 0.25 * unit(modes(0.5, [(low, 1.0, 0.15), (low * rng.uniform(1.04, 1.09), 0.8, 0.12)], 0.002, rng)),
        0.001)
    if take % 2 == 1:
        add(out, 0.4 * crackle(rng, 0.02, int(rng.integers(10, 25)), 2000, 11000, 0.0015), 0.0003)
    return surroundings(rng, out, 0.7, 0.6)


def knife_glass(rng, take):
    """The tip on a pane that holds: a sharp "tink", the pane's thump and a short ring. No crack."""
    out = np.zeros(int(0.5 * SR))
    add(out, 0.9 * spike(rng, 0.00004), 0.0)
    add(out, 0.5 * blade(rng), 0.0001)
    add(out, 0.25 * structure(rng, 80, 600, 8, 0.02, 0.3), 0.0003)
    pane = [(rng.uniform(1800, 2600), 1.0, 0.04), (rng.uniform(3500, 4500), 0.7, 0.03),
            (rng.uniform(5500, 6800), 0.45, 0.02)]
    add(out, 0.45 * unit(modes(0.3, pane, 0.0001, rng)), 0.0001)
    if take == 3:
        add(out, 0.2 * skid(rng, 0.04, 4000, 12000), 0.003)
    return surroundings(rng, out, 0.6, 0.4)


def knife_wood(rng, take):
    """The tip bites in: the fibres crush and the member knocks, and the wood grips the blade, so it barely rings."""
    out = np.zeros(int(0.5 * SR))
    add(out, 0.5 * spike(rng, 0.00012), 0.0)
    f1 = rng.uniform(140, 300)
    member = [(f1 * r * rng.uniform(0.95, 1.05), r ** -0.35, 25 / (np.pi * f1 * r)) for r in (1.0, 2.76, 5.4, 8.9)]
    add(out, 0.5 * unit(modes(0.3, member, 0.0003, rng)), 0.0002)
    add(out, 0.4 * crackle(rng, 0.03, int(rng.integers(10, 25)), 1500, 8000, 0.006), 0.0003)
    add(out, 0.3 * burst(rng, 0.03, 300, 3000, 0.0003, 0.003), 0.0)
    add(out, 0.15 * blade(rng), 0.0001)
    return surroundings(rng, out, 0.6, 0.4)


def knife_plastic(rng, take):
    out = np.zeros(int(0.4 * SR))
    add(out, 0.4 * spike(rng, 0.0001), 0.0)
    f1 = rng.uniform(150, 300)
    shell = [(f1 * r * rng.uniform(0.95, 1.05), r ** -0.4, 0.025 / r ** 0.7) for r in (1.0, 1.9, 2.8, 4.1, 5.5)]
    add(out, 0.7 * unit(modes(0.25, shell, 0.0004, rng)), 0.0002)
    add(out, 0.4 * burst(rng, 0.02, 1000, 8000, 0.0002, 0.0015), 0.0)
    add(out, 0.25 * blade(rng), 0.0001)
    return surroundings(rng, out, 0.6, 0.4)


def knife_dirt(rng, take):
    """The blade sinks into the soil: a soft chuff and the grains crunching, no ring."""
    out = np.zeros(int(0.4 * SR))
    t = seconds_axis(0.08)
    add(out, 0.6 * np.sin(2 * np.pi * rng.uniform(120, 200) * t) * envelope(t, 0.002, 0.01), 0.0)
    add(out, 0.7 * burst(rng, 0.1, 200, 2000, 0.002, 0.02), 0.0)
    add(out, 0.4 * crackle(rng, 0.05, int(rng.integers(20, 45)), 500, 5000, 0.015, 0.8), 0.001)
    if take == 0:
        add(out, 0.2 * fragment(rng, rng.uniform(2500, 5000), rng.uniform(0.001, 0.002), 2), rng.uniform(0.0, 0.01))
    return surroundings(rng, out, 0.5, 0.3)


def knife_grass(rng, take):
    out = np.zeros(int(0.45 * SR))
    t = seconds_axis(0.08)
    add(out, 0.5 * np.sin(2 * np.pi * rng.uniform(110, 180) * t) * envelope(t, 0.002, 0.01), 0.0)
    add(out, 0.4 * burst(rng, 0.1, 200, 2000, 0.002, 0.02), 0.0)
    rustle_t = seconds_axis(0.2)
    flicks = unit(band(rng.standard_normal(len(rustle_t)), 0, 80)) ** 2
    add(out, 0.45 * noise(rng, len(rustle_t), 1500, 10000) * (0.35 + flicks) * envelope(rustle_t, 0.004, 0.04), 0.0)
    add(out, 0.3 * crackle(rng, 0.03, int(rng.integers(3, 9)), 2000, 7000, 0.006), 0.0)
    return surroundings(rng, out, 0.5, 0.3)


def knife_fabric(rng, take):
    """Cloth, a cushion, a sandbag: the tip snags and tears the face, and what's behind it takes the blow."""
    out = np.zeros(int(0.4 * SR))
    add(out, 0.7 * rip(rng, rng.uniform(0.04, 0.09), 800, 7000), 0.0)
    add(out, 0.45 * knock(rng, 150, 600, 0.008), 0.002)
    add(out, 0.3 * thump(rng, 90, 140, 0.012), 0.002)
    return surroundings(rng, out, 0.5, 0.3)


def knife_flesh(rng, take):
    """A stab into a soldier: the uniform's cloth punctured, the fist and the guard slapping the body, and the body's
    dull thud. The kit on it knocks as it's jolted. No crack, no ring, no debris: quieter by far than a bullet's hit."""
    out = np.zeros(int(0.4 * SR))
    add(out, 0.45 * rip(rng, rng.uniform(0.02, 0.04), 1000, 6000), 0.0)
    add(out, 0.8 * burst(rng, 0.04, 400, 3000, 0.0003, 0.004), 0.003)
    add(out, 0.8 * knock(rng, 200, 900, 0.006), 0.003)
    add(out, 0.25 * thump(rng, 90, 130, 0.012), 0.004)
    if take % 2 == 0:
        add(out, 0.08 * rattle(rng, int(rng.integers(2, 4)), 0.05), 0.01)
    return surroundings(rng, out, 0.5, 0.3)


KNIFE_IMPACTS = {
    "masonry": knife_masonry,
    "tile": knife_tile,
    "metal": knife_metal,
    "sheetmetal": knife_sheetmetal,
    "glass": knife_glass,
    "wood": knife_wood,
    "plastic": knife_plastic,
    "dirt": knife_dirt,
    "grass": knife_grass,
    "fabric": knife_fabric,
    "flesh": knife_flesh,
}


def knife_swing(rng, take):
    """The blade cutting the air in a slash of ~0.2 s, its tip peaking at 12-18 m/s. Vortices shed off the spine
    (Strouhal: 0.2 v / 4 mm, ~750 Hz at 15 m/s) and the edge's finer ones make a band of noise whose pitch follows the
    blade's speed and whose pressure goes as its cube (a dipole's aeolian sound). The sleeve and the kit move with it."""
    seconds = 0.5
    t = seconds_axis(seconds)
    start, sweep = rng.uniform(0.01, 0.03), rng.uniform(0.15, 0.24)
    phase = np.clip((t - start) / sweep, 0.0, 1.0)
    speed = rng.uniform(12, 18) * np.sin(np.pi * phase ** rng.uniform(0.8, 1.2)) ** 1.3
    centre = np.maximum(0.2 * speed / 0.004, 60.0)
    amplitude = (speed / speed.max()) ** 3
    white = rng.standard_normal(len(t))
    freqs, times, spectrum = signal.stft(white, SR, nperseg=512, noverlap=448)
    fc = np.interp(times, t, centre)
    amp = np.interp(times, t, amplitude)
    logs = np.log(np.maximum(freqs, 1.0)[:, None] / fc[None, :])
    tone = np.exp(-0.5 * (logs / 0.3) ** 2)                      # the spine's shedding, about an octave wide
    edge = np.exp(-0.5 * ((logs - np.log(4.0)) / 0.7) ** 2) * 0.35  # the edge's finer vortices, two octaves up
    _, swish = signal.istft(spectrum * (tone + edge) * amp[None, :], SR, nperseg=512, noverlap=448)
    swish = unit(swish[: len(t)])
    out = np.zeros(len(t))
    add(out, swish, 0.0)
    # The arm's own air, a low whump, and the sleeve and kit.
    add(out, 0.15 * unit(band(rng.standard_normal(len(t)), 80, 400)) * (speed / speed.max()) ** 2, 0.0)
    add(out, rustle(rng, sweep + 0.1, 0.12), max(start - 0.02, 0.0))
    if take % 2 == 1:
        add(out, 0.05 * rattle(rng, int(rng.integers(1, 3)), 0.1), start + sweep * 0.8)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# Grenade bounces

def grenade_body(rng, body, hardness):
    """The grenade's own sound as it strikes, `hardness` how hard the floor is (1 for concrete, tile and steel, less
    for wood, little for soil, grass or a body, which stop it too slowly to set its shell ringing).
    - frag: an M67, a 64 mm steel sphere with a 2.5 mm wall, 0.4 kg filled with Composition B, which damps its shell
      modes to a dull "clunk"; the fuze's striker and spring tick in the fuze body a moment later.
    - can: an M18 smoke, M84 or AN-M14, a thin sheet-steel can over its filler: a hollow "tonk" that rings a little
      longer, and its lid and fuze rattling."""
    out = np.zeros(int(0.3 * SR))
    if body == "frag":
        shell = [(rng.uniform(2000, 2600), 1.0, 0.004), (rng.uniform(3300, 4000), 0.7, 0.003),
                 (rng.uniform(5200, 6200), 0.4, 0.002), (rng.uniform(900, 1200), 0.5, 0.005)]
        add(out, hardness * unit(modes(0.1, shell, 0.0001, rng)), 0.0)
        add(out, 0.25 * hardness * fragment(rng, rng.uniform(4500, 7000), rng.uniform(0.002, 0.004), 3),
            rng.uniform(0.001, 0.003))
    else:
        f1 = rng.uniform(700, 1000)
        can = [(f1 * r * rng.uniform(0.97, 1.03), r ** -0.3, 0.014 / r ** 0.5) for r in (1.0, 1.62, 2.31, 3.12, 4.4)]
        add(out, hardness * unit(modes(0.15, can, 0.0001, rng)), 0.0)
        for _ in range(int(rng.integers(1, 4))):
            add(out, 0.2 * hardness * fragment(rng, rng.uniform(2500, 6000), rng.uniform(0.001, 0.003), 2),
                rng.uniform(0.002, 0.02))
    return out


def bounce(rng, body, floor):
    """A thrown grenade striking `floor` at about 6 m/s (its later bounces; GrenadeBounce plays harder ones louder)."""
    seconds = 0.8
    out = np.zeros(int(seconds * SR))
    if floor in ("concrete", "tile", "metal"):
        # Steel on a hard floor: a contact of ~0.2 ms (Hertz, for 0.4 kg at 6 m/s), a sharp click.
        add(out, 0.8 * spike(rng, 0.00006), 0.0)
        add(out, 0.8 * grenade_body(rng, body, 1.0), 0.0001)
        if floor == "concrete":
            # 0.4 kg stopping dead jolts the slab round the contact: a dull knock under the click.
            add(out, 0.25 * crackle(rng, 0.01, int(rng.integers(3, 10)), 2500, 9000, 0.001), 0.0001)
            add(out, 0.4 * knock(rng, 300, 1500, 0.003), 0.0)
            add(out, 0.3 * structure(rng, 150, 700, 6, 0.008, 0.2), 0.0003)
        elif floor == "tile":
            ring = [(rng.uniform(2000, 2600), 1.0, 0.007), (rng.uniform(3200, 3800), 0.6, 0.005),
                    (rng.uniform(4700, 5500), 0.35, 0.003)]
            add(out, 0.35 * unit(modes(0.06, ring, 0.0001, rng)), 0.0001)
            add(out, 0.3 * knock(rng, 300, 1500, 0.003), 0.0)
            add(out, 0.25 * structure(rng, 150, 700, 6, 0.008, 0.2), 0.0003)
        else:
            # Steel on a steel deck: the hard contact reaches the plate's upper modes, a bright clank, the loudest
            # floor to land a grenade on. A deck built into its frame damps them within a tenth of a second
            # (structural_modes, loss 1.5-3%), where a hung plate would ring on.
            add(out, 0.7 * structural_modes(rng, 48, 150, 8000, rng.uniform(0.015, 0.03), rng.uniform(800, 1400)),
                0.0001)
            add(out, 0.3 * knock(rng, 300, 1500, 0.003), 0.0)
            add(out, 0.25 * structure(rng, 100, 500, 6, 0.012, 0.25), 0.0003)
    elif floor == "wood":
        # Floorboards over joists: the board's hollow modes carry most of it.
        add(out, 0.5 * spike(rng, 0.00012), 0.0)
        add(out, 0.5 * grenade_body(rng, body, 0.6), 0.0001)
        f1 = rng.uniform(95, 140)
        board = [(f1, 1.0, 0.07), (f1 * rng.uniform(2.2, 2.5), 0.8, 0.05), (f1 * rng.uniform(3.9, 4.4), 0.6, 0.03),
                 (f1 * rng.uniform(6.5, 7.2), 0.35, 0.018), (f1 * rng.uniform(10, 11.5), 0.2, 0.01)]
        add(out, 0.8 * unit(modes(0.4, board, 0.001, rng)), 0.0001)
        add(out, 0.3 * knock(rng, 200, 1500, 0.004), 0.0)
    elif floor in ("dirt", "grass"):
        # The soil gives: a thud and a crunch, and the grenade barely rings.
        t = seconds_axis(0.1)
        add(out, 0.7 * np.sin(2 * np.pi * rng.uniform(90, 150) * t) * envelope(t, 0.003, 0.012), 0.0)
        add(out, 0.6 * knock(rng, 150, 800, 0.008), 0.0)
        add(out, 0.12 * grenade_body(rng, body, 0.3), 0.0005)
        if floor == "dirt":
            add(out, 0.35 * crackle(rng, 0.05, int(rng.integers(15, 35)), 500, 5000, 0.01, 0.8), 0.001)
            if rng.random() < 0.5:
                add(out, 0.15 * fragment(rng, rng.uniform(2500, 5000), rng.uniform(0.001, 0.002), 2),
                    rng.uniform(0.0, 0.01))
        else:
            rustle_t = seconds_axis(0.2)
            flicks = unit(band(rng.standard_normal(len(rustle_t)), 0, 80)) ** 2
            add(out, 0.4 * noise(rng, len(rustle_t), 1500, 10000) * (0.35 + flicks) * envelope(rustle_t, 0.004, 0.04),
                0.0)
    else:
        # Cloth, a cushion or a body: a dull thump.
        add(out, 0.6 * knock(rng, 150, 600, 0.01), 0.0)
        add(out, 0.4 * thump(rng, 90, 140, 0.014), 0.0)
        add(out, 0.25 * burst(rng, 0.04, 400, 3000, 0.001, 0.006), 0.0)
        add(out, 0.08 * grenade_body(rng, body, 0.3), 0.001)
    return surroundings(rng, out, 0.7, 0.6)


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
    folder = os.path.join(ASSETS, "sounds", "world", "knife")
    for index, (material, (target, distance)) in enumerate(KNIVES.items()):
        names, takes, volume = build_set(f"knife_{material}", KNIFE_IMPACTS[material], KNIFE_TAKES, 2000 + 100 * index,
                                         target, IMPACT_DRIVE)
        out.append((folder, "sounds/world/knife", f"knife_{material}", names, takes, volume, 1.5, "0.95 1.05",
                    distance, KNIFE_REFERENCE))
    target, distance, count = KNIFE_SWING
    names, takes, volume = build_set("knife_swing", knife_swing, count, 3200, target)
    out.append((folder, "sounds/world/knife", "knife_swing", names, takes, volume, 2.0, "0.94 1.06", distance,
                KNIFE_REFERENCE))
    folder = os.path.join(ASSETS, "sounds", "world", "grenades")
    for body_index, (body, over) in enumerate(BOUNCE_BODIES.items()):
        for index, (floor, (target, distance)) in enumerate(BOUNCE_FLOORS.items()):
            hard = floor in ("concrete", "tile", "metal")
            make = lambda rng, i, body=body, floor=floor: bounce(rng, body, floor)
            names, takes, volume = build_set(f"{body}_{floor}", make, BOUNCE_TAKES,
                                             7000 + 1000 * body_index + 100 * index, target + (over if hard else 0.0),
                                             IMPACT_DRIVE)
            out.append((folder, "sounds/world/grenades", f"{body}_{floor}", names, takes, volume, 1.5, "0.95 1.05",
                        distance, BOUNCE_REFERENCE))
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
    "knife_masonry": "sounds/impacts/bullets/impact-bullet-generic.sound",
    "knife_metal": "sounds/impacts/bullets/impact-bullet-metal.sound",
    "knife_wood": "sounds/impacts/bullets/impact-bullet-wood.sound",
    "knife_swing": "sounds/guns/knife/knife.swing.sound",
    "frag_concrete": "sounds/impacts/melee/impact-melee-metal.sound",
    "frag_wood": "sounds/impacts/melee/impact-melee-metal.sound",
    "ui_button_press": "sounds/kenney/ui/ui.button.press.sound",
    "ui_button_hover": "sounds/kenney/ui/ui.button.over.sound",
}


def stock_file(path):
    """A compiled file from s&box's core, or else from the project's own Assets (upstream's sounds)."""
    core = os.path.join(SBOX_CORE, path + "_c")
    return core if os.path.exists(core) else os.path.join(ROOT, "Assets", path + "_c")


def stock_event(path):
    """A compiled core event's takes and volume: its source JSON is kept in the _c."""
    import re
    data = open(stock_file(path), "rb").read()
    source = json.loads(re.search(rb"\{.*\}", data, re.S).group().decode("utf-8", "replace"))
    volume = source.get("Volume", source.get("volume", 1))
    volume = float(str(volume).replace(",", " ").split()[0])
    return source.get("Sounds") or source.get("sounds"), volume


def stock_audio(vsnd):
    """A compiled vsnd's samples: the DATA block holds the rate, format and channels, and 16-bit PCM follows the
    header. None for other formats."""
    data = open(stock_file(vsnd), "rb").read()
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


def bouncing(takes, rng, speed=9.0, restitution=0.4):
    """A grenade landing at `speed` m/s and bouncing on, each bounce as loud as GrenadeBounce plays it."""
    out = np.zeros(int(3.0 * SR))
    at = 0.0
    while speed > 1.0 and at < 2.5:
        add(out, takes[rng.integers(len(takes))] * min(2.0, (speed / 6.0) ** 1.2), at)
        at += 2 * speed / G
        speed *= restitution
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
            elif name.startswith(("frag_", "can_")):
                section += [bouncing(takes, rng)]
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
