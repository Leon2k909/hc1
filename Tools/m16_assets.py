"""Build the M16A4's materials and sounds from easy4115's MWII M16 addon (Workshop 2962304029, mg_iw9_mike16).

Same material conversion as ks74u_assets.py (see there): the addon packs its MW PBR textures the same way. The model
and animation side runs through the shared Kastov pipeline (Tools/port_kastov.py --weapon m16). The receiver, carry
handle, barrel (with the front sight base), handguard, rail sections and stock are the M16's own textures; the flash
hider, pistol grip, 30-round magazine and its rounds are MWII's M4 parts, which the addon ships with it.

The magazine's window strip is translucent (its vmt's $translucent: the _rgb alpha is opacity, not a metal mask).

Sounds: the addon's shot and suppressed shot (MWII's M4 recordings, one take and its ADS take each), levelled to the
AK-105's: the shot SHOT_GAIN_DB, and the suppressed shot SUPPRESSED_GAIN_DB, which CoD masters almost as loud as the
open one. The shot is then voiced away from CoD's sound design by m16_shot.py, into four takes. Reload foley plays where the CoD clips' own sound events put it: the viewmodel QC's event 5004 frames
(30 fps), resolved to files through the addon's alias list (weapon_iw9_ar_mike16_plr.all.lua). CoD's generic
Viewmodel.Small/Medium rattles are left out.

Run: python Tools/m16_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import m16_shot
import ported_foley
import suppressed_shots
from ks74u_assets import ASSETS, TOOLS, asset_path, build_material, ffmpeg, sound_event

EXTRACTED = TOOLS / "extracted" / "2962304029"
DEST = ASSETS / "Weapons" / "M16"
QC = TOOLS / "decompiled" / "mike16" / "vm_iw9_mike16.qc"
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "weapon_iw9_ar_mike16_plr.all.lua"
MIKE16 = "easy/mw/weapons/iw9_mike16"
MIKE4 = "easy/mw/weapons/iw9_mike4"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/)
MATERIALS = {
    "material_25f601e245e564db": ("m16_receiver", f"{MIKE16}/material_25f601e245e564db"),
    "material_39a89cffab3d08bf": ("m16_carry_handle", f"{MIKE16}/material_39a89cffab3d08bf"),
    # The barrel, front sight base and the handguard's end caps.
    "material_bd497eb66e09b3c": ("m16_barrel", f"{MIKE16}/material_bd497eb66e09b3c"),
    "material_5762d4f7f3cdfeeb": ("m16_handguard", f"{MIKE16}/material_5762d4f7f3cdfeeb"),
    "wpn_p01_ar_mike16_rail_v0": ("m16_rail", f"{MIKE16}/wpn_p01_ar_mike16_rail_v0"),
    "material_1ae0691f40c31b94": ("m16_stock", f"{MIKE16}/material_1ae0691f40c31b94"),
    "wpn_p01_ar_mike4_brake_v0": ("m16_flash_hider", f"{MIKE4}/wpn_p01_ar_mike4_brake_v0"),
    "wpn_p01_ar_mike4_pstlgrip_v0": ("m16_pistolgrip", f"{MIKE4}/wpn_p01_ar_mike4_pstlgrip_v0"),
    "wpn_p01_ar_mike4_mag_556n_v0": ("m16_mag", f"{MIKE4}/wpn_p01_ar_mike4_mag_556n_v0"),
    "wpn_p01_ar_mike4_mag_556n_trans_v0": ("m16_mag_window", f"{MIKE4}/wpn_p01_ar_mike4_mag_556n_trans_v0"),
    "wpn_p01_ar_mike16_smag_556n_v0": ("m16_mag_15", f"{MIKE4}/wpn_p01_ar_mike16_smag_556n_v0"),
    "wpn_p01_ar_mike4_xmag_556n_v0": ("m16_mag_45", f"{MIKE4}/wpn_p01_ar_mike4_xmag_556n_v0"),
    "wpn_p01_ar_mike4_xmaglrg_556n_v0": ("m16_mag_60", f"{MIKE4}/wpn_p01_ar_mike4_xmaglrg_556n_v0"),
    "att_ammo_556n": ("m16_rounds", f"{MIKE4}/att_ammo_556n"),
}
TRANSLUCENT = {"wpn_p01_ar_mike4_mag_556n_trans_v0"}

SHOT = "iw9/wpn/ar_mike4/weap_iw9_mike4_fire_plr_01"
SUPPRESSED = "iw9/wpn/ar_mike4/weap_iw9_mike4_sup_plr_01"
# Loudest 100 ms: the shot -1.5 dB and the suppressed shot -1.8 dB, against the AK-105's levelled -4.7 and -11.8.
SHOT_GAIN_DB = -3
SUPPRESSED_GAIN_DB = -10

# The clips whose sound events are timed (kastov_weapons.M16: the 30-round magazine's reloads), by their name in the
# QC -> the name port_kastov.py exports them under.
RELOAD_CLIPS = {f"{prefix}{suffix}": f"{prefix}{suffix}" for prefix in ("reload", "reload_empty")
                for suffix in ("", "_smag", "_xmag", "_xmaglrg")}
# Deploy and holster foley: the first sound of these clips.
ONE_SHOTS = {"raise": "draw", "drop": "holster"}


def clip_events() -> dict[str, list[tuple[int, str]]]:
    """Each clip's (frame, alias) sound events from the viewmodel qc, the addon's own aliases only."""
    qc = QC.read_text(encoding="utf-8", errors="replace")
    events = {}
    for match in re.finditer(r'\$sequence "([^"]+)"(.*?)(?=\$sequence|\Z)', qc, re.DOTALL):
        events[match.group(1)] = [(int(frame), alias) for frame, alias in
                                  re.findall(r'event 5004 (\d+) "([^"]+)"', match.group(2))
                                  if alias.startswith("wfoly_plr_iw9_ar_mike16")]
    return events


def alias_files() -> dict[str, list[str]]:
    """Sound alias -> its files under sound/ (the foley aliases have one each), without Source's ^ prefix."""
    lua = ALIASES_LUA.read_text(encoding="utf-8", errors="replace")
    return {name: [file.lstrip("^") for file in re.findall(r'"([^"]+)"', sounds)]
            for name, sounds in re.findall(r'name\s*=\s*"([^"]+)".*?sound\s*=\s*\{([^}]*)\}', lua, re.DOTALL)}


