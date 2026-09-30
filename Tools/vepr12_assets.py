"""Build the Vepr-12's materials and sounds from the MWII Kastovia Platform addon (its "KV Broadside", mg_iw9_vecho).

Same source pack and material/sound conversion as ks74u_assets.py (see there); the model/animation side runs through
the shared Kastov pipeline (Tools/port_kastov.py --weapon vepr12). The receiver, bolt, barrel (with its handguard,
gas block and front sight), muzzle brake, laser rail, shells and the 8-, 12- and 25-round magazines are the Vepr's
own textures. The stocks and pistol grips are Kastovia parts the 74u already builds, so they map to its materials.

Sounds: the Vepr's own shot (one recording and its ADS take), turned down SHOT_GAIN_DB to the Kastovs' level. It has
no suppressed shot: no muzzle device fits it (kastov_prefabs.PREFABS["vepr12"] has no Muzzle slot). Reload foley plays
where the CoD clips' own sound events put it: the viewmodel QC's event 5004 frames (30 fps), resolved to files through
the addon's alias list (weapon_iw9_sh_vecho_plr.all.lua). CoD's generic Viewmodel.Small/Medium rattles are left out.

Run: python Tools/vepr12_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import ported_foley
import ported_shots
from ks74u_assets import ASSETS, EXTRACTED, asset_path, build_material, ffmpeg, sound_event

DEST = ASSETS / "Weapons" / "Vepr12"
KASTOV74U_MANIFEST = ASSETS / "Weapons" / "Kastov74u" / "ks74u_assets.json"
QC = Path(r"D:\tmp\hc1-mw22-tools\decompiled\vecho\v_vecho.qc")
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "weapon_iw9_sh_vecho_plr.all.lua"
VEPR = "zeron/weapons/vepr"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/)
MATERIALS = {
    "xmaterial_4704a574fdffb129": ("vepr12_receiver", f"{VEPR}/xmaterial_4704a574fdffb129"),
    "xmaterial_4f62f15dd806b8c6": ("vepr12_receiver_parts", f"{VEPR}/xmaterial_4f62f15dd806b8c6"),
    "xmaterial_7aab6339c2de47b4": ("vepr12_barrel", f"{VEPR}/xmaterial_7aab6339c2de47b4"),
    # The handguard, gas block and front sight.
    "xmaterial_4822dce0dcf8515": ("vepr12_handguard", f"{VEPR}/xmaterial_4822dce0dcf8515"),
    "xmaterial_6cf0a285d53dd5f": ("vepr12_muzzle", f"{VEPR}/xmaterial_6cf0a285d53dd5f"),
    "xmaterial_420bac7a73018f77": ("vepr12_laser_rail", f"{VEPR}/xmaterial_420bac7a73018f77"),
    "xmaterial_279cceb0f373d162": ("vepr12_shells", f"{VEPR}/xmaterial_279cceb0f373d162"),
    "xmaterial_1e73cb6c0afc550a": ("vepr12_mag", f"{VEPR}/xmaterial_1e73cb6c0afc550a"),
    "xmaterial_31d507bc1193b324": ("vepr12_mag_12", f"{VEPR}/xmaterial_31d507bc1193b324"),
    "xmaterial_72260dae39d1fad": ("vepr12_drum", f"{VEPR}/xmaterial_72260dae39d1fad"),
}
# The stocks and pistol grips (kastov_weapons.VEPR12.part_choices) are the 74u's: its materials.
SHARED_MATERIALS = re.compile(r"/ks74u_(stock|grip|pistolgrip)")

SHOT = "zeron/vecho/shot/weap_vecho_fire_plr_shot_01_v3"
# The Vepr's shot is ~5 dB hotter than the AK-105's levelled one (loudest 100 ms: -2.7 dB against -7.8 dB). Level it
# to the Kastovs'.
SHOT_GAIN_DB = -5

# The clips whose sound events are timed (kastov_weapons.VEPR12: the 8-round magazine's reloads and the 12-round
# magazine's and drum's), by their name in the QC -> the name port_kastov.py exports them under.
RELOAD_CLIPS = {"reload": "reload", "reload_empty": "reload_empty", "reload_xmag": "reload_xmag",
                "reload_empty_xmag": "reload_empty_xmag", "reload_drummag": "reload_drummag",
                "reload_empty_drummag": "reload_empty_drummag"}
# Deploy and holster foley: the first sound of these clips.
ONE_SHOTS = {"raise": "draw", "drop": "holster"}


def clip_events() -> dict[str, list[tuple[int, str]]]:
    """Each clip's (frame, alias) sound events from the viewmodel qc, the addon's own aliases only."""
    qc = QC.read_text(encoding="utf-8", errors="replace")
    events = {}
    for match in re.finditer(r'\$sequence "([^"]+)"(.*?)(?=\$sequence|\Z)', qc, re.DOTALL):
        events[match.group(1)] = [(int(frame), alias) for frame, alias in
                                  re.findall(r'event 5004 (\d+) "([^"]+)"', match.group(2))
                                  if alias.startswith("p04_sh_vecho")]
    return events


def alias_files() -> dict[str, list[str]]:
    """Sound alias -> its files under sound/ (the foley aliases have one each), without Source's ^ prefix."""
    lua = ALIASES_LUA.read_text(encoding="utf-8", errors="replace")
    return {name: [file.lstrip("^") for file in re.findall(r'"([^"]+)"', sounds)]
            for name, sounds in re.findall(r'name\s*=\s*"([^"]+)".*?sound\s*=\s*\{([^}]*)\}', lua, re.DOTALL)}


