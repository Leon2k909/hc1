"""Build the SIG MCX Virtus's materials and sounds from Viper's MW2019 Assault Rifles pack (Workshop 2528829149,
mg_mcharlie: MW2019's "M13", which is the MCX Virtus SBR with its 11.5-inch barrel).

Same material conversion as ks74u_assets.py (see there): the pack packs its MW PBR textures the same way. The model
and animation side runs through the shared Kastov pipeline (Tools/port_kastov.py --weapon mcx). Everything is the
MCX's own: the lower receiver (with the pistol grip, magazine well and trigger guard), the upper (the handguard and the
top rail), the flip-up sights, the barrel and its three-prong flash hider, the 30-round polymer magazine (with its
window, translucent: the vmt's $translucent) and the factory folding telescoping stock. The gunsmith's Thin Folding
Stock is the pack's light stock and its hinge. The viewmodel's stock adapter (an adapter for MW's generic stocks) isn't
used: each MCX stock carries its own hinge.

Sounds: the shot is the pack's six dry shot recordings (weap_mcharlie_fire_plr_01..06.ogg), each levelled to the same
loudness, so every shot sounds a little different, as MW's own random pick does. The pack's alias plays a premixed wav
of the first one instead, with a long baked-in reverb tail. The subsonic set (weap_mcharlie_sub_plr_*) is the .300 BLK
conversion's and isn't used. The suppressed shot is the six suppressed recordings the same way. Reload foley plays
where the clips' own sound events put it: the viewmodel QC's event 5004 frames (30 fps) of reload and reload_empty,
resolved to files through the pack's alias list (mw_sounds_ar_mcharlie.lua). The MW base's generic
Viewmodel.Small/Medium/Large rattles and magazine drop are left out.

Run: python Tools/mcx_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
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

EXTRACTED = TOOLS / "extracted" / "2528829149"
DEST = ASSETS / "Weapons" / "MCX"
QC = TOOLS / "decompiled" / "mcharlie" / "v_mcharlie" / "v_mcharlie.qc"
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "mw_sounds_ar_mcharlie.lua"
MCHARLIE = "viper/mw/weapons/mcharlie"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/, the pack it's in)
MATERIALS = {
    # The lower receiver: the pistol grip, the magazine well, the trigger guard and the controls.
    "weapon_vm_ar_mcharlie_lower": ("mcx_lower", f"{MCHARLIE}/weapon_vm_ar_mcharlie_lower", EXTRACTED),
    # The upper receiver with the M-LOK handguard and the top rail.
    "weapon_vm_ar_mcharlie_upper": ("mcx_upper", f"{MCHARLIE}/weapon_vm_ar_mcharlie_upper", EXTRACTED),
    # The flip-up front and rear sights, raised (the factory gun) or folded down under an optic.
    "weapon_vm_ar_mcharlie_sights": ("mcx_sights", f"{MCHARLIE}/weapon_vm_ar_mcharlie_sights", EXTRACTED),
    "weapon_vm_ar_mcharlie_barrel": ("mcx_barrel", f"{MCHARLIE}/weapon_vm_ar_mcharlie_barrel", EXTRACTED),
    # The three-prong flash hider, SIG's factory one.
    "attachment_vm_muzzledefault01": ("mcx_flash_hider", f"{MCHARLIE}/attachment_vm_muzzledefault01", EXTRACTED),
    # The 30-round polymer magazine, its follower and rounds, and its window.
    "weapon_vm_ar_mcharlie_mag": ("mcx_mag", f"{MCHARLIE}/weapon_vm_ar_mcharlie_mag", EXTRACTED),
    "weapon_vm_ar_mcharlie_mag_interior": ("mcx_mag_interior", f"{MCHARLIE}/weapon_vm_ar_mcharlie_mag_interior",
                                           EXTRACTED),
    "weapon_vm_ar_mcharlie_mag_trans": ("mcx_mag_window", f"{MCHARLIE}/weapon_vm_ar_mcharlie_mag_trans", EXTRACTED),
    # The factory folding telescoping stock.
    "weapon_vm_ar_mcharlie_stock": ("mcx_stock", f"{MCHARLIE}/weapon_vm_ar_mcharlie_stock", EXTRACTED),
    # The gunsmith's Thin Folding Stock and its hinge.
    "weapon_vm_ar_mcharlie_stock_lw": ("mcx_thin_stock", f"{MCHARLIE}/weapon_vm_ar_mcharlie_stock_lw", EXTRACTED),
    "weapon_vm_ar_mcharlie_stock_hinge": ("mcx_thin_stock_hinge", f"{MCHARLIE}/weapon_vm_ar_mcharlie_stock_hinge",
                                          EXTRACTED),
}
# The magazine's window: its _rgb alpha is opacity, not a metal mask.
TRANSLUCENT = {"weapon_vm_ar_mcharlie_mag_trans"}

SHOTS = [f"viper/weapons/mcharlie/weap_mcharlie_fire_plr_{index:02d}.ogg" for index in range(1, 7)]
SUPPRESSED_SHOTS = [f"viper/weapons/mcharlie/weap_mcharlie_sup_plr_{index:02d}.ogg" for index in range(1, 7)]
# Loudest 100 ms of the two channels' mean power, limited at -1 dBFS like the FAL's: +9 gives about -6.5 dB, where the
# voiced AUG sits (-6.3) and 0.5 dB over the FAL's -7.0. A 5.56 blast from an 11.5-inch barrel burns more of its powder
# past the muzzle than a rifle-length one, and at the shooter it's about as loud as a .308 from a full-length barrel.
# The suppressed shots at -12 give about -14.5; suppressed_shots.py sets them 10 dB under the voiced open shot.
SHOT_GAIN_DB = 9
SUPPRESSED_GAIN_DB = -12

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
                                  if alias.startswith("wfoly_plr_ar_mcharlie")]
    return events


def alias_files() -> dict[str, list[str]]:
    """Sound alias -> its files under sound/, without Source's ^ prefix. The pack's sound.Add blocks give either one
    file (sound = "...") or a list of them (sound = {...})."""
    lua = ALIASES_LUA.read_text(encoding="utf-8", errors="replace")
    files = {}
    for block in re.findall(r"sound\.Add\(\s*\{(.*?)\}\s*\)", lua, re.DOTALL):
        name = re.search(r'name\s*=\s*"([^"]+)"', block)
        sounds = re.search(r'sound\s*=\s*(\{[^}]*\}|"[^"]+")', block)
        if name and sounds:
            files[name.group(1)] = [file.lstrip("^") for file in re.findall(r'"([^"]+)"', sounds.group(1))]
    return files


def level_shots(out: Path, sources: list[str], name: str, gain_db: int) -> list[Path]:
    """Shot recordings, turned up or down gain_db and limited like the Bizon's: <name>_01.wav, _02, ..."""
    wavs = []
    for index, source in enumerate(sources, 1):
        wav = out / f"{name}_{index:02d}.wav"
        ffmpeg(["-i", str(EXTRACTED / "sound" / source),
                "-af", f"volume={gain_db}dB,alimiter=limit=0.891:attack=1:release=50:level=false",
                "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
        wavs.append(wav)
    return wavs


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

    # Same curve as sounds/weapons/m4a1/m4_shot.sound. Six recordings, so less pitch spread than one would need.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "mcx.fire.sound"
    # The rip's shot, voiced away from CoD's sound design (ported_shots.py).
    sound_event(fire, ported_shots.build("mcx", out), pitch=ported_shots.event_pitch("mcx"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the MCX's own suppressed shots.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    suppressed["Sounds"] = [asset_path(wav.with_suffix(".vsnd")) for wav in
                            level_shots(out, SUPPRESSED_SHOTS, "mcx_suppressed_shot", SUPPRESSED_GAIN_DB)]
    suppressed["Pitch"] = "0.97 1.03"
    fire_suppressed = out / "mcx.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events, files = clip_events(), alias_files()
    sounds: dict[str, str] = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}

    def event_for(alias: str, name: str | None = None) -> str:
        [file] = files[alias]
        # wfoly_ar_mcharlie_reload_empty_magout_01 -> reload_empty_magout_01
        name = name or re.sub(r"^wfoly_ar_mcharlie_", "", Path(file).stem)
        if name not in sounds:
            wav = out / f"mcx_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"mcx.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        event_for(alias, name)
    reloads = {exported: timed(events[clip], event_for) for clip, exported in RELOAD_CLIPS.items()}
    # The suppressed shots, voiced like the open shot (suppressed_shots.py).
    suppressed_shots.voice("mcx")
    # The foley, voiced away from CoD's sound design (ported_foley.py).
    ported_foley.voice("mcx")
    return sounds, reloads


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials", pack,
                                                   translucent=source in TRANSLUCENT))
                 for source, (name, base, pack) in MATERIALS.items()}
    manifest_path = DEST / "mcx_assets.json"
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
