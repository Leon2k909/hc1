"""Build the Steyr AUG A3's materials and sounds from Viper's MW2019 SMG pack (Workshop 2802430252, mg_augolf).

Same material conversion as ks74u_assets.py (see there): the pack packs its MW PBR textures the same way. The model
and animation side runs through the shared Kastov pipeline (Tools/port_kastov.py --weapon aug). The stock, its top
rail and iron sights, the folding foregrip, the 407 mm barrel and the 30-round magazine are the AUG's own textures.
The flash hider and the barrel's laser mount are MW's shared attachments, whose textures are in Viper's MW attachment
pack (Workshop 2459720887).

Sounds: MW2019's AUG is a 9mm gun until its 5.56 magazine goes in, which swaps in the 5.56 shot and suppressed shot
(the lua's doCalConversionStats: the weap_augolf_cal_plr aliases), so those are the ones used. The shot is levelled
to the M16A4's (the same round), and so is the suppressed shot. Reload foley plays where the clips' own sound events
put it: the viewmodel QC's event 5004 frames (30 fps) of the 5.56 magazine's reloads (reload_armag and
reload_empty_armag, whose foley is the pack's "waffle" magazine set), resolved to files through the pack's alias list
(weapon_sm_augolf.all.lua). The MW base's generic Viewmodel.Small/Medium rattles and magazine drop are left out.

Run: python Tools/aug_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import ported_foley
import ported_shots
import suppressed_shots
from ks74u_assets import ASSETS, TOOLS, asset_path, build_material as build_source_material, ffmpeg, sound_event

EXTRACTED = TOOLS / "extracted" / "2802430252"
ATTACHMENTS_PACK = TOOLS / "extracted" / "2459720887"
DEST = ASSETS / "Weapons" / "AUG"
QC = TOOLS / "decompiled" / "augolf" / "v_augolf" / "v_augolf.qc"
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "weapon_sm_augolf.all.lua"
AUGOLF = "viper/mw/weapons/augolf"
MW_ATTACHMENTS = "viper/mw/attachments"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/, the pack it's in)
MATERIALS = {
    # The stock (the receiver housing, with the pistol grip, trigger guard and butt).
    "weapon_vm_sm_augolf_body": ("aug_stock", f"{AUGOLF}/weapon_vm_sm_augolf_body", EXTRACTED),
    # The receiver's top: the rail, the barrel's collar and the front of the housing.
    "weapon_vm_sm_augolf_upper": ("aug_upper", f"{AUGOLF}/weapon_vm_sm_augolf_upper", EXTRACTED),
    "weapon_vm_sm_augolf_sights": ("aug_sights", f"{AUGOLF}/weapon_vm_sm_augolf_sights", EXTRACTED),
    "weapon_vm_sm_augolf_vertgrip": ("aug_foregrip", f"{AUGOLF}/weapon_vm_sm_augolf_vertgrip", EXTRACTED),
    # The barrel, and its rear section with the gas cylinder (the long barrel's texture).
    "weapon_vm_sm_augolf_ar_barrel": ("aug_barrel", f"{AUGOLF}/weapon_vm_sm_augolf_ar_barrel", EXTRACTED),
    "weapon_vm_sm_augolf_lmg_barrel": ("aug_barrel_rear", f"{AUGOLF}/weapon_vm_sm_augolf_lmg_barrel", EXTRACTED),
    # The 30-round magazine and its rounds.
    "weapon_vm_sm_augolf_ar_mag": ("aug_mag", f"{AUGOLF}/weapon_vm_sm_augolf_ar_mag", EXTRACTED),
    "weapon_vm_sm_augolf_stocklight": ("aug_stock_light", f"{AUGOLF}/weapon_vm_sm_augolf_stocklight", EXTRACTED),
    "weapon_vm_sm_augolf_stocktactical": ("aug_stock_tactical", f"{AUGOLF}/weapon_vm_sm_augolf_stocktactical", EXTRACTED),
    "weapon_vm_sm_augolf_lmg_mag": ("aug_drum", f"{AUGOLF}/weapon_vm_sm_augolf_lmg_mag", EXTRACTED),
    "attachment_vm_muzzledefault01": ("aug_flash_hider", f"{MW_ATTACHMENTS}/attachment_vm_muzzledefault01",
                                      ATTACHMENTS_PACK),
    "attachment_vm_laser_mount01": ("aug_laser_mount", f"{MW_ATTACHMENTS}/attachment_vm_laser_mount01",
                                    ATTACHMENTS_PACK),
}

SHOT = "weapons/augolf/weap_augolf_fire_plr_01.wav"
SUPPRESSED = "weapons/augolf/weap_augolf_sup_fire_plr_01.ogg"
# Loudest 100 ms of each channel, against the M16A4's -7.5 / -7.5 dB (suppressed -14.8 / -14.9). The shot is stereo
# and louder on the left (-4.7 / -9.8), so it's levelled by the two channels' mean power (-6.5). The suppressed shot is
# mono, so both channels get all of it, and its peaks run 9 dB over full scale before the gain.
SHOT_GAIN_DB = -1
SUPPRESSED_GAIN_DB = -13

# The clips whose sound events are timed (kastov_weapons.AUG: the 5.56 magazine's reloads), by their name in the QC ->
# the name port_kastov.py exports them under.
RELOAD_CLIPS = {"reload_armag": "reload", "reload_empty_armag": "reload_empty",
                "reload_drummag": "reload_drummag", "reload_empty_drummag": "reload_empty_drummag"}
# Deploy and holster foley: the first sound of these clips.
ONE_SHOTS = {"raise": "draw", "drop": "holster"}


def preserve_clean_stock(material: Path) -> Path:
    """Keep the edited, unbranded production maps across material rebuilds."""
    if material.stem != "aug_stock_tactical":
        return material
    text = material.read_text()
    for channel in ("color", "normal"):
        clean = material.with_name(f"aug_stock_tactical_clean_{channel}.png")
        if not clean.exists():
            raise FileNotFoundError(f"Missing cleaned stock texture: {clean}")
        text = text.replace(f"aug_stock_tactical_{channel}.png", clean.name)
    material.write_text(text)
    return material


def build_material(name, base, out, pack):
    return preserve_clean_stock(build_source_material(name, base, out, pack))


def clip_events() -> dict[str, list[tuple[int, str]]]:
    """Each clip's (frame, alias) sound events from the viewmodel qc, the pack's own aliases only."""
    qc = QC.read_text(encoding="utf-8", errors="replace")
    events = {}
    for match in re.finditer(r'\$sequence "([^"]+)"(.*?)(?=\$sequence|\Z)', qc, re.DOTALL):
        events[match.group(1)] = [(int(frame), alias) for frame, alias in
                                  re.findall(r'event 5004 (\d+) "([^"]+)"', match.group(2))
                                  if alias.startswith("wfoly_plr_sm_augolf")]
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

    # Same curve as sounds/weapons/m4a1/m4_shot.sound. One recording only, so more pitch spread than the M16's.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "aug.fire.sound"
    # The rip's shot, voiced away from CoD's sound design (ported_shots.py).
    sound_event(fire, ported_shots.build("aug", out), pitch=ported_shots.event_pitch("aug"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the AUG's own suppressed shot.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    suppressed["Sounds"] = [asset_path(level_shot(out, SUPPRESSED, "aug_suppressed_shot", SUPPRESSED_GAIN_DB,
                                                  mono=True).with_suffix(".vsnd"))]
    fire_suppressed = out / "aug.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events, files = clip_events(), alias_files()
    sounds: dict[str, str] = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}

    def event_for(alias: str, name: str | None = None) -> str:
        [file] = files[alias]
        # wfoly_sm_augolf_reload_waffle_magout_01 -> reload_magout_01 ("waffle" is the 5.56 magazine's set).
        name = name or re.sub(r"^wfoly_sm_augolf_", "", Path(file).stem).replace("_waffle", "")
        if name not in sounds:
            wav = out / f"aug_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"aug.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        event_for(alias, name)
    reloads = {exported: timed(events[clip], event_for) for clip, exported in RELOAD_CLIPS.items()}
    # The suppressed shots, voiced like the open shot (suppressed_shots.py).
    suppressed_shots.voice("aug")
    # The foley, voiced away from CoD's sound design (ported_foley.py).
    ported_foley.voice("aug")
    return sounds, reloads


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials", pack))
                 for source, (name, base, pack) in MATERIALS.items()}
    manifest_path = DEST / "aug_assets.json"
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
