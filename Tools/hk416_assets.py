"""Build the HK416 A5's materials and sounds from Ha2ard's RoN HK416 A5 pack (Workshop 3385630838, mg_ron_hk416).

The pack is Ready or Not's HK416 A5 (the 11-inch carbine with HK's tan M-LOK handguard) on the MW base, with Escape
from Tarkov's magazines and stocks as attachments. The model and animation side runs through the shared Kastov pipeline
(Tools/port_kastov.py --weapon hk416).

Materials:
- RoN's own (the receiver with every gun part, and the steel magazine with its rounds) pack the MW way, like
  ks74u_assets.py's, but their _rgb alpha covers nearly the whole sheet and only darkens it to $color2 .35 in the vmt
  ($blendtintbybasealpha). build_material's metalness_scale takes that as 0.65 metal, which leaves Source's diffuse.
- The polymer HK PM Gen2 magazine, the E1 and Slim Line stocks and the M-LOK rail sections are Tarkov's sheets in the
  same _rgb/_n/_e packing. They're polymer (the rail sections aluminium, but their mask is empty), so no metal.
- Magpul's PMAGs are Source-style: a _diff colour map, a _nrm normal map and an _exp phong exponent map (build_eft).
  The 30-round window's glass is a colour map with opacity in its alpha, and the vmt's $translucent "0" is wrong: the
  real window is see-through.
- The laser mount is MW's (attachment_vm_laser_mount03), as the pack ships it.

Sounds: Tarkov's two close HK416 shots and its suppressed shot, levelled to the MCX's (the same round from a barrel of
about the same length). Reload foley plays where the clips' own sound events put them: the viewmodel QC's event 5004
frames (30 fps), resolved to files through the pack's alias list (mw_sounds_hk416.lua): the MCX's MW2019 moves and the
pack's own magazine and charging handle sounds. The MW base's generic Viewmodel.Small/Medium rattles and magazine drop
are left out.

Run: python Tools/hk416_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import ported_foley
import ported_shots
import suppressed_shots
from ks74u_assets import ASSETS, TOOLS, asset_path, build_material, ffmpeg, load_vtf, markings, sound_event

EXTRACTED = TOOLS / "extracted" / "3385630838"
DEST = ASSETS / "Weapons" / "HK416"
QC = TOOLS / "decompiled" / "hk416" / "v_ron_hk416" / "v_ron_hk416.qc"
ALIASES_LUA = EXTRACTED / "lua" / "weapons" / "mg_base" / "modules" / "sounds" / "mw_sounds_hk416.lua"
RON = "ha2ard/ron_hk416"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/, metalness_scale)
MATERIALS = {
    # The upper and lower receivers, the barrel and flash hider, the iron sights, the bolt and charging handle, and the
    # stock. Main_2 is the same sheet, named apart so the pack's camos can take the handguard, grip and stock.
    "RON_HK416_Main": ("hk416_receiver", f"{RON}/RON_HK416_Main", 0.65),
    "RON_HK416_Main_2": ("hk416_receiver", f"{RON}/RON_HK416_Main", 0.65),
    # The steel 30-round magazine and the rounds (the loose round's and every magazine's).
    "RON_HK416_Mag": ("hk416_mag", f"{RON}/RON_HK416_Mag", 0.65),
    "mag_stanag_hk_gen_2_pm_556x45_30_LOD0": ("hk416_polymer_mag",
                                              f"{RON}/yukiz_eft/mag_stanag_hk_gen_2_pm_556x45_30_LOD0", 0.0),
    "stock_ar15_hk_e1_LOD0": ("hk416_e1_stock", f"{RON}/hk_stocks_eft/e1/stock_ar15_hk_e1_LOD0", 0.0),
    "stock_ar15_hk_slim_line_LOD0": ("hk416_slim_line_stock",
                                     f"{RON}/hk_stocks_eft/silm_line/stock_ar15_hk_slim_line_LOD0", 0.0),
    "mount_m_lok_magpul_picatinny_rail_sections_LOD0": ("hk416_mlok_rail", f"{RON}/mlok_rail/eft_magpul_mlok_rail",
                                                        0.0),
    "laser_mount03": ("hk416_laser_mount", f"{RON}/attachment_vm_laser_mount03", 1.0),
}
# Source-style sheets: Source material -> (friendly name, _diff, _nrm (None: flat), _exp, translucent)
PMAG = f"{RON}/yukiz_eft/mag_stanag_magpul_pmag_gen_m3"
EFT_MATERIALS = {
    "mag_stanag_magpul_pmag_gen_m3_556x45_20_LOD0_blk": ("hk416_pmag20", f"{PMAG}_556x45_20_diff",
                                                         f"{PMAG}_556x45_20_nrm", f"{PMAG}_556x45_20_exp", False),
    "mag_stanag_magpul_pmag_gen_m3_window_556x45_30_LOD0_blk": (
        "hk416_pmag30", f"{PMAG}_window_556x45_30_blk_diff", f"{PMAG}_window_556x45_30_nrm",
        f"{PMAG}_window_556x45_30_exp", False),
    "mag_stanag_magpul_pmag_gen_m3_window_556x45_30_LOD0_glass": (
        "hk416_pmag30_window", f"{RON}/yukiz_eft/ak104smart_glass_col", None, f"{RON}/yukiz_eft/ak104smart_glass_spc",
        True),
    "mag_stanag_magpul_pmag_gen_m3_556x45_40_LOD0_blk": ("hk416_pmag40", f"{PMAG}_556x45_40_blk_diff",
                                                         f"{PMAG}_556x45_40_nrm", f"{PMAG}_556x45_40_exp", False),
}

# Tarkov's two close shots and its suppressed shot, each with its own gain. Loudest 100 ms (K-weighted, both channels):
# fire -2.3 dB, fire_2 -5.3 and the suppressed shot -5.6. Levelled, the open shots sit about where the MCX's do
# (-6.5: the same M855 from an 11-inch barrel against its 11.5), and the suppressed one where its were before voicing;
# suppressed_shots.py sets that 10 dB under the voiced open shot.
SHOTS = [("hk416_sound/eft_hk416_fire.wav", -4), ("hk416_sound/eft_hk416_fire_2.wav", -1)]
SUPPRESSED = ("hk416_sound/eft_hk416_fire_sil.wav", -9)

# The clips whose sound events are timed, by their name in the QC -> the name port_kastov.py exports them under. The
# 20-round PMAG reloads with the smag clips and the 40-round one with the xmag clips, as the pack's magazines do.
RELOAD_CLIPS = {"reload": "reload", "reload_empty": "reload_empty", "reload_smag": "reload_smag",
                "reload_empty_smag": "reload_empty_smag", "reload_xmag": "reload_xmag",
                "reload_empty_xmag": "reload_empty_xmag"}
# Deploy and holster foley: the first sound of these clips.
ONE_SHOTS = {"raise": "draw", "drop": "holster"}
# The pack's own aliases: the MCX's foley (wfoly_plr_ar_mcharlie_*) and its HK416 sounds (416_*).
OWN_ALIASES = ("wfoly_plr_ar_mcharlie", "416_")


def clip_events() -> dict[str, list[tuple[int, str]]]:
    """Each clip's (frame, alias) sound events from the viewmodel qc, the pack's own aliases only, in frame order."""
    qc = QC.read_text(encoding="utf-8", errors="replace")
    events = {}
    for match in re.finditer(r'\$sequence "([^"]+)"(.*?)(?=\$sequence|\Z)', qc, re.DOTALL):
        events[match.group(1)] = sorted((int(frame), alias) for frame, alias in
                                        re.findall(r'event 5004 (\d+) "([^"]+)"', match.group(2))
                                        if alias.startswith(OWN_ALIASES))
    return events


def alias_files() -> dict[str, list[str]]:
    """Sound alias -> its files under sound/, without Source's ^ prefix (as mcx_assets reads its pack's)."""
    lua = ALIASES_LUA.read_text(encoding="utf-8", errors="replace")
    files = {}
    for block in re.findall(r"sound\.Add\(\s*\{(.*?)\}\s*\)", lua, re.DOTALL):
        name = re.search(r'name\s*=\s*"([^"]+)"', block)
        sounds = re.search(r'sound\s*=\s*(\{[^}]*\}|"[^"]+")', block)
        if name and sounds:
            files[name.group(1)] = [file.lstrip("^") for file in re.findall(r'"([^"]+)"', sounds.group(1))]
    return files


def level_shot(out: Path, source: str, name: str, gain_db: int) -> Path:
    """A shot recording, turned up or down gain_db and limited like the Bizon's."""
    wav = out / f"{name}.wav"
    ffmpeg(["-i", str(EXTRACTED / "sound" / source),
            "-af", f"volume={gain_db}dB,alimiter=limit=0.891:attack=1:release=50:level=false",
            "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
    return wav


def level_shots(out: Path, name: str) -> list[Path]:
    """The open shots, each at its own gain: <name>_01.wav, _02."""
    return [level_shot(out, source, f"{name}_{index:02d}", gain) for index, (source, gain) in enumerate(SHOTS, 1)]


def roughness_from_exponent(exponent: np.ndarray) -> np.ndarray:
    """A phong exponent map's red channel (Source's 1..150 over 0..255) as GGX roughness: alpha = sqrt(2 / (n + 2))
    (Walter et al.'s Blinn-Phong match), and roughness = sqrt(alpha)."""
    n = 1 + 149 * exponent.astype(np.float32) / 255
    return np.round(255 * np.sqrt(np.sqrt(2 / (n + 2)))).astype(np.uint8)


def build_eft(name: str, diff: str, nrm: str | None, exp: str, translucent: bool, out: Path) -> Path:
    """A complex.shader material from a Source-style _diff / _nrm / _exp set: no metal, roughness from the exponent.
    A translucent one has opacity in the colour map's alpha and no normal map."""
    out.mkdir(parents=True, exist_ok=True)
    colour = load_vtf(diff, EXTRACTED)
    exponent = load_vtf(exp, EXTRACTED)
    rel = lambda suffix: asset_path(out / f"{name}_{suffix}.png")
    Image.fromarray(colour[:, :, :3].copy()).save(out / f"{name}_color.png")
    Image.fromarray(roughness_from_exponent(exponent[:, :, 0])).save(out / f"{name}_roughness.png")
    lines = ['"Layer0"', "{", '\tshader "shaders/complex.shader"', '\tF_SPECULAR "1"']
    if translucent:
        Image.fromarray(colour[:, :, 3].copy()).save(out / f"{name}_opacity.png")
        lines += ['\tF_TRANSLUCENT "1"']
    lines += ['\tg_flMetalness "0"', '\tg_flRoughnessScaleFactor "1"', '\tg_vColorTint "[1 1 1 1]"',
              f'\tTextureColor "{rel("color")}"']
    if nrm is None:
        lines += ['\tTextureNormal "materials/default/default_normal.tga"']
    else:
        flipped = load_vtf(nrm, EXTRACTED)[:, :, :3].copy()
        flipped[:, :, 1] = 255 - flipped[:, :, 1]
        Image.fromarray(flipped).save(out / f"{name}_normal.png")
        lines += [f'\tTextureNormal "{rel("normal")}"']
    lines += [f'\tTextureRoughness "{rel("roughness")}"']
    if translucent:
        lines += [f'\tTextureTranslucency "{rel("opacity")}"']
    lines += ['\tTextureAmbientOcclusion "materials/default/default_ao.tga"', "}"]
    vmat = out / f"{name}.vmat"
    vmat.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    markings.after_rip(asset_path(vmat))
    return vmat


def build_materials() -> dict[str, str]:
    """Source material -> vmat path. Main and Main_2 share one material, built once."""
    out = DEST / "materials"
    built: dict[str, str] = {}
    materials = {}
    for source, (name, base, metalness) in MATERIALS.items():
        if name not in built:
            built[name] = asset_path(build_material(name, base, out, EXTRACTED, metalness_scale=metalness))
        materials[source] = built[name]
    for source, (name, diff, nrm, exp, translucent) in EFT_MATERIALS.items():
        materials[source] = asset_path(build_eft(name, diff, nrm, exp, translucent, out))
    return materials


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

    # Same curve as sounds/weapons/m4a1/m4_shot.sound.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "hk416.fire.sound"
    # The rip's shots, voiced towards what a shooter hears outdoors (ported_shots.py).
    sound_event(fire, ported_shots.build("hk416", out), pitch=ported_shots.event_pitch("hk416"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the HK416's own suppressed shot.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    source, gain = SUPPRESSED
    suppressed["Sounds"] = [asset_path(level_shot(out, source, "hk416_suppressed_shot_01", gain).with_suffix(".vsnd"))]
    fire_suppressed = out / "hk416.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events, files = clip_events(), alias_files()
    sounds: dict[str, str] = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}

    def event_for(alias: str, name: str | None = None) -> str:
        [file] = files[alias]
        # hk416_sound/mcharlie/wfoly_ar_mcharlie_reload_rotate.ogg -> reload_rotate; hk416_sound/416_magout.wav ->
        # magout; hk416_sound/kg_1_1.ogg -> kg_1_1
        name = name or re.sub(r"^(wfoly_ar_mcharlie_|416_)", "", Path(file).stem.lower())
        if name not in sounds:
            wav = out / f"hk416_{name}.wav"
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
            event = out / f"hk416.{name}.sound"
            sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
            sounds[name] = asset_path(event)
        return sounds[name]

    for name, clip in ONE_SHOTS.items():
        frame, alias = events[clip][0]
        event_for(alias, name)
    reloads = {exported: timed(events[clip], event_for) for clip, exported in RELOAD_CLIPS.items()}
    # The suppressed shot, voiced like the open shots (suppressed_shots.py).
    suppressed_shots.voice("hk416")
    # The foley, voiced away from the games' sound design (ported_foley.py).
    ported_foley.voice("hk416")
    return sounds, reloads


def main() -> None:
    materials = build_materials()
    manifest_path = DEST / "hk416_assets.json"
    if "--materials-only" in sys.argv[1:]:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["materials"] = materials
    else:
        sounds, reloads = build_sounds()
        manifest = {"materials": materials, "sounds": sounds, "reloads": reloads}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(set(materials.values()))} materials, {len(manifest['sounds'])} sound events -> {DEST}")


if __name__ == "__main__":
    main()
