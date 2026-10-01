"""
Handling and hit sounds modelled on the real thing, in place of the stock and upstream ones: the dry-fire click, drawing a
weapon, spent brass landing, and a bullet striking a helmet or a bare head. Like world_sounds.py, they're synthesised
from the physics of each event, with no samples.

    python Tools/handling_sounds.py [--preview <wav>] [--out <dir>]

Writes, with a .sound event for each set if it doesn't exist yet (an event may be tuned in the editor, so it isn't
overwritten; delete one to have it rewritten):
- Assets/sounds/guns/handling/dryfire_{rifle,ak,pistol}: the hammer falling on an empty chamber. The guns' prefabs
  pick theirs (`DryFireSound`); upstream's one click was on every gun.
- Assets/sounds/guns/handling/draw_{rifle,pistol,grenade}: a long gun brought up off its sling, a pistol out of its
  holster, a grenade out of its pouch (each prefab's `DeploySound`, in place of upstream's weapon_switch).
- Assets/sounds/world/casings/brass_{rifle,pistol}_<floor>: one case landing, on concrete, tile, wood, metal, dirt or
  grass (WorldSounds.CasingBounce, from SpentCasing on each bounce, in place of upstream's shell_case_bounce).
- Assets/sounds/player/hits/helmet_hit and head_hit: the player prefab's headshot sounds (with and without a helmet),
  in place of upstream's (13000 units' reach, 7-10 dB over a flesh hit).
--preview writes every take in a row, and a few casings bouncing as SpentCasing plays them.

Dry fire. An AR's trigger breaks (the disconnector and sear let go: a tick), the hammer swings ~60 degrees and strikes
the firing pin 4-6 ms later (a sharp steel blow), and the bolt carrier and the aluminium receiver ring with it, damped by
the hands; the hammer spring twangs, and the trigger comes to its stop. An AK's hammer is heavier and its stamped steel
receiver rattles round the trigger group, so the click is lower and buzzier. A pistol's click (the USP's and 1911's
hammers, the M18's striker) is lighter, higher and shorter. At the shooter's ear it's ~75-80 dB.

Draws. A rifle: the sleeve and the sling's nylon webbing sliding through its swivel, the swivel's clink, the magazine
knocking in the well, then the support hand slapping onto the handguard as the stock comes to the shoulder. A pistol: a
Kydex holster's retention clicking open, the slide scraping out of it, then the support hand meeting the grip. A grenade:
the pouch's hook-and-loop flap tearing open, the grenade sliding out of the nylon, and its lever ticking against the
body.

Brass. A spent 5.56 case is a thin brass tube 9.6 mm across: its lowest ring modes (the n = 2 and 3 circumferential
modes, ~7 kHz and up) give the "tink", and its bending modes are above hearing. It lands rim-first or side-first and
chatters (two or three contacts within a few ms). Hard floors let it ring for tens of ms; wood damps it and knocks
under it; a steel deck rings with it; earth and grass take the ring and leave a dull tick. A 9 mm case is shorter and
thicker-walled: higher and shorter. One case on concrete is ~70 dB at 1 m.

Hits. A rifle round through an aramid composite helmet (an ACH): the shell's fibres and resin fracturing (a dry, sharp
crack), the shell's damped hollow modes, the mount's hardware clinking, and the head behind it. Through a bare head:
the bone's fracture crack, the head's dull thud and a wet spray. The attacker and the victim hear them flat, as a hit's
feedback (PlayerPawn.Health).

Levels are K-weighted loudness of the loudest 50 ms (ui_sounds.loudness), against world_sounds' walk on concrete (-36,
a ~63 dB footstep), with real differences squeezed by 0.43 as the rest of the mix is: the dry fire ~8 dB over the
step (the AK's 1 dB more, a pistol's 2 dB less), a draw ~4.5 dB over it, a case on concrete 3 dB over it (louder on
tile and steel, far quieter on earth and grass, a pistol case 1.5 dB under a rifle case). The hits sit just over a
flesh impact (-22.5), as upstream's sat over theirs.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_sounds as ws  # noqa: E402
from world_sounds import (SR, add, band, burst, crackle, envelope, fragment, modes, noise, rattle, rip,  # noqa: E402
                          seconds_axis, spike, unit)

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ASSETS = os.path.join(ROOT, "Assets")
REFERENCE = 64

# (target loudness, event distance) for each set.
DRYFIRE = {"rifle": (-28.5, 800), "ak": (-27.5, 800), "pistol": (-30.5, 700)}
DRAWS = {"rifle": (-31.5, 800), "pistol": (-32.5, 700), "grenade": (-33.0, 700)}
CASING_FLOORS = {
    "concrete": -33.0,
    "tile": -32.5,
    "wood": -37.0,
    "metal": -30.5,
    "dirt": -46.0,
    "grass": -49.0,
}
CASING_DISTANCE = 700
PISTOL_CASE = -1.5
HITS = {"helmet_hit": (-20.0, 2500), "head_hit": (-21.0, 2500)}
HIT_REFERENCE = 96
TAKES = {"dryfire": 4, "draw": 3, "casing": 5, "hit": 4}


# ----------------------------------------------------------------------------------------------------------------------
# Dry fire

def steel_blow(rng, low, high, tau, count=8):
    """A small steel part struck: its modes, spread log-uniformly over the band, damped by the hands round the gun."""
    freqs = np.exp(rng.uniform(np.log(low), np.log(high), count))
    partials = [(f, rng.lognormal(0, 0.35) * (f / low) ** -0.2, tau * (low / f) ** 0.35) for f in freqs]
    return unit(modes(0.15, partials, 0.00005, rng))


def dryfire(rng, take, kind):
    seconds = 0.3
    out = np.zeros(int(seconds * SR))
    if kind == "pistol":
        trigger, travel = 0.0, rng.uniform(0.003, 0.0045)
        add(out, 0.25 * fragment(rng, rng.uniform(6000, 8000), 0.0012, 2), trigger)
        add(out, 1.0 * spike(rng, 0.00006), trigger + travel)
        add(out, 0.75 * steel_blow(rng, 2500, 9000, 0.012), trigger + travel)
        add(out, 0.2 * burst(rng, 0.03, 600, 3000, 0.0003, 0.006), trigger + travel)          # the frame and the hand
        add(out, 0.15 * fragment(rng, rng.uniform(3500, 5000), 0.003, 2), trigger + travel + rng.uniform(0.015, 0.03))
        return out
    trigger = 0.0
    travel = rng.uniform(0.004, 0.006) * (1.15 if kind == "ak" else 1.0)
    # The sear letting go.
    add(out, 0.3 * fragment(rng, rng.uniform(5500, 7500), 0.0015, 2), trigger)
    # The hammer on the firing pin, and the parts round it ringing.
    add(out, 1.0 * spike(rng, 0.00008 if kind == "rifle" else 0.0001), trigger + travel)
    if kind == "rifle":
        add(out, 0.8 * steel_blow(rng, 1800, 7500, 0.02), trigger + travel)
        receiver = [(rng.uniform(900, 1300), 1.0, 0.012), (rng.uniform(2100, 2700), 0.6, 0.008)]
        add(out, 0.35 * unit(modes(0.1, receiver, 0.0002, rng)), trigger + travel)
    else:
        add(out, 0.8 * steel_blow(rng, 1400, 6000, 0.025), trigger + travel)
        # The stamped receiver's sheet buzzing round the trigger group: a few loose contacts in a burst.
        add(out, 0.35 * rattle(rng, int(rng.integers(3, 6)), 0.012)[: int(0.12 * SR)], trigger + travel + 0.001)
        receiver = [(rng.uniform(700, 1000), 1.0, 0.018), (rng.uniform(1600, 2200), 0.7, 0.012)]
        add(out, 0.4 * unit(modes(0.12, receiver, 0.0002, rng)), trigger + travel)
    # The hammer spring's twang and the trigger reaching its stop.
    t = seconds_axis(0.08)
    twang = np.sin(2 * np.pi * rng.uniform(700, 1100) * t) * envelope(t, 0.0005, 0.012)
    add(out, 0.12 * twang, trigger + travel + 0.001)
    add(out, 0.2 * fragment(rng, rng.uniform(3000, 4500), 0.002, 2), trigger + travel + rng.uniform(0.012, 0.025))
    add(out, 0.1 * burst(rng, 0.04, 300, 2000, 0.0005, 0.008), trigger + travel)       # the hands round the gun
    return out


# ----------------------------------------------------------------------------------------------------------------------
# Draws

def webbing(rng, seconds):
    """Nylon webbing sliding through a swivel and over a sleeve: a scratchy friction noise with the weave's grain."""
    t = seconds_axis(seconds)
    grain = 0.35 + unit(np.abs(band(rng.standard_normal(len(t)), 0, 250)))
    return noise(rng, len(t), 900, 6500) * grain * envelope(t, seconds * 0.3, seconds * 0.3)