def level_shots(out: Path, sources: list[str], name: str) -> list[Path]:
    """Each shot recording, turned down SHOT_GAIN_DB and limited like the Bizon's."""
    shots = []
    for index, source in enumerate(sources, start=1):
        wav = out / f"{name}_{index:02d}.wav"
        ffmpeg(["-i", str(EXTRACTED / "sound" / f"{source}.ogg"),
                "-af", f"volume={SHOT_GAIN_DB}dB,alimiter=limit=0.891:attack=1:release=50:level=false",
                "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
        shots.append(wav)
    return shots


def timed(events: list[tuple[int, str]], event_for) -> dict[str, str]:
    """{seconds: sound event} for a clip's (frame, alias) events. Two sounds on one frame (the magazine leaving as the
    arm moves) can't share a key, so the later one plays 10 ms after."""
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

    # Same curve as sounds/weapons/m4a1/m4_shot.sound. Two recordings only, so a little more pitch spread than the
    # other guns' eight.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "vepr12.fire.sound"
    # The rip's shot, voiced away from CoD's sound design (ported_shots.py).
    sound_event(fire, ported_shots.build("vepr12", out), pitch=ported_shots.event_pitch("vepr12"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    events, files = clip_events(), alias_files()
    sounds: dict[str, str] = {"fire": asset_path(fire)}

    def event_for(alias: str) -> str:
        [file] = files[alias]
        name = re.sub(r"^p04_sh_vecho_", "", Path(file).stem)
        if name not in sounds:
            wav = out / f"vepr12_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"vepr12.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        sounds[name] = event_for(alias)
    reloads = {exported: timed(events[clip], event_for) for clip, exported in RELOAD_CLIPS.items()}
    # The foley, voiced away from CoD's sound design (ported_foley.py).
    ported_foley.voice("vepr12")
    return sounds, reloads


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials"))
                 for source, (name, base) in MATERIALS.items()}
    shared = json.loads(KASTOV74U_MANIFEST.read_text(encoding="utf-8"))["materials"]
    materials.update({source: vmat for source, vmat in shared.items() if SHARED_MATERIALS.search(vmat)})
    manifest_path = DEST / "vepr12_assets.json"
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
