"""Build the L85A2's materials and sounds from Viper's MW2019 LMG pack (Workshop 2960120610, mg_lima86).

Same material conversion as ks74u_assets.py (see there): the pack packs its MW PBR textures the same way. The model
and animation side runs through the shared Kastov pipeline (Tools/port_kastov.py --weapon l85a2). MW2019's "SA87" is
the L86A2 light support weapon; with its short barrel it's the L85A2 rifle, which is what's built. The receiver (the
body and the front end with its rails), the butt plate, the carrying handle's iron sights, the short barrel and the
30-round magazine are its own textures. The flash hider and the laser's mount are MW's shared attachments, whose
textures are in Viper's MW attachment pack (Workshop 2459720887).

Sounds: the pack's one close shot and one suppressed shot, levelled to the M16A4's (the same round from a barrel of
about the same length). Reload foley plays where the clips' own sound events put it: the viewmodel QC's event 5004
frames (30 fps), resolved to files through the pack's alias list (weapon_lm_lima86.all.lua). The MW base's generic
Viewmodel.Small/Medium/Large rattles and magazine drop are left out.

Run: python Tools/l85a2_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import ported_foley
import ported_shots
import suppressed_shots
from ks74u_assets import ASSETS, TOOLS, asset_path, build_material, ffmpeg, sound_event

EXTRACTED = TOOLS / "extracted" / "2960120610"
ATTACHMENTS_PACK = TOOLS / "extracted" / "2459720887"
DEST = ASSETS / "Weapons" / "L85A2"
QC = TOOLS / "decompiled" / "lima86" / "v_lima86" / "v_lima86.qc"
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "weapon_lm_lima86.all.lua"
LIMA86 = "viper/mw/weapons/lima86"
MW_ATTACHMENTS = "viper/mw/attachments"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/, the pack it's in)
MATERIALS = {
    # The receiver (with the pistol grip, trigger guard, magazine well and cocking handle) and the butt plate.
    "weapon_vm_lm_lima86_body": ("l85a2_body", f"{LIMA86}/weapon_vm_lm_lima86_body", EXTRACTED),
    # The front end: the railed handguard, the gas block and the front sight's bracket.
    "weapon_vm_lm_lima86_frontend": ("l85a2_handguard", f"{LIMA86}/weapon_vm_lm_lima86_frontend", EXTRACTED),
    # The carrying handle with the rear aperture, and the front sight blade.
    "weapon_vm_lm_lima86_sights": ("l85a2_sights", f"{LIMA86}/weapon_vm_lm_lima86_sights", EXTRACTED),
    "weapon_vm_lm_lima86_barshort": ("l85a2_barrel", f"{LIMA86}/weapon_vm_lm_lima86_barshort", EXTRACTED),
    # The 30-round magazine and its rounds.
    "weapon_vm_lm_lima86_mag": ("l85a2_mag", f"{LIMA86}/weapon_vm_lm_lima86_mag", EXTRACTED),
    "attachment_vm_muzzledefault01": ("l85a2_flash_hider", f"{MW_ATTACHMENTS}/attachment_vm_muzzledefault01",
                                      ATTACHMENTS_PACK),
    "attachment_vm_laser_mount02": ("l85a2_laser_mount", f"{MW_ATTACHMENTS}/attachment_vm_laser_mount02",
                                    ATTACHMENTS_PACK),
}

SHOT = "weapons/lima86/weap_l86_fire_plr.wav"
SUPPRESSED = "weapons/lima86/weap_l86_sup_plr.wav"
# Loudest 100 ms (K-weighted), against the M16A4's voiced shot (-5.4 dB) and suppressed shot (-15.4): the rip's shot is
# -4.4 over both channels. The suppressed shot's right channel is 26 dB under its left (-7.5), so the left goes into
# both; suppressed_shots.py sets its final level against the voiced open shot.
SHOT_GAIN_DB = -1
SUPPRESSED_GAIN_DB = -8

# The clips whose sound events are timed, by their name in the QC -> the name port_kastov.py exports them under.
RELOAD_CLIPS = {"reload": "reload", "reload_empty": "reload_empty"}
# Deploy and holster foley: the first sound of these clips.
ONE_SHOTS = {"raise": "draw", "drop": "holster"}


def clip_events() -> dict[str, list[tuple[int, str]]]:
    """Each clip's (frame, alias) sound events from the viewmodel qc, the pack's own aliases only."""
    qc = QC.read_text(encoding="utf-8", errors="replace")
    events = {}
    for match in re.finditer(r'\$sequence "([^"]+)"(.*?)(?=\$sequence|\Z)', qc, re.DOTALL):
        events[match.group(1)] = [(int(frame), alias) for frame, alias in
                                  re.findall(r'event 5004 (\d+) "([^"]+)"', match.group(2))
                                  if alias.startswith("wfoly_plr_lm_lima86")]
    return events


def alias_files() -> dict[str, list[str]]:
    """Sound alias -> its files under sound/ (the foley aliases have one each), without Source's ^ prefix."""
    lua = ALIASES_LUA.read_text(encoding="utf-8", errors="replace")
    return {name: [file.lstrip("^") for file in re.findall(r'"([^"]+)"', sounds)]
            for name, sounds in re.findall(r'name\s*=\s*"([^"]+)".*?sound\s*=\s*\{([^}]*)\}', lua, re.DOTALL)}


def level_shot(out: Path, source: str, name: str, gain_db: int, mono: bool = False) -> Path:
    """A shot recording, turned up or down gain_db and limited like the Bizon's. A mono one takes the left channel
    into both at full level (ffmpeg's own downmix would take the quiet right channel in too)."""
    wav = out / f"{name}_01.wav"
    upmix = "pan=stereo|c0=c0|c1=c0," if mono else ""
    ffmpeg(["-i", str(EXTRACTED / "sound" / source),
            "-af", f"{upmix}volume={gain_db}dB,alimiter=limit=0.891:attack=1:release=50:level=false",
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

    # Same curve as sounds/weapons/m4a1/m4_shot.sound.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "l85a2.fire.sound"
    # The rip's shot, voiced away from CoD's sound design (ported_shots.py).
    sound_event(fire, ported_shots.build("l85a2", out), pitch=ported_shots.event_pitch("l85a2"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the L85A2's own suppressed shot.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    suppressed["Sounds"] = [asset_path(level_shot(out, SUPPRESSED, "l85a2_suppressed_shot", SUPPRESSED_GAIN_DB,
                                                  mono=True).with_suffix(".vsnd"))]
    fire_suppressed = out / "l85a2.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events, files = clip_events(), alias_files()
    sounds: dict[str, str] = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}

    def event_for(alias: str, name: str | None = None) -> str:
        [file] = files[alias]
        # wfoly_lm_lima86_reload_magout_01 -> reload_magout_01
        name = name or re.sub(r"^wfoly_lm_lima86_", "", Path(file).stem)
        if name not in sounds:
            wav = out / f"l85a2_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"l85a2.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        event_for(alias, name)
    reloads = {exported: timed(events[clip], event_for) for clip, exported in RELOAD_CLIPS.items()}
    # The suppressed shots, voiced like the open shot (suppressed_shots.py).
    suppressed_shots.voice("l85a2")
    # The foley, voiced away from CoD's sound design (ported_foley.py).
    ported_foley.voice("l85a2")
    return sounds, reloads


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials", pack))
                 for source, (name, base, pack) in MATERIALS.items()}
    manifest_path = DEST / "l85a2_assets.json"
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
