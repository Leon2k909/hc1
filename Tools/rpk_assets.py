"""Build the RPK's materials and sounds from the MWII Kastovia Platform addon (its RPK, mg_iw9_rkilo).

Same source pack and material/sound conversion as ks74u_assets.py (see there); the model/animation side runs through
the shared Kastov pipeline (Tools/port_kastov.py --weapon rpk). The stocks and pistol grips are Kastovia platform
parts the 74u already builds, so they map to its materials.

Sounds: the shot is the Kastov 762's (sounds/weapons/kastov, the same 7.62x39 cartridge; kastov_prefabs.gameplay_rpk).
Reload foley plays where the CoD clips' own sound events put it: the viewmodel qc's event 5004 frames (30 fps),
resolved to files through the addon's alias list (weapon_iw9_lm_rkilo_plr.all.lua). CoD's generic
Viewmodel.Small/Medium/Large rattles and the magazine drops are left out. The drum reloads are the RPK's own foley;
the box magazines' (reload_mag, reload_xmag) are the AK's, and the 30-rounder's are the files the 74u's reload
already uses, so those map to its sound events.

Run: python Tools/rpk_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ks74u_assets import ASSETS, EXTRACTED, FOLEY as KS74U_FOLEY, asset_path, build_material, ffmpeg, sound_event

DEST = ASSETS / "Weapons" / "RPK"
KASTOV74U_MANIFEST = ASSETS / "Weapons" / "Kastov74u" / "ks74u_assets.json"
QC = Path(r"D:\tmp\hc1-mw22-tools\decompiled\rkilo\vm_iw9_rkilo\vm_iw9_rkilo.qc")
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "weapon_iw9_lm_rkilo_plr.all.lua"
RKILO = "pwci/mw/weapons/rkilo"
AKILO = "pwci/mw/weapons/akilo103"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/)
MATERIALS = {
    "wpn_p04_lm_rkilo_receiver_v0": ("rpk_receiver", f"{RKILO}/wpn_p04_lm_rkilo_receiver_v0"),
    "wpn_p04_lm_rkilo_optic_rail_v0": ("rpk_optic_rail", f"{RKILO}/wpn_p04_lm_rkilo_optic_rail_v0"),
    "wpn_p04_lm_rkilo_barrel_v0": ("rpk_barrel", f"{RKILO}/wpn_p04_lm_rkilo_barrel_v0"),
    "wpn_p04_lm_rkilo_bipod_v0": ("rpk_bipod", f"{RKILO}/wpn_p04_lm_rkilo_bipod_v0"),
    "wpn_p04_lm_rkilo_drum_762s_v0": ("rpk_drum", f"{RKILO}/wpn_p04_lm_rkilo_drum_762s_v0"),
    "wpn_p04_lm_rkilo_stockadapter_v0": ("rpk_stock_adapter", f"{RKILO}/wpn_p04_lm_rkilo_stockadapter_v0"),
    "wpn_p04_lm_rkilo_brake_v0": ("rpk_brake", f"{AKILO}/wpn_p04_lm_rkilo_brake_v0"),
    "att_ammo_762s_df": ("rpk_rounds", f"{AKILO}/att_ammo_762s_df"),
    "wpn_p04_ar_akilo_mag_762s_v0": ("rpk_mag_30", f"{AKILO}/wpn_p04_ar_akilo_mag_762s_v0"),
    "wpn_p04_ar_akilo_xmag_762s_v0": ("rpk_mag_40", f"{AKILO}/wpn_p04_ar_akilo_xmag_762s_v0"),
}
# The stocks and pistol grips (kastov_weapons.RPK.part_choices) are the 74u's: its materials.
SHARED_MATERIALS = re.compile(r"/ks74u_(stock|grip|pistolgrip)")

# The clips whose sound events are timed (kastov_weapons.RPK: the factory drum's reloads and the box magazines').
RELOAD_CLIPS = ["reload", "reload_empty", "reload_mag", "reload_empty_mag", "reload_xmag", "reload_empty_xmag"]
# Deploy and holster foley: the first sound of these clips.
ONE_SHOTS = {"raise": "draw", "drop": "holster"}


def clip_events() -> dict[str, list[tuple[int, str]]]:
    """Each clip's (frame, alias) sound events from the viewmodel qc, the addon's own aliases only."""
    qc = QC.read_text(encoding="utf-8", errors="replace")
    events = {}
    for match in re.finditer(r'\$sequence "([^"]+)"(.*?)(?=\$sequence|\Z)', qc, re.DOTALL):
        events[match.group(1)] = [(int(frame), alias) for frame, alias in
                                  re.findall(r'event 5004 (\d+) "([^"]+)"', match.group(2))
                                  if "wfoly_plr" in alias]
    return events


def alias_files() -> dict[str, list[str]]:
    """Sound alias -> its files under sound/ (the foley aliases have one each, the shots several)."""
    lua = ALIASES_LUA.read_text(encoding="utf-8", errors="replace")
    return {name: re.findall(r'"([^"]+)"', sounds)
            for name, sounds in re.findall(r'name\s*=\s*"([^"]+)".*?sound\s*=\s*\{([^}]*)\}', lua, re.DOTALL)}


def build_sounds() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """The sound events by friendly name (the file's name), and each reload clip's {seconds: event}."""
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)
    events, files = clip_events(), alias_files()
    ks74u_sounds = json.loads(KASTOV74U_MANIFEST.read_text(encoding="utf-8"))["sounds"]
    ks74u_events = {file: ks74u_sounds[name] for name, file in KS74U_FOLEY.items()}

    sounds: dict[str, str] = {}

    def event_for(alias: str) -> str:
        [file] = files[alias]
        if file in ks74u_events:
            return ks74u_events[file]
        name = re.sub(r"^(p04_)?(lm_rkilo|ar_akilo)_", "", Path(file).stem)
        if name not in sounds:
            wav = out / f"rpk_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"rpk.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        sounds[name] = event_for(alias)
    reloads = {clip: {f"{round(frame / 30, 3):g}": event_for(alias) for frame, alias in events[clip]}
               for clip in RELOAD_CLIPS}
    return sounds, reloads


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials"))
                 for source, (name, base) in MATERIALS.items()}
    shared = json.loads(KASTOV74U_MANIFEST.read_text(encoding="utf-8"))["materials"]
    materials.update({source: vmat for source, vmat in shared.items() if SHARED_MATERIALS.search(vmat)})
    manifest_path = DEST / "rpk_assets.json"
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
