"""Build the IMI Uzi's materials and sounds from Viper's MW2019 SMG pack (Workshop 2802430252, mg_uzulu).

Same material conversion as ks74u_assets.py (see there): the pack packs its MW PBR textures the same way. The model
and animation side runs through the shared Kastov pipeline (Tools/port_kastov.py --weapon uzi). The receiver, barrel,
sights, top rail, magazines and stocks are the Uzi's own textures. The laser's mount is MW's shared attachment, whose
textures are in Viper's MW attachment pack (Workshop 2459720887).

Sounds: the pack's shot and suppressed shot (one recording each), levelled to the Vityaz's 9mm ones. Reload foley plays
where the clips' own sound events put it: the viewmodel QC's event 5004 frames (30 fps), resolved to files through the
pack's alias list (weapon_sm_uzulu.all.lua). The MW base's generic Viewmodel.Small/Medium/Large rattles and magazine
drop are left out.

Run: python Tools/uzi_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ks74u_assets import ASSETS, TOOLS, asset_path, build_material, ffmpeg, sound_event

EXTRACTED = TOOLS / "extracted" / "2802430252"
ATTACHMENTS_PACK = TOOLS / "extracted" / "2459720887"
DEST = ASSETS / "Weapons" / "Uzi"
QC = TOOLS / "decompiled" / "uzulu" / "v_uzulu" / "v_uzulu.qc"
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "weapon_sm_uzulu.all.lua"
UZULU = "viper/mw/weapons/uzulu"
MW_ATTACHMENTS = "viper/mw/attachments"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/, the pack it's in)
MATERIALS = {
    # The receiver, its front (under the barrel), the pistol grip with the trigger group, and the barrel and its nut.
    "weapon_vm_sm_uzulu_body": ("uzi_body", f"{UZULU}/weapon_vm_sm_uzulu_body", EXTRACTED),
    "weapon_vm_sm_uzulu_frontgrip": ("uzi_lower_front", f"{UZULU}/weapon_vm_sm_uzulu_frontgrip", EXTRACTED),
    "weapon_vm_sm_uzulu_pstl_grip": ("uzi_pistol_grip", f"{UZULU}/weapon_vm_sm_uzulu_pstl_grip", EXTRACTED),
    "weapon_vm_sm_uzulu_barrel": ("uzi_barrel", f"{UZULU}/weapon_vm_sm_uzulu_barrel", EXTRACTED),
    # The front and rear sights, and the top rail an optic brings.
    "weapon_vm_sm_uzulu_sight": ("uzi_sight", f"{UZULU}/weapon_vm_sm_uzulu_sight", EXTRACTED),
    "weapon_vm_sm_uzulu_v2_rail": ("uzi_rail", f"{UZULU}/weapon_vm_sm_uzulu_v2_rail", EXTRACTED),
    # The 32-round magazine (the 40 and 50 add their extensions to it) and the stocks.
    "weapon_vm_sm_uzulu_mag": ("uzi_mag", f"{UZULU}/weapon_vm_sm_uzulu_mag", EXTRACTED),
    "weapon_vm_sm_uzulu_extmag": ("uzi_mag_40", f"{UZULU}/weapon_vm_sm_uzulu_extmag", EXTRACTED),
    "weapon_vm_sm_uzulu_extmag2": ("uzi_mag_50", f"{UZULU}/weapon_vm_sm_uzulu_extmag2", EXTRACTED),
    "weapon_vm_sm_uzulu_stock": ("uzi_stock", f"{UZULU}/weapon_vm_sm_uzulu_stock", EXTRACTED),
    "weapon_vm_sm_uzulu_woodstock": ("uzi_wood_stock", f"{UZULU}/weapon_vm_sm_uzulu_woodstock", EXTRACTED),
    # The laser's mount on the receiver's right side, and its clamp.
    "attachment_vm_laser_mount03": ("uzi_laser_mount", f"{MW_ATTACHMENTS}/attachment_vm_laser_mount03",
                                    ATTACHMENTS_PACK),
    "attachment_vm_laser_mount02": ("uzi_laser_mount_clamp", f"{MW_ATTACHMENTS}/attachment_vm_laser_mount02",
                                    ATTACHMENTS_PACK),
}

SHOT = "weapons/uzulu/weap_uzulu_fire_plr_01.wav"
SUPPRESSED = "weapons/uzulu/weap_uzulu_sup_fire_plr_01.ogg"
# Loudest 100 ms of each channel: the shot -6.4 / -7.6 dB, levelled to the Vityaz's 9mm (-12.0 / -11.6). The suppressed
# shot peaks 7 dB over full scale, which the limiter holds down: +2 dB gives -8.9 / -8.7 dB over 20 ms, the Vityaz's
# -8.8 / -8.4, and -13.5 / -13.3 over 100 ms against its -12.9 / -12.5.
SHOT_GAIN_DB = -5
SUPPRESSED_GAIN_DB = 2

# The clips whose sound events are timed, by their name in the QC -> the name port_kastov.py exports them under. The
# 40- and 50-round magazines both reload with the xmag clips.
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
                                  if alias.startswith("wfoly_plr_sm_uzulu")]
    return events


def alias_files() -> dict[str, list[str]]:
    """Sound alias -> its files under sound/ (the foley aliases have one each), without Source's ^ prefix."""
    lua = ALIASES_LUA.read_text(encoding="utf-8", errors="replace")
    return {name: [file.lstrip("^") for file in re.findall(r'"([^"]+)"', sounds)]
            for name, sounds in re.findall(r'name\s*=\s*"([^"]+)".*?sound\s*=\s*\{([^}]*)\}', lua, re.DOTALL)}


def level_shot(out: Path, source: str, name: str, gain_db: int) -> Path:
    """A shot recording, turned up or down gain_db and limited like the Bizon's."""
    wav = out / f"{name}_01.wav"
    ffmpeg(["-i", str(EXTRACTED / "sound" / source),
            "-af", f"volume={gain_db}dB,alimiter=limit=0.891:attack=1:release=50:level=false",
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
    fire = out / "uzi.fire.sound"
    sound_event(fire, [level_shot(out, SHOT, "uzi_shot", SHOT_GAIN_DB)], pitch="0.95 1.05",
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-SMG event's settings and curve, with the Uzi's own suppressed shot.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_smg.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    suppressed["Sounds"] = [asset_path(level_shot(out, SUPPRESSED, "uzi_suppressed_shot", SUPPRESSED_GAIN_DB)
                                       .with_suffix(".vsnd"))]
    fire_suppressed = out / "uzi.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events, files = clip_events(), alias_files()
    sounds: dict[str, str] = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}

    def event_for(alias: str) -> str:
        [file] = files[alias]
        name = re.sub(r"^wfoly_plr_sm_uzulu_", "", Path(file).stem)
        if name not in sounds:
            wav = out / f"uzi_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"uzi.{name}.sound"
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
    manifest_path = DEST / "uzi_assets.json"
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
