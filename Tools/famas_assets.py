"""Convert the existing Workshop 2528829149 FAMAS source for the development build.

These are MW2019 port assets, not original art or release-cleared assets. See famas.md.
Run after decompiling v_falpha and its factory barrel/magazine with Crowbar.
"""
from pathlib import Path
import json
import re
import shutil

from ks74u_assets import ASSETS, TOOLS, asset_path, build_material, ffmpeg, sound_event

EXTRACTED = TOOLS / "extracted/2528829149"
BASE_PACK = TOOLS / "extracted/2459720887"
DEST = ASSETS / "Weapons/FAMAS"
SOURCE = TOOLS / "decompiled/falpha/v_falpha/v_falpha.qc"
MATERIALS = {f"weapon_vm_ar_falpha_{suffix}": (f"famas_{suffix}",
             f"viper/mw/weapons/falpha/weapon_vm_ar_falpha_{suffix}", EXTRACTED)
             for suffix in ("body", "mag", "grip", "upper", "sights", "barrel", "barlong", "barlong_alt",
                            "v1_stock_light", "v1_stock_stable", "v1_stock_tactical", "xmag2", "handlecust")}
MATERIALS["weapon_vm_ar_mike4_magext"] = ("famas_xmag", "viper/mw/weapons/falpha/weapon_vm_ar_mike4_magext", EXTRACTED)
MATERIALS["attachment_vm_barrel03"] = ("famas_barrel_sleeve", "viper/mw/attachments/attachment_vm_barrel03", BASE_PACK)
MATERIALS["attachment_vm_laser_mount01"] = ("famas_laser_mount",
    "viper/mw/attachments/attachment_vm_laser_mount01", BASE_PACK)


def sounds():
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)
    lua = (EXTRACTED / "lua/weapons/mg_base/modules/sounds/mw_sounds_ar_falpha.lua").read_text()
    aliases = {}
    for block in re.findall(r"sound\.Add\(\s*\{(.*?)\}\s*\)", lua, re.S):
        name = re.search(r'name\s*=\s*"([^"]+)"', block)
        files = re.search(r'sound\s*=\s*(\{[^}]*\}|"[^"]+")', block)
        if name and files:
            aliases[name[1]] = [f.lstrip("^") for f in re.findall(r'"([^"]+)"', files[1])]
    events = {}
    for match in re.finditer(r'\$sequence "([^"]+)"(.*?)(?=\$sequence|\Z)', SOURCE.read_text(), re.S):
        events[match[1]] = [(int(frame), alias) for frame, alias in re.findall(r'event 5004 (\d+) "([^"]+)"', match[2])
                            if alias.startswith("wfoly_plr_ar_falpha")]
    result = {}

    def convert(name, files, shot=False, suppressed=False):
        if name in result:
            return result[name]
        wavs = []
        for index, file in enumerate(files, 1):
            wav = out / f"famas_{name}_{index:02d}.wav"
            # Match the existing rifles' dry-shot level; avoid stacking the pack's separate trigger/reverb layers.
            filters = ["-af", f"volume={-12 if suppressed else 0}dB,alimiter=limit=0.891:attack=1:release=50:level=false"] if shot else []
            ffmpeg(["-i", str(EXTRACTED / "sound" / file), *filters, "-ar", "44100", "-ac", "2" if shot else "1", "-c:a", "pcm_s16le", str(wav)])
            wavs.append(wav)
        event = out / f"famas.{name}.sound"
        if shot:
            template = ASSETS / ("sounds/swb/attachments/silencer/swb_rifle.silenced.fire.sound" if suppressed else "sounds/weapons/m4a1/m4_shot.sound")
            settings = json.loads(template.read_text())
            sound_event(event, wavs, pitch="0.97 1.03", decibels=settings["Decibels"],
                        distance=settings["Distance"], falloff=settings["Falloff"])
        else:
            sound_event(event, wavs, pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
        result[name] = asset_path(event)
        return result[name]

    convert("fire", aliases["mw19.falpha.fire"], shot=True)
    convert("fire_suppressed", aliases["mw19.falpha.fire.s"], shot=True, suppressed=True)
    for clip, name in (("draw", "raise"), ("holster", "drop")):
        convert(name, aliases[events[clip][0][1]])
    reloads = {}
    for clip in ("reload", "reload_empty", "reload_xmag", "reload_empty_xmag", "reload_xmag2", "reload_empty_xmag2"):
        timed = {}
        source_clip = "reload" if clip in ("reload_xmag", "reload_xmag2") else clip
        for frame, alias in events[source_clip]:
            name = alias.removeprefix("wfoly_plr_ar_falpha_")
            timed[f"{frame / 30:.3f}"] = convert(name, aliases[alias])
        reloads[clip] = timed
    return result, reloads


def main():
    # This sleeve shares the factory barrel's colour map but has its own normal/exponent maps.
    sleeve = TOOLS / "decompiled/falpha/material_import"
    folder = sleeve / "materials/viper/mw/attachments"
    folder.mkdir(parents=True, exist_ok=True)
    for suffix in ("rgb", "n", "e"):
        source = (EXTRACTED / "materials/viper/mw/weapons/falpha/weapon_vm_ar_falpha_barrel_rgb.vtf" if suffix == "rgb"
                  else BASE_PACK / f"materials/viper/mw/attachments/attachment_vm_barrel03_{suffix}.vtf")
        shutil.copyfile(source, folder / f"attachment_vm_barrel03_{suffix}.vtf")
    MATERIALS["attachment_vm_barrel03"] = ("famas_barrel_sleeve", "viper/mw/attachments/attachment_vm_barrel03", sleeve)
    materials = {source: asset_path(build_material(name, base, DEST / "materials", pack))
                 for source, (name, base, pack) in MATERIALS.items()}
    # Keep the locally removed fictional-brand stamp removed when regenerating this port.
    # Only the 48x36 logo patch was taken from each imagegen edit; the remaining UV atlas is unchanged.
    for texture in ("color", "normal"):
        cleaned = Path(__file__).resolve().parent.parent / f"Sources/FAMAS/branding/famas_upper_{texture}.png"
        shutil.copyfile(cleaned, DEST / f"materials/famas_upper_{texture}.png")
    audio, reloads = sounds()
    (DEST / "famas_assets.json").write_text(json.dumps({"materials": materials, "sounds": audio, "reloads": reloads}, indent=2) + "\n")
    print(f"FAMAS: {len(materials)} materials, {len(audio)} sound events")


if __name__ == "__main__":
    main()
