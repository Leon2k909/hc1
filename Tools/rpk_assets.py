"""Build the RPK's materials and sounds from the MWII Kastovia Platform addon (its RPK, mg_iw9_rkilo).

Same source pack and material/sound conversion as ks74u_assets.py (see there); the model/animation side runs through
the shared Kastov pipeline (Tools/port_kastov.py --weapon rpk). The stocks and pistol grips are Kastovia platform
parts the 74u already builds, so they map to its materials.

Sounds: the shot is the Kastov 762's (sounds/weapons/kastov, the same 7.62x39 cartridge; kastov_prefabs.gameplay_rpk).
Reload foley plays where the CoD clips' own sound events put it: the viewmodel qc's event 5004 frames (30 fps),
resolved to files through the addon's alias list (weapon_iw9_lm_rkilo_plr.all.lua). CoD's generic
Viewmodel.Small/Medium/Large rattles and the magazine drops are left out. The drum reloads are the RPK's own foley;
the box magazines' (reload_mag, reload_xmag) are the AK's, and the 30-rounder's are the files the 74u's reload
already uses. The RPK has its own copies of those (rpk_ak_*), because its foley is voiced away from CoD's sound design
(rpk_foley.py) and the 74u's isn't.

Run: python Tools/rpk_assets.py [--materials-only | --sounds-only]  (--materials-only keeps the sound events as they
are, --sounds-only the materials)
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


def own_name(file: str) -> str:
    """The name of the RPK's copy of a foley file (rpk_<name>.wav, rpk.<name>.sound). The AK's files, which the 74u
    plays too, are prefixed ak_: the 30-round magazine's reload_magout and the drum's are different files."""
    name = re.sub(r"^(p04_)?(lm_rkilo|ar_akilo)_", "", Path(file).stem)
    return f"ak_{name}" if file in KS74U_FOLEY.values() else name


def own_foley() -> dict[str, str]:
    """Each of the RPK's foley names and its file under sound/, in the order the clips first use them."""
    events, files = clip_events(), alias_files()
    foley: dict[str, str] = {}
    for alias in [events[clip][0][1] for clip in ONE_SHOTS.values()] + \
            [alias for clip in RELOAD_CLIPS for _, alias in events[clip]]:
        [file] = files[alias]
        foley.setdefault(own_name(file), file)
    return foley


def reload_clips() -> dict[str, dict[str, str]]:
    """Each reload clip's {seconds: foley name}."""
    events, files = clip_events(), alias_files()
    return {clip: {f"{round(frame / 30, 3):g}": own_name(files[alias][0]) for frame, alias in events[clip]}
            for clip in RELOAD_CLIPS}


def convert_own_foley(out: Path) -> dict[str, Path]:
    """The RPK's foley as ripped, converted to rpk_<name>.wav in `out` (mono, 44.1 kHz)."""
    wavs = {}
    for name, file in own_foley().items():
        wavs[name] = out / f"rpk_{name}.wav"
        ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le",
                str(wavs[name])])
    return wavs


def build_sounds() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """The sound events by friendly name (the file's name), and each reload clip's {seconds: event}. The foley is
    voiced away from CoD's sound design (rpk_foley.py) as it's converted."""
    import rpk_foley
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)
    wavs = convert_own_foley(out)
    rpk_foley.voice(list(wavs.values()))
    sounds: dict[str, str] = {}
    for name, wav in wavs.items():
        event = out / f"rpk.{name}.sound"
        sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
        sounds[name] = asset_path(event)
    events, files = clip_events(), alias_files()
    for name, clip in ONE_SHOTS.items():
        sounds[name] = sounds[own_name(files[events[clip][0][1]][0])]
    reloads = {clip: {t: sounds[name] for t, name in times.items()} for clip, times in reload_clips().items()}
    return sounds, reloads


def build_materials() -> dict[str, str]:
    materials = {source: asset_path(build_material(name, base, DEST / "materials"))
                 for source, (name, base) in MATERIALS.items()}
    shared = json.loads(KASTOV74U_MANIFEST.read_text(encoding="utf-8"))["materials"]
    materials.update({source: vmat for source, vmat in shared.items() if SHARED_MATERIALS.search(vmat)})
    return materials


def main() -> None:
    manifest_path = DEST / "rpk_assets.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    if "--sounds-only" not in sys.argv[1:]:
        manifest["materials"] = build_materials()
    if "--materials-only" not in sys.argv[1:]:
        manifest["sounds"], manifest["reloads"] = build_sounds()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(manifest['materials'])} materials, {len(manifest['sounds'])} sound events -> {DEST}")


if __name__ == "__main__":
    main()