def cloth(rng, seconds):
    """Sleeves and a plate carrier's nylon moving: a soft, low rustle."""
    t = seconds_axis(seconds)
    swell = 0.5 + unit(np.abs(band(rng.standard_normal(len(t)), 0, 20)))
    return noise(rng, len(t), 300, 4000) * swell * envelope(t, seconds * 0.35, seconds * 0.3)


def hand_slap(rng, low, high):
    """A gloved hand closing on a gun: a short padded slap."""
    return burst(rng, 0.05, low, high, 0.0006, 0.005)


def draw_rifle(rng, take):
    seconds = 0.8
    out = np.zeros(int(seconds * SR))
    add(out, 0.35 * cloth(rng, rng.uniform(0.35, 0.5)), 0.0)
    add(out, 0.4 * webbing(rng, rng.uniform(0.15, 0.25)), rng.uniform(0.02, 0.06))
    for _ in range(int(rng.integers(1, 3))):                                    # the sling's swivel
        add(out, 0.3 * fragment(rng, rng.uniform(3500, 5500), rng.uniform(0.004, 0.008), 3), rng.uniform(0.05, 0.2))
    add(out, 0.25 * rattle(rng, int(rng.integers(2, 4)), 0.05), rng.uniform(0.12, 0.22))   # the magazine in the well
    up = rng.uniform(0.3, 0.42)
    add(out, 1.0 * hand_slap(rng, 250, 2500), up)                              # the support hand on the handguard
    add(out, 0.45 * burst(rng, 0.06, 120, 700, 0.002, 0.012), up + rng.uniform(0.02, 0.05))  # the stock into the shoulder
    add(out, 0.15 * fragment(rng, rng.uniform(2500, 4000), 0.006, 3), up + 0.002)
    return out


