"""Build the AK-105's materials and sounds from the MWII Kastovia Platform addon (its "Kastov 545", mg_iw9_akilo105).

Same source pack and material/sound conversion as ks74u_assets.py (see there); the model/animation side runs through
the shared Kastov pipeline (Tools/port_kastov.py --weapon ak105). The receiver, side rail and barrel (with its gas
block and front sight) are the AK platform's textures, the handguard, stock, pistol grip and 30- and 60-round
magazines the AK-105's own. The muzzle booster, the rounds, the 20- and 45-round magazines and the other stocks and
grips are Kastovia parts the 74u already builds, so they map to its materials.

Sounds: the AK-105's own shot (one recording and its ADS take) and suppressed shots, turned down SHOT_GAIN_DB to the
74u's level (the same 5.45x39 cartridge). The shot is then voiced away from CoD's sound design by ak105_shot.py, into
four takes. Reload foley plays where the CoD clips' own sound events put it: the
viewmodel QC's event 5004 frames (30 fps), resolved to files through the addon's alias list
(weapon_iw9_ar_akilo105_plr.all.lua). CoD's generic Viewmodel.Small/Medium rattles and the magazine drops are left out.

Run: python Tools/ak105_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import ak105_shot
from ks74u_assets import ASSETS, EXTRACTED, FOLEY as KS74U_FOLEY, asset_path, build_material, ffmpeg, sound_event

DEST = ASSETS / "Weapons" / "AK105"
KASTOV74U_MANIFEST = ASSETS / "Weapons" / "Kastov74u" / "ks74u_assets.json"
QC = Path(r"D:\tmp\hc1-mw22-tools\decompiled\akilo105\vm_iw9_akilo105.qc")
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "weapon_iw9_ar_akilo105_plr.all.lua"
AKILO = "pwci/mw/weapons/akilo103"
AK105 = "pwci/mw/weapons/akilo105"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/)
MATERIALS = {
    "wpn_p04_ar_akilo_receiver_v0": ("ak105_receiver", f"{AKILO}/wpn_p04_ar_akilo_receiver_v0"),
    "wpn_p04_ar_akilo_rail_v0": ("ak105_rail", f"{AKILO}/wpn_p04_ar_akilo_rail_v0"),
    # The barrel, gas block, gas tube and front sight.
    "wpn_p04_ar_akilo_barhvyshort_v0": ("ak105_barrel", f"{AKILO}/wpn_p04_ar_akilo_barhvyshort_v0"),
    "wpn_p04_ar_akilo105_barrel_v0": ("ak105_handguard", f"{AK105}/wpn_p04_ar_akilo105_barrel_v0"),
    "wpn_p04_ar_akilo105_stock_v0": ("ak105_stock", f"{AK105}/wpn_p04_ar_akilo105_stock_v0"),
    "wpn_p04_ar_akilo105_pstlgrip_v0": ("ak105_pistolgrip", f"{AK105}/wpn_p04_ar_akilo105_pstlgrip_v0"),
    "wpn_p04_ar_akilo105_mag_545s_v0": ("ak105_mag", f"{AK105}/wpn_p04_ar_akilo105_mag_545s_v0"),
    "wpn_p04_ar_akilo105_xmaglrg_545s_v0": ("ak105_mag_60", f"{AK105}/wpn_p04_ar_akilo105_xmaglrg_545s_v0"),
}
# The muzzle booster, the rounds, the 20- and 45-round magazines and the other stocks and grips
# (kastov_weapons.AK105.part_choices) are the 74u's: its materials.
SHARED_MATERIALS = re.compile(r"/ks74u_(stock|grip|pistolgrip|muzzle|rounds|mag_20|mag_45)")
# The 60-round magazine's rounds (att_ammo_545s.vmt) draw the 74u's rounds texture.
ROUNDS = ("att_ammo_545s", "xmaterial_73f6e083c54472b0")

SHOT = "iw9/wpn/ar_akilo105/weap_akilo105_fire_plr_shot_01"
SUPPRESSED = "zeron/ar_akilo105/fire/weap_akilo105_sup_plr_shot_{:02d}"
SUPPRESSED_SHOTS = 8
# The AK-105's shot is ~3.5 dB hotter than the 74u's mixed shot and mechanism (ks74u_shot_*.wav: loudest 100 ms
# -7.9 dB against -4.2 dB). Level it, and the suppressed shots with it.
SHOT_GAIN_DB = -3

# The clips whose sound events are timed (kastov_weapons.AK105: the factory magazine's reloads and the 20-, 45- and
# 60-round magazines'), by their name in the QC -> the name port_kastov.py exports them under.
RELOAD_CLIPS = {"reload": "reload", "reload_empty": "reload_empty", "reload_smag": "reload_smag",
                "reload_empty_smag": "reload_empty_smag", "reload_xmag": "reload_xmag",
                "reload_empty_xmag": "reload_empty_xmag", "reload_xmaglrg": "reload_xmaglrg",
                "reload_xmaglrg_empty": "reload_empty_xmaglrg"}
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
    """Sound alias -> its files under sound/ (the foley aliases have one each)."""
    lua = ALIASES_LUA.read_text(encoding="utf-8", errors="replace")
    return {name: re.findall(r'"([^"]+)"', sounds)
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


def build_sounds() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """The sound events by friendly name (the file's name), and each reload clip's {seconds: event}."""
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)

    # Same curve as sounds/weapons/m4a1/m4_shot.sound. The two recordings, voiced into four takes (ak105_shot.py).
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "ak105.fire.sound"
    sound_event(fire, ak105_shot.build(out), pitch=ak105_shot.EVENT_PITCH,
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the AK-105's own suppressed shots.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    suppressed["Sounds"] = [asset_path(s.with_suffix(".vsnd")) for s in level_shots(
        out, [SUPPRESSED.format(index) for index in range(1, SUPPRESSED_SHOTS + 1)], "ak105_suppressed_shot")]
    fire_suppressed = out / "ak105.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events, files = clip_events(), alias_files()
    ks74u_sounds = json.loads(KASTOV74U_MANIFEST.read_text(encoding="utf-8"))["sounds"]
    ks74u_events = {file: ks74u_sounds[name] for name, file in KS74U_FOLEY.items()}
    sounds: dict[str, str] = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}

    def event_for(alias: str) -> str:
        [file] = files[alias]
        if file in ks74u_events:
            return ks74u_events[file]
        name = re.sub(r"^(p04_)?ar_akilo(105)?_", "", Path(file).stem)
        if name not in sounds:
            wav = out / f"ak105_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"ak105.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        sounds[name] = event_for(alias)
    reloads = {exported: {f"{round(frame / 30, 3):g}": event_for(alias) for frame, alias in events[clip]}
               for clip, exported in RELOAD_CLIPS.items()}
    return sounds, reloads


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials"))
                 for source, (name, base) in MATERIALS.items()}
    shared = json.loads(KASTOV74U_MANIFEST.read_text(encoding="utf-8"))["materials"]
    materials[ROUNDS[0]] = shared[ROUNDS[1]]
    materials.update({source: vmat for source, vmat in shared.items() if SHARED_MATERIALS.search(vmat)})
    manifest_path = DEST / "ak105_assets.json"
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
