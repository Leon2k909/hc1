"""Build the SIG Sauer M18's materials and sounds from Viper's MW2019 pistol pack (Workshop 2459723892, mg_p320).

Same material conversion as ks74u_assets.py (see there): the pack packs its MW PBR textures the same way. The model
and animation side runs through the shared Kastov pipeline (Tools/port_kastov.py --weapon m18). The frame, slides,
sights and magazines are the pistol's own textures. The suppressor's (a _c/_m/_n set) is left out with the suppressor:
the M18's barrel isn't threaded.

Sounds: the pack's shot, levelled to the Vityaz's 9mm. The pack plays it as a distance-variant sound (Source's ^ prefix:
the left channel is the shot up close, the right the far one), so only its left channel is used, in both channels.
Reload foley plays where the clips' own sound events put it: the viewmodel QC's event 5004 frames (30 fps), resolved to
files through the pack's alias list (weapon_pi_papa320.all.lua). The MW base's generic Viewmodel.Small/Medium/Large
rattles and magazine drop are left out.

Run: python Tools/p320_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ks74u_assets import ASSETS, TOOLS, asset_path, build_material, ffmpeg, sound_event

EXTRACTED = TOOLS / "extracted" / "2459723892"
DEST = ASSETS / "Weapons" / "M18"
QC = TOOLS / "decompiled" / "p320" / "v_p320.qc"
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "weapon_pi_papa320.all.lua"
P320 = "viper/mw/weapons/p320/weapon_vm_pi_papa320"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/)
MATERIALS = {
    # The polymer grip module with the trigger, and the barrel (the slide models carry it in the frame's material).
    "weapon_vm_pi_papa320_frame": ("m18_frame", f"{P320}_frame"),
    # The slides: the factory one, the black one, the one with lightening cuts, and the long one with its barrel.
    "weapon_vm_pi_papa320_slide": ("m18_slide", f"{P320}_slide"),
    "weapon_vm_pi_papa320_slide_black": ("m18_slide_black", f"{P320}_slide_black"),
    "weapon_vm_pi_papa320_slide_vented": ("m18_slide_vented", f"{P320}_slide_vented"),
    "weapon_vm_pi_papa320_barrel_ext": ("m18_slide_long", f"{P320}_barrel_ext"),
    # The front and rear sights (each slide model's "sight" bodygroup).
    "weapon_vm_pi_papa320_sights": ("m18_sights", f"{P320}_sights"),
    # The 17-round magazine, then the 21 and the 32.
    "weapon_vm_pi_papa320_mag": ("m18_mag", f"{P320}_mag"),
    "weapon_vm_pi_papa320_mag_ext": ("m18_mag_21", f"{P320}_mag_ext"),
    "weapon_vm_pi_papa320_mag_ext2": ("m18_mag_32", f"{P320}_mag_ext2"),
}

SHOT = "weapons/papa320/weap_papa320_fire_plr_01.wav"
# The left channel's loudest 100 ms is -5.4 dB and 20 ms -2.0 dB. -6 dB puts it at -11.4 and -8.0, against the
# Vityaz's 9mm shot's -12.3 / -11.9 and -7.7 / -7.6: a pistol's short barrel is a little louder at the shooter.
SHOT_GAIN_DB = -6

# The clips whose sound events are timed, by their name in the QC -> the name port_kastov.py exports them under. The
# 21-round magazine reloads with the xmag clips.
RELOAD_CLIPS = {"reload": "reload", "reload_empty": "reload_empty", "reload_xmag": "reload_xmag",
                "reload_empty_xmag": "reload_empty_xmag"}
# Deploy and holster foley: the first sound of these clips.
ONE_SHOTS = {"raise": "draw", "drop": "holster"}


def clip_events() -> dict[str, list[tuple[int, str]]]:
    """Each clip's (frame, alias) sound events from the viewmodel qc, the pack's own aliases only."""
    qc = QC.read_text(encoding="utf-8", errors="replace")
    events = {}
    for match in re.finditer(r'\$sequence "([^"]+)"(.*?)(?=\$sequence|\Z)', qc, re.DOTALL):
        events[match.group(1)] = [(int(frame), alias) for frame, alias in
                                  re.findall(r'event 5004 (\d+) "([^"]+)"', match.group(2))
                                  if alias.startswith("wfoly_plr_pi_papa320")]
    return events


def alias_files() -> dict[str, list[str]]:
    """Sound alias -> its files under sound/ (the foley aliases have one each), without Source's ^ prefix."""
    lua = ALIASES_LUA.read_text(encoding="utf-8", errors="replace")
    return {name: [file.lstrip("^") for file in re.findall(r'"([^"]+)"', sounds)]
            for name, sounds in re.findall(r'name\s*=\s*"([^"]+)".*?sound\s*=\s*\{([^}]*)\}', lua, re.DOTALL)}


def level_shot(out: Path, source: str, name: str, gain_db: int) -> Path:
    """The near (left) channel of a distance-variant shot in both channels, turned up or down gain_db and limited like
    the Bizon's."""
    wav = out / f"{name}_01.wav"
    ffmpeg(["-i", str(EXTRACTED / "sound" / source),
            "-af", f"pan=stereo|c0=c0|c1=c0,volume={gain_db}dB,alimiter=limit=0.891:attack=1:release=50:level=false",
            "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
    return wav


def timed(events: list[tuple[int, str]], event_for) -> dict[str, str]:
    """{seconds: sound event} for a clip's (frame, alias) events. Two sounds on one frame can't share a key, so the
    later one plays 10 ms after."""
    sounds: dict[str, str] = {}
    for frame, alias in events:
        seconds = frame / 30
        while f"{round(seconds, 3):g}" in sounds:
            seconds += 0.01
        sounds[f"{round(seconds, 3):g}"] = event_for(alias)
    return sounds


def build_sounds() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """The sound events by friendly name (the file's name), and each reload clip's {seconds: event}."""
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)

    # Same curve as sounds/weapons/m4a1/m4_shot.sound. One recording only, so more pitch spread than the other guns'.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "m18.fire.sound"
    sound_event(fire, [level_shot(out, SHOT, "m18_shot", SHOT_GAIN_DB)], pitch="0.95 1.05",
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    events, files = clip_events(), alias_files()
    sounds: dict[str, str] = {"fire": asset_path(fire)}

    def event_for(alias: str) -> str:
        [file] = files[alias]
        name = re.sub(r"^wfoly_plr_pi_papa320_", "", Path(file).stem)
        if name not in sounds:
            wav = out / f"m18_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"m18.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        sounds[name] = event_for(alias)
    reloads = {exported: timed(events[clip], event_for) for clip, exported in RELOAD_CLIPS.items()}
    return sounds, reloads


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials", EXTRACTED))
                 for source, (name, base) in MATERIALS.items()}
    manifest_path = DEST / "m18_assets.json"
    if "--materials-only" in sys.argv[1:]:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["materials"] = materials
    else:
        sounds, reloads = build_sounds()
        manifest = {"materials": materials, "sounds": sounds, "reloads": reloads}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(materials)} materials, {len(manifest['sounds'])} sound events -> {DEST}")


if __name__ == "__main__":
    main()
