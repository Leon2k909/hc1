"""Build the Kastov-74u materials and sounds from the MWII Kastovia Platform addon.

Source: Steam Workshop 3499492742, gmad-extracted to EXTRACTED. The model/animation side
of the port runs through the shared Kastov pipeline (Tools/port_kastov.py); this script only
produces the assets that pipeline references.

Materials: the addon ships MW PBR data packed for VertexLitGeneric:
  *_rgb  RGB = albedo, A = metal mask (drives $blendtintbybasealpha)
  *_n    RGB = normal (Source 1 / DirectX green), A = envmap mask
  *_e    R = phong exponent, G = metal mask again, A = gloss
so each material becomes color / normal (green flipped for Source 2) / roughness (1 - gloss)
/ metalness PNGs and a complex.shader vmat.

Sounds: .ogg files are converted to 44.1 kHz PCM wav with ffmpeg. Each shot variant is the
74u shot layer mixed with its mechanical layer. Reload foley reuses the Kastov (akilo) foley
from the same addon, because the 74u's own Lua points at MW2019 M4 foley that it doesn't ship.

Run: python Tools/ks74u_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent / "texture_markings"))
import markings  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "Assets"
DEST = ASSETS / "Weapons" / "Kastov74u"
TOOLS = Path(r"D:/tmp/hc1-mw22-tools")
EXTRACTED = TOOLS / "extracted" / "3499492742"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/)
MATERIALS = {
    "xmaterial_b1cc73363b399e9": ("ks74u_receiver", "zeron/weapons/kastov/xmaterial_b1cc73363b399e9"),
    "xmaterial_7915a70e03b314a": ("ks74u_rail", "zeron/weapons/kastov/xmaterial_7915a70e03b314a"),
    "xmaterial_176800459723c866": ("ks74u_barrel", "zeron/weapons/kastov/xmaterial_176800459723c866"),
    "xmaterial_2726a6746247c78c": ("ks74u_barrel_mounts", "zeron/weapons/kastov/xmaterial_2726a6746247c78c"),
    "xmaterial_1410fe4e45224d9": ("ks74u_muzzle", "zeron/weapons/kastov/xmaterial_1410fe4e45224d9"),
    "xmaterial_14e5cff401c75011": ("ks74u_mag", "zeron/weapons/kastov/xmaterial_14e5cff401c75011"),
    "xmaterial_73f6e083c54472b0": ("ks74u_rounds", "zeron/weapons/kastov/xmaterial_73f6e083c54472b0"),
    "xmaterial_1c0fbe815cee2ced": ("ks74u_stock", "zeron/weapons/vepr/xmaterial_1c0fbe815cee2ced"),
    "wpn_p04_ar_akilo_pstlgrip_v0": ("ks74u_pistolgrip", "pwci/mw/weapons/akilo103/wpn_p04_ar_akilo_pstlgrip_v0"),
    # The other stocks, pistol grips and magazines (kastov_weapons.KASTOV_74U.part_choices).
    "xmaterial_7fbb0a572b2df63": ("ks74u_stock_skeleton", "zeron/weapons/vepr/xmaterial_7fbb0a572b2df63"),
    "xmaterial_72129c296198ca6f": ("ks74u_stock_spetsnaz", "zeron/weapons/vepr/xmaterial_72129c296198ca6f"),
    "xmaterial_565b28beb19da10": ("ks74u_stock_wood", "zeron/weapons/vepr/xmaterial_565b28beb19da10"),
    "xmaterial_7c8b5a0f01933b53": ("ks74u_stock_tac", "zeron/weapons/vepr/xmaterial_7c8b5a0f01933b53"),
    "xmaterial_6c091df09c21d2a5": ("ks74u_stock_tac02", "zeron/weapons/vepr/xmaterial_6c091df09c21d2a5"),
    "xmaterial_7e736406c37951b4": ("ks74u_stock_wire", "zeron/weapons/vepr/xmaterial_7e736406c37951b4"),
    "xmaterial_7751c7fa2ecc7b00": ("ks74u_stock_broadside", "zeron/weapons/vepr/xmaterial_7751c7fa2ecc7b00"),
    "xmaterial_2a0266bcd0128fde": ("ks74u_stock_exo", "zeron/weapons/vepr/xmaterial_2a0266bcd0128fde"),
    "xmaterial_535b60d017059ff0": ("ks74u_stock_rpk", "zeron/weapons/vepr/xmaterial_535b60d017059ff0"),
    "xmaterial_7cdb053d4abc6fc7": ("ks74u_stock_rpk_heavy", "zeron/weapons/vepr/xmaterial_7cdb053d4abc6fc7"),
    "xmaterial_78c49d1377297bd1": ("ks74u_grip_tac", "zeron/weapons/vepr/xmaterial_78c49d1377297bd1"),
    "xmaterial_4bdf66a36afc9521": ("ks74u_grip_steady", "zeron/weapons/vepr/xmaterial_4bdf66a36afc9521"),
    "xmaterial_34f83c1410c9afaa": ("ks74u_grip_demo", "zeron/weapons/vepr/xmaterial_34f83c1410c9afaa"),
    "xmaterial_69c574f075d5df8e": ("ks74u_grip_shotgun", "zeron/weapons/vepr/xmaterial_69c574f075d5df8e"),
    "xmaterial_2c6a8fc7ddc7cb85": ("ks74u_grip_brace", "zeron/weapons/vepr/xmaterial_2c6a8fc7ddc7cb85"),
    "xmaterial_757096218252e0eb": ("ks74u_mag_20", "zeron/weapons/kastov/xmaterial_757096218252e0eb"),
    "xmaterial_7a331bfc0e9487f0": ("ks74u_mag_45", "zeron/weapons/kastov/xmaterial_7a331bfc0e9487f0"),
}

SHOTS = 8
FIRE_DIR = "zeron/ar_akilo105/fire"
FOLEY_DIR = "iw9/wpn/reloads/iw9_akilo"

# Friendly sound name -> source .ogg under sound/
FOLEY = {
    "reload.mvt": f"{FOLEY_DIR}/p04_ar_akilo_reload_mvt.ogg",
    "reload.maggrab": f"{FOLEY_DIR}/p04_ar_akilo_reload_maggrab.ogg",
    "reload.magout": f"{FOLEY_DIR}/p04_ar_akilo_reload_magout.ogg",
    "reload.magbump": f"{FOLEY_DIR}/p04_ar_akilo_reload_magbump.ogg",
    "reload.magclick": f"{FOLEY_DIR}/p04_ar_akilo_reload_magclick.ogg",
    "reload.mvt2": f"{FOLEY_DIR}/p04_ar_akilo_reload_mvt2.ogg",
    "reload.shoulder": f"{FOLEY_DIR}/p04_ar_akilo_reload_shoulder.ogg",
    "reload_empty.mvt": f"{FOLEY_DIR}/p04_ar_akilo_reload_empty_mvt.ogg",
    "reload_empty.charge": f"{FOLEY_DIR}/p04_ar_akilo_reload_empty_charge.ogg",
    "reload_empty.magout": f"{FOLEY_DIR}/p04_ar_akilo_reload_empty_magout.ogg",
    "reload_empty.magbump": f"{FOLEY_DIR}/p04_ar_akilo_reload_empty_magbump.ogg",
    "reload_empty.magin": f"{FOLEY_DIR}/p04_ar_akilo_reload_empty_magin.ogg",
    "reload_empty.mvt2": f"{FOLEY_DIR}/p04_ar_akilo_reload_empty_mvt2.ogg",
    "reload_empty.shoulder": f"{FOLEY_DIR}/p04_ar_akilo_reload_empty_shoulder.ogg",
    "raise": f"{FOLEY_DIR}/ar_akilo_raise_quick_grab.ogg",
    "raise_first.mvt": f"{FOLEY_DIR}/p04_ar_akilo_raise_first_mvt.ogg",
    "raise_first.charge": f"{FOLEY_DIR}/p04_ar_akilo_raise_first_charge.ogg",
    "raise_first.end": "zeron/ar_akilo105/reloads/p04_ar_akilo74_first_raise_end_01.ogg",
    "drop": f"{FOLEY_DIR}/p04_ar_akilo_drop_quick.ogg",
    "selector.on": "zeron/ar_akilo105/reloads/ar_akilo_selectsemi_on_click.ogg",
    "selector.off": "zeron/ar_akilo105/reloads/ar_akilo_selectsemi_off.ogg",
    "inspect.over": f"{FOLEY_DIR}/p04_ar_akilo_inspect_over.ogg",
    "inspect.mvt": f"{FOLEY_DIR}/p04_ar_akilo_inspect_mvt.ogg",
    "inspect.magout": f"{FOLEY_DIR}/p04_ar_akilo_inspect_magout.ogg",
    "inspect.magin": f"{FOLEY_DIR}/p04_ar_akilo_inspect_magin.ogg",
    "inspect.charge": f"{FOLEY_DIR}/p04_ar_akilo_inspect_charge.ogg",
    "inspect.shoulder": f"{FOLEY_DIR}/p04_ar_akilo_inspect_shoulder.ogg",
}

# Seconds into the 74u's reload clips (played at 1x), from its bone motion:
# tactical - mag leaves ~0.73s, swap ~1.0s, seats ~1.37s, hand back on the guard ~2.05s;
# empty    - charging handle locked back ~0.3s, mag out ~1.15s, new mag seats ~1.95s,
#            bolt released ~2.05s, hands back ~2.25s.
RELOAD_SOUNDS = {
    0.0: "reload.mvt", 0.3: "reload.maggrab", 0.7: "reload.magout", 1.13: "reload.magbump",
    1.35: "reload.magclick", 1.76: "reload.mvt2", 2.02: "reload.shoulder",
}
EMPTY_RELOAD_SOUNDS = {
    0.0: "reload_empty.mvt", 0.28: "reload_empty.charge", 1.12: "reload_empty.magout",
    1.82: "reload_empty.magbump", 1.95: "reload_empty.magin", 2.18: "reload_empty.shoulder",
}


def asset_path(path: Path) -> str:
    return path.relative_to(ASSETS).as_posix().lower()


def load_vtf(base: str, extracted: Path = EXTRACTED) -> np.ndarray:
    sys.path.insert(0, str(TOOLS))
    from SourceIO.library.utils.pylib.vtf import load_vtf_texture

    source = extracted / "materials" / f"{base}.vtf"
    pixels, width, height, floating = load_vtf_texture(source.read_bytes())
    if floating:
        raise RuntimeError(f"Unexpected HDR texture: {source}")
    return np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 4)


def build_material(name: str, base: str, out: Path = DEST / "materials", extracted: Path = EXTRACTED,
                   translucent: bool = False) -> Path:
    """A complex.shader material from a pack's _rgb/_n/_e textures (extracted: the gmad-extracted pack; another pack
    that packs its textures the same way, like the M16's). A translucent material ($translucent in its vmt, like a
    see-through magazine's strip) has opacity in the _rgb alpha instead of the metal mask."""
    out.mkdir(parents=True, exist_ok=True)
    rgb = load_vtf(base + "_rgb", extracted)
    normal = load_vtf(base + "_n", extracted)
    exponent = load_vtf(base + "_e", extracted)

    Image.fromarray(rgb[:, :, :3].copy()).save(out / f"{name}_color.png")
    flipped = normal[:, :, :3].copy()
    flipped[:, :, 1] = 255 - flipped[:, :, 1]
    Image.fromarray(flipped).save(out / f"{name}_normal.png")
    Image.fromarray(255 - exponent[:, :, 3]).save(out / f"{name}_roughness.png")
    Image.fromarray(rgb[:, :, 3].copy()).save(out / f"{name}_{'opacity' if translucent else 'metalness'}.png")

    vmat = out / f"{name}.vmat"
    rel = lambda suffix: asset_path(out / f"{name}_{suffix}.png")
    if translucent:
        alpha = ['\tF_TRANSLUCENT "1"', '\tg_flMetalness "0"', f'\tTextureTranslucency "{rel("opacity")}"']
    else:
        alpha = ['\tF_METALNESS_TEXTURE "1"', f'\tTextureMetalness "{rel("metalness")}"']
    vmat.write_text("\n".join([
        '"Layer0"', "{",
        '\tshader "shaders/complex.shader"',
        '\tF_SPECULAR "1"',
        alpha[0],
        '\tg_flRoughnessScaleFactor "1"',
        '\tg_vColorTint "[1 1 1 1]"',
        f'\tTextureColor "{rel("color")}"',
        f'\tTextureNormal "{rel("normal")}"',
        f'\tTextureRoughness "{rel("roughness")}"',
        *alpha[1:],
        '\tTextureAmbientOcclusion "materials/default/default_ao.tga"',
        "}",
    ]) + "\n", encoding="utf-8", newline="\n")
    # The rip's serials, stamps and logos come off again (Tools/texture_markings/specs).
    markings.after_rip(asset_path(vmat))
    return vmat