def level_shots(out: Path, sources: list[str], name: str, gain_db: int) -> list[Path]:
    """Each shot recording, turned down gain_db and limited like the Bizon's."""
    shots = []
    for index, source in enumerate(sources, start=1):
        wav = out / f"{name}_{index:02d}.wav"
        ffmpeg(["-i", str(EXTRACTED / "sound" / f"{source}.wav"),
                "-af", f"volume={gain_db}dB,alimiter=limit=0.891:attack=1:release=50:level=false",
                "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
        shots.append(wav)
    return shots


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

    # Same curve as sounds/weapons/m4a1/m4_shot.sound. The two recordings, voiced into four takes (m16_shot.py).
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "m16.fire.sound"
    sound_event(fire, m16_shot.build(out), pitch=m16_shot.EVENT_PITCH,
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the M16's own suppressed shots.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    suppressed["Sounds"] = [asset_path(s.with_suffix(".vsnd")) for s in level_shots(
        out, [SUPPRESSED, f"{SUPPRESSED}_ads"], "m16_suppressed_shot", SUPPRESSED_GAIN_DB)]
    fire_suppressed = out / "m16.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events, files = clip_events(), alias_files()
    sounds: dict[str, str] = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}

    def event_for(alias: str) -> str:
        [file] = files[alias]
        name = re.sub(r"^p01_ar_mike16_", "", Path(file).stem)
        if name not in sounds:
            wav = out / f"m16_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"m16.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        sounds[name] = event_for(alias)
    reloads = {exported: timed(events[clip], event_for) for clip, exported in RELOAD_CLIPS.items()}
    # The suppressed shots, voiced like the open shot (suppressed_shots.py).
    suppressed_shots.voice("m16")
    # The foley, voiced away from CoD's sound design (ported_foley.py).
    ported_foley.voice("m16")
    return sounds, reloads


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials", EXTRACTED,
                                                   translucent=source in TRANSLUCENT))
                 for source, (name, base) in MATERIALS.items()}
    manifest_path = DEST / "m16_assets.json"
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
