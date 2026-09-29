"""Build the H&K MP7A1's materials and sounds from Viper's MW2019 SMG pack (Workshop 2802430252, mg_mpapa7).

Same material conversion as ks74u_assets.py (see there): the pack packs its MW PBR textures the same way. The model
and animation side runs through the shared Kastov pipeline (Tools/port_kastov.py --weapon mp7). The receiver, barrel,
iron sights, magazine and stock are the MP7's own textures. The flash hider and the side rail's laser mount are MW's
shared attachments, whose textures are in Viper's MW attachment pack (Workshop 2459720887).

Sounds: the pack's shot and suppressed shot (one recording each). The 4.6x30mm round carries about the energy of the
P90's 5.7x28mm, so the shot is levelled to the P90's (between the 9mm SMGs' and the Kastov-74u's 5.45). The suppressed
shot is as loud as its short burst allows: at the quiet end of the other suppressed guns'. Reload foley plays where
the clips' own sound events put it: the viewmodel QC's event 5004 frames (30 fps), resolved to files through the
pack's alias list (weapon_sm_mpapa7.all.lua). The MW base's generic Viewmodel.Small/Medium/Large rattles and magazine
drop are left out.

Run: python Tools/mp7_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ks74u_assets import ASSETS, TOOLS, asset_path, build_material, ffmpeg, sound_event

EXTRACTED = TOOLS / "extracted" / "2802430252"
ATTACHMENTS_PACK = TOOLS / "extracted" / "2459720887"
DEST = ASSETS / "Weapons" / "MP7"
QC = TOOLS / "decompiled" / "mpapa7" / "v_mpapa7" / "v_mpapa7.qc"
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "weapon_sm_mpapa7.all.lua"
MPAPA7 = "viper/mw/weapons/mpapa7"
MW_ATTACHMENTS = "viper/mw/attachments"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/, the pack it's in)
MATERIALS = {
    # The receiver (with its rails and pistol grip) and the barrel.
    "weapon_vm_sm_mpapa7_body": ("mp7_body", f"{MPAPA7}/weapon_vm_sm_mpapa7_body", EXTRACTED),
    "weapon_vm_sm_mpapa7_sight": ("mp7_sight", f"{MPAPA7}/weapon_vm_sm_mpapa7_sight", EXTRACTED),
    # The magazine and its rounds.
    "weapon_vm_sm_mpapa7_mag": ("mp7_mag", f"{MPAPA7}/weapon_vm_sm_mpapa7_mag", EXTRACTED),
    "weapon_vm_sm_mpapa7_stock": ("mp7_stock", f"{MPAPA7}/weapon_vm_sm_mpapa7_stock", EXTRACTED),
    "attachment_vm_muzzledefault04": ("mp7_flash_hider", f"{MW_ATTACHMENTS}/attachment_vm_muzzledefault04",
                                      ATTACHMENTS_PACK),
    "attachment_vm_laser_mount03": ("mp7_laser_mount", f"{MW_ATTACHMENTS}/attachment_vm_laser_mount03",
                                    ATTACHMENTS_PACK),
}

SHOT = "weapons/mpapa7/weap_mpapa7_fire_plr_01.wav"
SUPPRESSED = "weapons/mpapa7/weap_mpapa7_sup_fire_plr_01.ogg"
# Loudest 100 ms of each channel: the shot -4.5 / -8.3 dB, levelled like the P90's (-5.7 / -12.9 from -3.7 / -10.9).
# The suppressed shot is mono, so both channels get all of it. It's a 20 ms burst peaking 7 dB over full scale, which
# the limiter holds down, so turning it up hardly makes it louder: +4 dB gives -10.4 dB over 20 ms and -15.9 over
# 100 ms, against the other suppressed guns' -8.3 to -12.8 and -12.1 to -14.8.
SHOT_GAIN_DB = -2
SUPPRESSED_GAIN_DB = 4

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
                                  if alias.startswith("wfoly_plr_sm_mpapa7")]
    return events


def alias_files() -> dict[str, list[str]]:
    """Sound alias -> its files under sound/ (the foley aliases have one each), without Source's ^ prefix."""
    lua = ALIASES_LUA.read_text(encoding="utf-8", errors="replace")
    return {name: [file.lstrip("^") for file in re.findall(r'"([^"]+)"', sounds)]
            for name, sounds in re.findall(r'name\s*=\s*"([^"]+)".*?sound\s*=\s*\{([^}]*)\}', lua, re.DOTALL)}


def level_shot(out: Path, source: str, name: str, gain_db: int, mono: bool = False) -> Path:
    """A shot recording, turned up or down gain_db and limited like the Bizon's. A mono one goes into both channels at
    full level (ffmpeg's own upmix would take 3 dB off each)."""
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

    # Same curve as sounds/weapons/m4a1/m4_shot.sound. One recording only, so more pitch spread than the other guns'.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "mp7.fire.sound"
    sound_event(fire, [level_shot(out, SHOT, "mp7_shot", SHOT_GAIN_DB)], pitch="0.95 1.05",
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-SMG event's settings and curve, with the MP7's own suppressed shot.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_smg.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    suppressed["Sounds"] = [asset_path(level_shot(out, SUPPRESSED, "mp7_suppressed_shot", SUPPRESSED_GAIN_DB,
                                                  mono=True).with_suffix(".vsnd"))]
    fire_suppressed = out / "mp7.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events, files = clip_events(), alias_files()
    sounds: dict[str, str] = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}

    def event_for(alias: str) -> str:
        [file] = files[alias]
        name = re.sub(r"^wfoly_plr_sm_mpapa7_", "", Path(file).stem)
        if name not in sounds:
            wav = out / f"mp7_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"mp7.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        sounds[name] = event_for(alias)
    reloads = {exported: timed(events[clip], event_for) for clip, exported in RELOAD_CLIPS.items()}
    return sounds, reloads


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials", pack))
                 for source, (name, base, pack) in MATERIALS.items()}
    manifest_path = DEST / "mp7_assets.json"
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