def ffmpeg(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def sound_event(path: Path, sounds: list[Path], *, pitch: str, decibels: int, distance: int,
                falloff: list[dict]) -> None:
    path.write_text(json.dumps({
        "UI": False,
        "Volume": "1",
        "Pitch": pitch,
        "Decibels": decibels,
        "SelectionMode": "Random",
        "Sounds": [asset_path(s.with_suffix(".vsnd")) for s in sounds],
        "Occlusion": False,
        "AirAbsorption": True,
        "Transmission": True,
        "OcclusionRadius": 64,
        "DistanceAttenuation": True,
        "Distance": distance,
        "Falloff": falloff,
        "__references": [],
        "__version": 1,
    }, indent=2) + "\n", encoding="utf-8", newline="\n")


def build_sounds() -> dict[str, str]:
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)
    src = EXTRACTED / "sound"

    shots = []
    for index in range(1, SHOTS + 1):
        wav = out / f"ks74u_shot_{index:02d}.wav"
        ffmpeg(["-i", str(src / FIRE_DIR / f"weap_akilo74_fire_plr_shot_{index:02d}.ogg"),
                "-i", str(src / FIRE_DIR / f"weap_akilo74_fire_plr_mech_{index:02d}.ogg"),
                "-filter_complex", "amix=inputs=2:duration=longest:normalize=0",
                "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
        shots.append(wav)
    # Same curve as sounds/weapons/m4a1/m4_shot.sound.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "ks74u.fire.sound"
    sound_event(fire, shots, pitch="0.98 1.02", decibels=m4["Decibels"], distance=m4["Distance"],
                falloff=m4["Falloff"])

    events = {"fire": asset_path(fire)}
    for name, relative in FOLEY.items():
        wav = out / f"ks74u_{name.replace('.', '_')}.wav"
        ffmpeg(["-i", str(src / relative), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
        event = out / f"ks74u.{name}.sound"
        sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
        events[name] = asset_path(event)
    return events


def main() -> None:
    materials = {source: asset_path(build_material(name, base)) for source, (name, base) in MATERIALS.items()}
    manifest_path = DEST / "ks74u_assets.json"
    if "--materials-only" in sys.argv[1:]:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["materials"] = materials
        sounds = manifest["sounds"]
    else:
        sounds = build_sounds()
        manifest = {
            "materials": materials,
            "sounds": sounds,
            "reload_sounds": {str(t): sounds[n] for t, n in RELOAD_SOUNDS.items()},
            "empty_reload_sounds": {str(t): sounds[n] for t, n in EMPTY_RELOAD_SOUNDS.items()},
        }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(materials)} materials, {len(sounds)} sound events -> {DEST}")


if __name__ == "__main__":
    main()