def draw_pistol(rng, take):
    seconds = 0.6
    out = np.zeros(int(seconds * SR))
    add(out, 0.25 * cloth(rng, rng.uniform(0.25, 0.35)), 0.0)
    click = rng.uniform(0.04, 0.08)                                             # the holster's retention letting go
    add(out, 0.8 * fragment(rng, rng.uniform(2800, 4200), 0.0025, 3), click)
    add(out, 0.3 * spike(rng, 0.00008), click)
    t = seconds_axis(0.09)                                                      # the slide scraping out of the Kydex
    scrape = noise(rng, len(t), 1200, 7000) * (0.4 + unit(np.abs(band(rng.standard_normal(len(t)), 0, 500))))
    add(out, 0.45 * scrape * envelope(t, 0.02, 0.03), click + 0.01)
    grip = click + rng.uniform(0.18, 0.26)
    add(out, 0.9 * hand_slap(rng, 300, 3000), grip)                             # the support hand meeting the grip
    add(out, 0.12 * fragment(rng, rng.uniform(3000, 4500), 0.004, 2), grip + 0.003)
    return out


def draw_grenade(rng, take):
    seconds = 0.7
    out = np.zeros(int(seconds * SR))
    add(out, 0.25 * cloth(rng, rng.uniform(0.3, 0.4)), 0.0)
    flap = rng.uniform(0.03, 0.06)                                              # the pouch's hook-and-loop tearing open
    add(out, 0.75 * rip(rng, rng.uniform(0.08, 0.14), 1500, 9000), flap)
    out_at = flap + rng.uniform(0.15, 0.22)
    add(out, 0.35 * webbing(rng, rng.uniform(0.08, 0.12)), out_at)              # the grenade sliding out of the nylon
    for _ in range(int(rng.integers(1, 3))):                                    # its lever ticking on the body
        add(out, 0.35 * fragment(rng, rng.uniform(4000, 6500), rng.uniform(0.002, 0.004), 3),
            out_at + rng.uniform(0.04, 0.12))
    add(out, 0.6 * hand_slap(rng, 300, 2000), out_at + rng.uniform(0.12, 0.18))   # caught in the throwing hand
    return out


# ----------------------------------------------------------------------------------------------------------------------
# Brass

CASE_RING = {"rifle": (6500, 11000), "pistol": (9500, 14500)}
# How each floor treats a landing case: its ring's decay (s), the floor's own part, and how bright the contact is.
FLOOR_CONTACT = {
    "concrete": (0.035, "grit", 1.0),
    "tile": (0.04, "tile", 1.1),
    "wood": (0.012, "board", 0.7),
    "metal": (0.045, "plate", 1.1),
    "dirt": (0.003, "soil", 0.35),
    "grass": (0.002, "grass", 0.25),
}


