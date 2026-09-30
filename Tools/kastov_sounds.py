#!/usr/bin/env python3
"""Convert the Kastov 762's sounds (from the MW base addon) to WAV and write HC1 sound events for them.

The shot is voiced away from CoD's sound design by kastov762_shot.py, from the close shots alone. The suppressed shots
mix each close shot with its matching atmosphere tail (the MW base plays both, the tail at 0.65 volume).
Reload foley follows the CoD reload's sound events; each .sound picks randomly among its variants. It's then voiced
away from CoD's sound design by ported_foley.py.

Needs ffmpeg on PATH. Run: python Tools/kastov_sounds.py
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "Assets" / "sounds" / "weapons" / "kastov"
OUT_ASSET = "sounds/weapons/kastov"
SOURCE = Path(r"D:\tmp\hc1-mw22-tools\extracted\3803722029\sound\ak47")
TAIL_VOLUME = 0.65

FOLEY = "wfoly_rex_plr_ar_akilo_"
# event name -> source clips (random variants)
FOLEY_EVENTS = {
    "reload_01": ["reload_01"],
    "reload_02": ["reload_02", "reload_02a", "reload_02b", "reload_02c"],
    "reload_03": ["reload_03", "reload_03a", "reload_03b", "reload_03c"],
    "reload_04": ["reload_04", "reload_04a"],
    "reload_05": ["reload_05"],
    "reload_empty_01": ["reload_empty_01"],
    "reload_empty_02": ["reload_empty_02"],
    "reload_empty_03": ["reload_empty_03"],
    "reload_empty_04": ["reload_empty_04"],
    "reload_empty_05": ["reload_empty_05", "reload_empty_05a", "reload_empty_05b"],
    "reload_empty_06": ["reload_empty_06"],
    "reload_empty_07": ["reload_empty_07"],
    "raise": ["raise_01"],
}


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def mix(shot: Path, tail: Path, out: Path) -> None:
    # The tails run ~5 s; cut them to 2.5 s (with a fade) so full-auto fire doesn't stack dozens of voices.
    ffmpeg("-i", str(shot), "-i", str(tail), "-filter_complex",
           f"[1:a]volume={TAIL_VOLUME}[t];[0:a][t]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.98,"
           "afade=t=out:st=1.5:d=1.0,atrim=0:2.5",
           "-c:a", "pcm_s16le", str(out))


def convert(source: Path, out: Path) -> None:
    ffmpeg("-i", str(source), "-c:a", "pcm_s16le", str(out))


def sound_event(path: Path, clips: list[str], gunshot: bool) -> None:
    event = {
        "UI": False,
        "Volume": "1",
        "Pitch": "0.98 1.02" if gunshot else "1",
        "Decibels": 10000 if gunshot else 70,
        "SelectionMode": "Random",
        "Sounds": [f"{OUT_ASSET}/{clip}.vsnd" for clip in clips],
        "Occlusion": False,
        "AirAbsorption": not gunshot,
        "Transmission": not gunshot,
        "OcclusionRadius": 64,
        "DistanceAttenuation": True,
        "Distance": 13000 if gunshot else 1000,
        "Falloff": ([{"y": 1}, {"x": 0.23809524, "y": 0.3583625, "in": 1.329805, "out": -1.329805}, {"x": 1}]
                    if gunshot else [{"y": 1}, {"x": 1}]),
        "__references": [],
        "__version": 1,
    }
    path.write_text(json.dumps(event, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    import kastov762_shot
    OUT.mkdir(parents=True, exist_ok=True)
    shots = [path.stem for path in kastov762_shot.build(OUT)]
    suppressed = []
    for index in (1, 2, 3):
        name = f"kastov_shot_sup_{index:02d}"
        mix(SOURCE / "fire" / f"weap_rex_akilo_sup_plr_shot_{index:02d}.wav",
            SOURCE / "fire" / f"weap_rex_akilo_sup_plr_atmo_{index:02d}.wav", OUT / f"{name}.wav")
        suppressed.append(name)
    sound_event(OUT / "kastov_shot.sound", shots, gunshot=True)
    sound_event(OUT / "kastov_shot_sup.sound", suppressed, gunshot=True)
    # The suppressed shots, voiced like the open shot (suppressed_shots.py).
    import suppressed_shots
    suppressed_shots.voice("kastov762")

    for event, variants in FOLEY_EVENTS.items():
        clips = []
        for variant in variants:
            name = f"kastov_{variant}"
            convert(SOURCE / f"{FOLEY}{variant}.ogg", OUT / f"{name}.wav")
            clips.append(name)
        sound_event(OUT / f"kastov_{event}.sound", clips, gunshot=False)
    # The foley, with ak47_gunsmith.py's drum and xmag sets, voiced away from CoD's sound design (ported_foley.py).
    import ported_foley
    ported_foley.voice("kastov762")
    print(f"wrote {len(list(OUT.glob('*.wav')))} wavs and {len(list(OUT.glob('*.sound')))} sound events to {OUT}")


if __name__ == "__main__":
    main()
