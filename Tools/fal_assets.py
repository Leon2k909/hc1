"""Build the FN FAL's materials and sounds from Viper's MW2019 Assault Rifles pack (Workshop 2528829149, mg_falima).

Same material conversion as ks74u_assets.py (see there): the pack packs its MW PBR textures the same way. The model
and animation side runs through the shared Kastov pipeline (Tools/port_kastov.py --weapon fal). The receiver (with the
optic rail), the rear sight, the handguard, the barrel with its flash hider, the 20-round magazine and the stock are
the FAL's own textures, and so are the gunsmith parts': the Para's folding stock, the 30-round magazine and the
18-inch barrel. The laser's mount on the handguard and the 18-inch barrel's short flash hider are MW's shared
attachments, whose textures are in Viper's MW attachment pack (Workshop 2459720887).

Sounds: the shot is the pack's six dry shot recordings (weap_falima_fire_plr_01..06.ogg), each levelled to the same
loudness, so every shot sounds a little different, as MW's own random pick does. The pack's alias plays a premixed wav
of the first one instead, with a long baked-in reverb tail. The suppressed shot is the six suppressed recordings the
same way (the premixed wav's right channel is silent). Reload foley plays where the clips' own sound events put it:
the viewmodel QC's event 5004 frames (30 fps) of reload and reload_empty, and of the 30-round magazine's reload_xmag
and reload_empty_xmag, resolved to files through the pack's alias list (mw_sounds_ar_falima.lua). The MW base's
generic Viewmodel.Small/Medium/Large rattles and magazine drop are left out.

Run: python Tools/fal_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
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
ATTACHMENTS_PACK = TOOLS / "extracted" / "2459720887"
DEST = ASSETS / "Weapons" / "FAL"
QC = TOOLS / "decompiled" / "falima" / "v_falima" / "v_falima.qc"
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "mw_sounds_ar_falima.lua"
FALIMA = "viper/mw/weapons/falima"
MW_ATTACHMENTS = "viper/mw/attachments"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/, the pack it's in)
MATERIALS = {
    # The receiver, with the carrying handle, the pistol grip and trigger guard, and the optic rail (a bodygroup).
    "weapon_vm_ar_falima_upper": ("fal_receiver", f"{FALIMA}/weapon_vm_ar_falima_upper", EXTRACTED),
    # The rear sight, raised (the factory gun) or folded down under an optic.
    "weapon_vm_ar_falima_sights": ("fal_rear_sight", f"{FALIMA}/weapon_vm_ar_falima_sights", EXTRACTED),
    # The handguard, the gas block and the front sight.
    "weapon_vm_ar_falima_forend": ("fal_forend", f"{FALIMA}/weapon_vm_ar_falima_forend", EXTRACTED),
    # The barrel ahead of the gas block, and the flash hider.
    "weapon_vm_ar_falima_barrel": ("fal_barrel", f"{FALIMA}/weapon_vm_ar_falima_barrel", EXTRACTED),
    # The 20-round magazine and its rounds.
    "weapon_vm_ar_falima_mag": ("fal_mag", f"{FALIMA}/weapon_vm_ar_falima_mag", EXTRACTED),
    "weapon_vm_ar_falima_stock": ("fal_stock", f"{FALIMA}/weapon_vm_ar_falima_stock", EXTRACTED),
    "attachment_vm_laser_mount02": ("fal_laser_mount", f"{MW_ATTACHMENTS}/attachment_vm_laser_mount02",
                                    ATTACHMENTS_PACK),
    # The gunsmith parts: the Para's tubular folding stock, the 30-round magazine and its rounds, and the 18-inch
    # barrel with its short flash hider.
    "weapon_vm_ar_falima_stock_lw": ("fal_para_stock", f"{FALIMA}/weapon_vm_ar_falima_stock_lw", EXTRACTED),
    "weapon_vm_ar_falima_mag_ext2": ("fal_mag_30", f"{FALIMA}/weapon_vm_ar_falima_mag_ext2", EXTRACTED),
    "weapon_vm_ar_falima_shortbarrel": ("fal_short_barrel", f"{FALIMA}/weapon_vm_ar_falima_shortbarrel", EXTRACTED),
    "attachment_vm_muzzledefault01": ("fal_short_flash_hider", f"{MW_ATTACHMENTS}/attachment_vm_muzzledefault01",
                                      ATTACHMENTS_PACK),
}

SHOTS = [f"viper/weapons/falima/weap_falima_fire_plr_{index:02d}.ogg" for index in range(1, 7)]
SUPPRESSED_SHOTS = [f"viper/weapons/falima/weap_falima_sup_plr_{index:02d}.ogg" for index in range(1, 7)]
# Loudest 100 ms of the two channels' mean power. The recordings' peaks run 8 dB over full scale, so the limiter
# (-1 dBFS) sets the level more than the gain does: +8 gives -6.6 to -6.9, 0.7-1 dB over the 5.56 rifles' -7.6 (the M16A4,
# AUG and AK-105). A .308 is about that much louder than a .223 at the shooter, and the SCAR-H's -4.6 is louder
# still, as its short barrel would be. The suppressed shots at -12 give about -14.3, as far over the 5.56 rifles'
# suppressed -15.0.
SHOT_GAIN_DB = 8
SUPPRESSED_GAIN_DB = -12

# The clips whose sound events are timed, by their name in the QC -> the name port_kastov.py exports them under.
RELOAD_CLIPS = {"reload": "reload", "reload_empty": "reload_empty",
                "reload_xmag": "reload_xmag", "reload_empty_xmag": "reload_empty_xmag"}
# Deploy and holster foley: the first sound of these clips.
ONE_SHOTS = {"raise": "draw", "drop": "holster"}


def clip_events() -> dict[str, list[tuple[int, str]]]:
    """Each clip's (frame, alias) sound events from the viewmodel qc, the pack's own aliases only."""
    qc = QC.read_text(encoding="utf-8", errors="replace")
    events = {}
    for match in re.finditer(r'\$sequence "([^"]+)"(.*?)(?=\$sequence|\Z)', qc, re.DOTALL):
        events[match.group(1)] = [(int(frame), alias) for frame, alias in
                                  re.findall(r'event 5004 (\d+) "([^"]+)"', match.group(2))
                                  if alias.startswith("wfoly_plr_ar_falima")]
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
    fire = out / "fal.fire.sound"
    # The rip's shot, voiced away from CoD's sound design (ported_shots.py).
    sound_event(fire, ported_shots.build("fal", out), pitch=ported_shots.event_pitch("fal"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the FAL's own suppressed shots.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    suppressed["Sounds"] = [asset_path(wav.with_suffix(".vsnd")) for wav in
                            level_shots(out, SUPPRESSED_SHOTS, "fal_suppressed_shot", SUPPRESSED_GAIN_DB)]
    suppressed["Pitch"] = "0.97 1.03"
    fire_suppressed = out / "fal.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events, files = clip_events(), alias_files()
    sounds: dict[str, str] = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}

    def event_for(alias: str, name: str | None = None) -> str:
        [file] = files[alias]
        # wfoly_plr_ar_falima_reload_empty_magout_01 -> reload_empty_magout_01
        name = name or re.sub(r"^wfoly_plr_ar_falima_", "", Path(file).stem)
        if name not in sounds:
            wav = out / f"fal_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"fal.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        event_for(alias, name)
    reloads = {exported: timed(events[clip], event_for) for clip, exported in RELOAD_CLIPS.items()}
    # The suppressed shots, voiced like the open shot (suppressed_shots.py).
    suppressed_shots.voice("fal")
    # The foley, voiced away from CoD's sound design (ported_foley.py).
    ported_foley.voice("fal")
    return sounds, reloads


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials", pack))
                 for source, (name, base, pack) in MATERIALS.items()}
    manifest_path = DEST / "fal_assets.json"
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