def case_ring(rng, kind, tau):
    """A brass case's ring: its circumferential modes in the case's band, the lowest strongest."""
    low, high = CASE_RING[kind]
    f = rng.uniform(low, low * 1.25)
    ratios = [1.0, rng.uniform(1.35, 1.55), rng.uniform(1.85, 2.1), rng.uniform(2.5, 2.8)]
    partials = [(f * r, a, tau / r ** 0.4) for r, a in zip(ratios, (1.0, 0.7, 0.4, 0.25)) if f * r < high * 1.6]
    return unit(modes(min(0.4, 8 * tau + 0.02), partials, 0.00003, rng))


def casing(rng, take, kind, floor):
    tau, part, brightness = FLOOR_CONTACT[floor]
    if kind == "pistol":
        tau *= 0.6
    seconds = 0.4
    out = np.zeros(int(seconds * SR))
    # Two or three contacts within a few ms (rim, then side), each a tick and the case's ring.
    at = 0.0
    for i in range(int(rng.integers(2, 4))):
        strength = (1.0, rng.uniform(0.35, 0.7), rng.uniform(0.15, 0.35))[i]
        add(out, strength * brightness * 0.6 * spike(rng, 0.00004), at)
        add(out, strength * case_ring(rng, kind, tau * rng.uniform(0.8, 1.2)), at)
        at += rng.uniform(0.0015, 0.006)
    t = seconds_axis(0.1)
    if part == "grit":
        add(out, 0.06 * crackle(rng, 0.03, int(rng.integers(3, 8)), 3000, 10000, 0.004), 0.0005)
    elif part == "tile":
        glaze = [(rng.uniform(2200, 2800), 1.0, 0.004), (rng.uniform(3500, 4200), 0.6, 0.003)]
        add(out, 0.12 * unit(modes(0.03, glaze, 0.0001, rng)), 0.0)
    elif part == "board":
        f1 = rng.uniform(600, 1100)
        board = [(f1, 1.0, 0.012), (f1 * rng.uniform(2.3, 2.6), 0.6, 0.008), (f1 * rng.uniform(4, 4.5), 0.35, 0.005)]
        add(out, 0.5 * unit(modes(0.06, board, 0.0002, rng)), 0.0)
        add(out, 0.3 * noise(rng, len(t), 800, 4000) * envelope(t, 0.0002, 0.002), 0.0)
    elif part == "plate":
        freqs = np.exp(rng.uniform(np.log(800), np.log(6000), 10))
        plate = [(f, rng.lognormal(0, 0.3) * (f / 800) ** -0.3, float(np.clip(0.12 * (800 / f) ** 0.5, 0.02, 0.12)))
                 for f in freqs]
        add(out, 0.25 * unit(modes(0.3, plate, 0.0002, rng)), 0.0)
    elif part == "soil":
        add(out, 0.8 * noise(rng, len(t), 250, 3000) * envelope(t, 0.0004, 0.004), 0.0)
        add(out, 0.25 * crackle(rng, 0.03, int(rng.integers(4, 10)), 1500, 7000, 0.006), 0.0005)
    else:
        add(out, 0.5 * noise(rng, len(t), 1500, 9000) * envelope(t, 0.002, 0.012), 0.0)   # the blades it falls through
        add(out, 0.5 * noise(rng, len(t), 200, 1500) * envelope(t, 0.0006, 0.004), 0.004)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# Hits

def helmet_hit(rng, take):
    seconds = 0.45
    out = np.zeros(int(seconds * SR))
    # The composite's fibres and resin fracturing: a dry, sharp crack.
    add(out, 1.0 * spike(rng, 0.00005), 0.0)
    add(out, 0.8 * crackle(rng, 0.02, int(rng.integers(25, 50)), 2000, 12000, 0.0015, 0.7), 0.0)
    # The shell's hollow modes, damped by its lossy resin and the head inside it.
    freqs = np.exp(rng.uniform(np.log(600), np.log(3500), 7))
    shell = [(f, rng.lognormal(0, 0.3) * (f / 600) ** -0.3, 0.02 * (600 / f) ** 0.4) for f in freqs]
    add(out, 0.55 * unit(modes(0.15, shell, 0.0002, rng)), 0.0)
    # The mount and the chinstrap's hardware clinking.
    for _ in range(int(rng.integers(1, 3))):
        add(out, 0.25 * fragment(rng, rng.uniform(3500, 6000), rng.uniform(0.004, 0.008), 3), rng.uniform(0.001, 0.02))
    # The head behind it.
    add(out, 0.45 * burst(rng, 0.08, 120, 800, 0.001, 0.012), 0.0015)
    return out


