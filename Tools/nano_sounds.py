"""Deterministic quiet nano-helicopter rotor loop, with a faster, vertical tail rotor.

    python Tools/nano_sounds.py

Original synthesis, no recorded manufacturer samples. 4800 rpm main and 4.2x tail;
8 seconds, periodic in phase and noise, with loop metadata. The quiet level is
baked into the PCM so flight's SoundHandle.Volume control preserves it. The loop
is 15 dB below the octocopter mix at its reference distance and attenuates out to 18 metres.
"""
import json
from pathlib import Path

import numpy as np

import octocopter_sounds as octo
import world_sounds as ws
from ordnance_sounds import periodic_noise, write_loop_meta
from ui_sounds import loudness

OUT = Path(__file__).resolve().parents[1] / "Assets/sounds/drones"
NAME, SECONDS = "nano_rotors", 8.
HOVER_RPM, TAIL_RATIO = 4800., 4.2


def build():
    rng = np.random.default_rng(4107)
    n = int(ws.SR * SECONDS)
    t = np.arange(n) / ws.SR
    sound = np.zeros(n)
    for shaft, level in ((HOVER_RPM / 60, 1.), (HOVER_RPM / 60 * TAIL_RATIO, .19)):
        shaft = round(shaft * SECONDS) / SECONDS
        phase = shaft * t + shaft * octo.wander_phase(rng, n, 2.25, .0025)
        blade_phase = 2 * phase
        tones = octo.harmonics(blade_phase, [k ** -1.65 for k in range(1, 13)], rng)
        hiss = periodic_noise(rng, n, 1100, 6000, 2)
        hiss /= max(np.sqrt(np.mean(hiss ** 2)), 1e-9)
        hiss *= .16 * (1 + .25 * np.cos(2 * np.pi * blade_phase))
        whine = .025 * np.cos(2 * np.pi * 6 * phase)
        sound += level * (tones + hiss + whine)
    sound -= sound.mean()
    sound *= .85 / np.abs(sound).max()
    volume = min(1., 10 ** ((octo.TARGET - 15 - loudness(sound)) / 20))
    return sound, volume


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    loop, volume = build()
    write_loop_meta(str(OUT), NAME)
    ws.write_wav(str(OUT / f"{NAME}.wav"), loop * volume)
    ws.write_event(str(OUT), "sounds/drones", NAME, [NAME], 1., 0., "1", 18 * 39.37, 39.37)
    # Nano occlusion should sample its own scale, not an octocopter-sized radius.
    event_path = OUT / f"{NAME}.sound"
    event = json.loads(event_path.read_text())
    event["OcclusionRadius"] = 4
    event["Volume"] = "1"
    event_path.write_text(json.dumps(event, indent=2) + "\n", encoding="utf-8")
    print(f"Nano rotors: {SECONDS:g} second loop, main 160 Hz / tail 672 Hz blade-pass, PCM gain {volume:.5f}")


if __name__ == "__main__":
    main()
