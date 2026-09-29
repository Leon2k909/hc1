"""Build the FN P90's materials and sounds from Viper's MW2019 SMG pack (Workshop 2802430252, mg_papa90).

Same material conversion as ks74u_assets.py (see there): the pack packs its MW PBR textures the same way. The model
and animation side runs through the shared Kastov pipeline (Tools/port_kastov.py --weapon p90). The receiver, rails,
barrel, flash hider, iron sights and magazine are all the P90's own textures.

The magazine's shell is translucent (its vmt's $translucent: the _rgb alpha is opacity, not a metal mask). The inside of
the shell (weapon_vm_sm_papa90_mag_trans_interior) names no texture of its own (its vmt's is "${ALBEDONAME}") but uses
the shell's normal and gloss maps, so it takes the shell's material. The receiver's second material
(weapon_vm_papa90_body) is drawn with the first one's textures.

Sounds: the pack's shot and suppressed shot (one recording each). A 5.7x28mm shot is louder than a 9mm SMG's and
quieter than a 5.45mm carbine's, so the shot is levelled between the Vityaz's and the Kastov-74u's, and the suppressed
shot to the other SMGs' suppressed shots. Reload foley plays where the clips' own sound events put it: the viewmodel
QC's event 5004 frames (30 fps), resolved to files through the pack's alias list (weapon_sm_papa90.all.lua). The MW
base's generic Viewmodel.Small/Medium rattles and magazine drop are left out.

Run: python Tools/p90_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ks74u_assets import ASSETS, TOOLS, asset_path, build_material, ffmpeg, sound_event

EXTRACTED = TOOLS / "extracted" / "2802430252"
DEST = ASSETS / "Weapons" / "P90"
QC = TOOLS / "decompiled" / "papa90" / "v_papa90" / "v_papa90.qc"
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "weapon_sm_papa90.all.lua"
PAPA90 = "viper/mw/weapons/papa90"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/)
MATERIALS = {
    "weapon_vm_sm_papa90_body": ("p90_body", f"{PAPA90}/weapon_vm_sm_papa90_body"),
    # The rails, and the barrel and flash hider.
    "weapon_vm_sm_papa90_rail": ("p90_rail", f"{PAPA90}/weapon_vm_sm_papa90_rail"),
    "weapon_vm_papa90_sights": ("p90_sights", f"{PAPA90}/weapon_vm_sm_papa90_sights"),
    # The magazine's rounds, follower and feed lips.
    "weapon_vm_sm_papa90_mag": ("p90_mag", f"{PAPA90}/weapon_vm_sm_papa90_mag"),
    "weapon_vm_sm_papa90_mag_trans": ("p90_mag_shell", f"{PAPA90}/weapon_vm_sm_papa90_mag_trans"),
}
TRANSLUCENT = {"weapon_vm_sm_papa90_mag_trans"}
# Source materials drawn with another one's textures (see above).
SAME_AS = {"weapon_vm_papa90_body": "weapon_vm_sm_papa90_body",
           "weapon_vm_sm_papa90_mag_trans_interior": "weapon_vm_sm_papa90_mag_trans"}

SHOT = "weapons/papa90/weap_papa90_fire_plr_01.wav"
SUPPRESSED = "weapons/papa90/weap_papa90_sup_fire_plr_01.ogg"
# Loudest 100 ms: the shot -8.8 dB and the suppressed shot -4.1 dB, against the Vityaz's levelled 9mm -12.0 (suppressed
# -12.9), the Bizon's -11.3 (-13.4) and the Kastov-74u's 5.45 -8.2.
SHOT_GAIN_DB = -2
SUPPRESSED_GAIN_DB = -9

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
                                  if alias.startswith("wfoly_plr_sm_papa90")]
    return events


def alias_files() -> dict[str, list[str]]:
    """Sound alias -> its files under sound/ (the foley aliases have one each), without Source's ^ prefix."""
    lua = ALIASES_LUA.read_text(encoding="utf-8", errors="replace")
    return {name: [file.lstrip("^") for file in re.findall(r'"([^"]+)"', sounds)]
            for name, sounds in re.findall(r'name\s*=\s*"([^"]+)".*?sound\s*=\s*\{([^}]*)\}', lua, re.DOTALL)}


def level_shot(out: Path, source: str, name: str, gain_db: int) -> Path:
    """A shot recording, turned down gain_db and limited like the Bizon's."""
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
    fire = out / "p90.fire.sound"
    sound_event(fire, [level_shot(out, SHOT, "p90_shot", SHOT_GAIN_DB)], pitch="0.95 1.05",
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-SMG event's settings and curve, with the P90's own suppressed shot.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_smg.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    suppressed["Sounds"] = [asset_path(level_shot(out, SUPPRESSED, "p90_suppressed_shot", SUPPRESSED_GAIN_DB)
                                       .with_suffix(".vsnd"))]
    fire_suppressed = out / "p90.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events, files = clip_events(), alias_files()
    sounds: dict[str, str] = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}

    def event_for(alias: str) -> str:
        [file] = files[alias]
        name = re.sub(r"^wfoly_sm_papa90_", "", Path(file).stem)
        if name not in sounds:
            wav = out / f"p90_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"p90.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        sounds[name] = event_for(alias)
    reloads = {exported: timed(events[clip], event_for) for clip, exported in RELOAD_CLIPS.items()}
    return sounds, reloads


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials", EXTRACTED,
                                                   translucent=source in TRANSLUCENT))
                 for source, (name, base) in MATERIALS.items()}
    materials.update({source: materials[same] for source, same in SAME_AS.items()})
    manifest_path = DEST / "p90_assets.json"
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