def head_hit(rng, take):
    seconds = 0.4
    out = np.zeros(int(seconds * SR))
    # The bone's fracture: a short crack.
    add(out, 0.7 * spike(rng, 0.00008), 0.0)
    add(out, 0.6 * crackle(rng, 0.012, int(rng.integers(10, 25)), 1000, 6000, 0.001, 0.6), 0.0)
    # The head's dull thud: soft tissue and the skull's low, heavily damped modes.
    add(out, 1.0 * burst(rng, 0.1, 100, 900, 0.0008, 0.014), 0.0)
    t = seconds_axis(0.1)
    add(out, 0.5 * np.sin(2 * np.pi * rng.uniform(170, 260) * t) * envelope(t, 0.001, 0.012), 0.0)
    # The wet spray: droplets and tissue thrown out, a granular hiss that falls away.
    spray = crackle(rng, 0.25, int(rng.integers(120, 220)), 1200, 7000, 0.03, 0.8)
    add(out, 0.35 * spray, 0.003)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# Writing

def sets():
    """Every set: (folder, sound path, name, take names, takes, volume, volume spread in dB, pitch, distance,
    reference)."""
    out = []
    folder, path = os.path.join(ASSETS, "sounds", "guns", "handling"), "sounds/guns/handling"
    for index, (kind, (target, distance)) in enumerate(DRYFIRE.items()):
        names, takes, volume = ws.build_set(f"dryfire_{kind}", lambda rng, i, kind=kind: dryfire(rng, i, kind),
                                            TAKES["dryfire"], 31000 + 100 * index, target, 1.6)
        out.append((folder, path, f"dryfire_{kind}", names, takes, volume, 1.0, "0.97 1.03", distance, REFERENCE))
    makers = {"rifle": draw_rifle, "pistol": draw_pistol, "grenade": draw_grenade}
    for index, (kind, (target, distance)) in enumerate(DRAWS.items()):
        names, takes, volume = ws.build_set(f"draw_{kind}", makers[kind], TAKES["draw"], 32000 + 100 * index, target)
        out.append((folder, path, f"draw_{kind}", names, takes, volume, 1.5, "0.96 1.04", distance, REFERENCE))
    folder, path = os.path.join(ASSETS, "sounds", "world", "casings"), "sounds/world/casings"
    for k, kind in enumerate(("rifle", "pistol")):
        for index, (floor, target) in enumerate(CASING_FLOORS.items()):
            name = f"brass_{kind}_{floor}"
            make = lambda rng, i, kind=kind, floor=floor: casing(rng, i, kind, floor)
            names, takes, volume = ws.build_set(name, make, TAKES["casing"], 33000 + 1000 * k + 100 * index,
                                                target + (PISTOL_CASE if kind == "pistol" else 0.0), 1.6)
            out.append((folder, path, name, names, takes, volume, 3.0, "0.92 1.08", CASING_DISTANCE, REFERENCE))
    folder, path = os.path.join(ASSETS, "sounds", "player", "hits"), "sounds/player/hits"
    makers = {"helmet_hit": helmet_hit, "head_hit": head_hit}
    for index, (name, (target, distance)) in enumerate(HITS.items()):
        names, takes, volume = ws.build_set(name, makers[name], TAKES["hit"], 34000 + 100 * index, target, 2.0)
        out.append((folder, path, name, names, takes, volume, 1.0, "0.95 1.05", distance, HIT_REFERENCE))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", help="write a WAV with every take in a row")
    parser.add_argument("--out", help="write the sounds under this folder instead of Assets (to try changes)")
    args = parser.parse_args()

    built = sets()
    preview = []
    for folder, path, name, names, takes, volume, spread, pitch, distance, reference in built:
        if args.out:
            folder = os.path.join(args.out, *path.split("/"))
        os.makedirs(folder, exist_ok=True)
        for take_name, x in zip(names, takes):
            ws.write_wav(os.path.join(folder, take_name + ".wav"), x)
        if not ws.write_event(folder, path, name, names, volume, spread, pitch, distance, reference):
            print(f"  {name}.sound exists, left as it is")
        ws.describe(name, takes, volume)
        if name.startswith("brass_"):
            # A case landing as SpentCasing plays it: each bounce a take, quieter as the case slows.
            rng = np.random.default_rng(len(preview))
            for speed in (180.0, 90.0, 45.0):
                gain = min(2.0, (speed / 240.0) ** 1.2)
                preview += [takes[int(rng.integers(len(takes)))] * volume * gain, ws.gap(speed / 2000)]
            preview.append(ws.gap(0.5))
        else:
            for x in takes:
                preview += [x * volume, ws.gap(0.4)]
            preview.append(ws.gap(0.6))
    if args.preview:
        mix = np.concatenate(preview)
        ws.write_wav(args.preview, mix / max(1.0, np.abs(mix).max()))
        print(f"preview: {args.preview}")


if __name__ == "__main__":
    main()
