#!/usr/bin/env python3
"""Convert the Kastov 762's Source (MW base) materials into s&box complex.shader materials.

MW base texture packing:
  <name>_rgb  RGB albedo, A metal mask (also $blendtintbybasealpha's mask)
  <name>_n    RGB normal (DirectX, green down), A gloss
  <name>_e    R phong exponent, G albedo tint mask, A occlusion / rim mask

Written per material into Assets/Weapons/Kastov/materials: <name>_color/_normal/_rough/_metal/_ao.png and <name>.vmat.
The .vmat is named after the SMD material, which is what ModelDoc looks up ("<name>.vmat").

Needs SourceIO (for the VTF decoder) under TOOLS, and the extracted addon under ADDON.
Run: python Tools/kastov_materials.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "Assets" / "Weapons" / "Kastov" / "materials"
OUT_ASSET = "weapons/kastov/materials"
TOOLS = Path(r"D:\tmp\hc1-mw22-tools")
ADDON = TOOLS / "extracted" / "3803722029" / "materials"

sys.path.insert(0, str(TOOLS))
from SourceIO.library.utils.pylib.vtf import load_vtf_texture  # noqa: E402

sys.path.insert(0, str(PROJECT / "Tools" / "texture_markings"))
import markings  # noqa: E402

ATTACHMENT_MATERIALS = {
    **{name: f"mw4/ak47/sto/{name}" for name in
       ("ak47_s_ass", "ak47_s_h", "ak47_s_ha", "ak47_s_l", "ak47_s_no", "ak47_s_t")},
    **{name: f"mw4/ak47/psg/{name}" for name in ("ak47_p_a", "ak47_p_ass", "ak47_p_s")},
    **{name: f"mw4/ak47/mag/{name}" for name in ("47_apex_m_d", "ak47_m_e1", "ak47_m_e2")},
    **{name: f"mw4/ak47/bar/{name}" for name in ("ak47_b_s", "ak47_b_s_hg", "ak47_b_s_muz")},
    "ak47_rec_sto_ada": "mw4/ak47/ak47_rec_sto_ada",
}

MATERIALS = {
    **ATTACHMENT_MATERIALS,
    "76239": "mw4/ak47/mag/76239",
    "76239_dt": "mw4/ak47/mag/76239_dt",
    "ak47_m_d": "mw4/ak47/mag/ak47_m_d",
    "ak47_p_d": "mw4/ak47/psg/ak47_p_d",
    "ak47_rail": "mw4/ak47/ak47_rail",
    "ak47_rec_misc_1": "mw4/ak47/ak47_rec_misc_1",
    "wpn_rex_ar_akilo_bar_df_v0": "mw4/ak47/bar/wpn_rex_ar_akilo_bar_df_v0",
    "wpn_rex_ar_akilo_guard_df_v0": "mw4/ak47/bar/wpn_rex_ar_akilo_guard_df_v0",
    "wpn_rex_ar_akilo_muz_df_v0": "mw4/ak47/bar/wpn_rex_ar_akilo_muz_df_v0",
    "wpn_rex_ar_akilo_rec_01_v0": "mw4/ak47/wpn_rex_ar_akilo_rec_01_v0",
    "wpn_rex_ar_akilo_rec_02_v0": "mw4/ak47/wpn_rex_ar_akilo_rec_02_v0",
    "wpn_rex_ar_akilo_stock_df_v0": "mw4/ak47/sto/wpn_rex_ar_akilo_stock_df_v0",
}


def vmt_textures(vmt: Path) -> dict[str, str]:
    text = vmt.read_text(encoding="utf-8", errors="replace")
    result = {}
    for key in ("$basetexture", "$bumpmap", "$phongexponenttexture"):
        match = re.search('"' + re.escape(key) + r'"\s+"([^"]+)"', text, re.IGNORECASE)
        if match:
            result[key] = match.group(1).replace("\\", "/")
    return result


def load(texture: str) -> np.ndarray:
    pixels, width, height, _ = load_vtf_texture((ADDON / f"{texture}.vtf").read_bytes())
    return np.frombuffer(pixels, np.uint8).reshape(height, width, 4)


def save(array: np.ndarray, path: Path) -> None:
    mode = "L" if array.ndim == 2 else "RGB"
    Image.fromarray(np.ascontiguousarray(array), mode).save(path, optimize=True)


def convert(name: str, vmt_path: str) -> None:
    textures = vmt_textures(ADDON / f"{vmt_path}.vmt")
    rgb = load(textures["$basetexture"])
    normal = load(textures["$bumpmap"])
    extra = load(textures["$phongexponenttexture"]) if "$phongexponenttexture" in textures else None

    save(rgb[:, :, :3], OUT / f"{name}_color.png")
    save(rgb[:, :, 3], OUT / f"{name}_metal.png")
    flipped = normal[:, :, :3].copy()
    flipped[:, :, 1] = 255 - flipped[:, :, 1]
    save(flipped, OUT / f"{name}_normal.png")
    save(255 - normal[:, :, 3], OUT / f"{name}_rough.png")
    ao = f"{OUT_ASSET}/{name}_ao.png"
    if extra is not None:
        save(extra[:, :, 3], OUT / f"{name}_ao.png")
    else:
        ao = "materials/default/default_ao.tga"

    (OUT / f"{name}.vmat").write_text(
        '"Layer0"\n'
        "{\n"
        '    shader "shaders/complex.shader"\n'
        '    F_SPECULAR "1"\n'
        '    F_METALNESS_TEXTURE "1"\n'
        '    g_flRoughnessScaleFactor "1"\n'
        f'    TextureColor "{OUT_ASSET}/{name}_color.png"\n'
        f'    TextureNormal "{OUT_ASSET}/{name}_normal.png"\n'
        f'    TextureRoughness "{OUT_ASSET}/{name}_rough.png"\n'
        f'    TextureMetalness "{OUT_ASSET}/{name}_metal.png"\n'
        f'    TextureAmbientOcclusion "{ao}"\n'
        '    g_vColorTint "[1.0 1.0 1.0 1.0]"\n'
        '    g_flModelTintAmount "1.0"\n'
        "}\n", encoding="utf-8", newline="\n")
    # The rip's serials, stamps and logos come off again (Tools/texture_markings/specs).
    markings.after_rip(f"{OUT_ASSET}/{name}.vmat")
    print(f"{name}: {rgb.shape[1]}x{rgb.shape[0]}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, vmt_path in MATERIALS.items():
        convert(name, vmt_path)


if __name__ == "__main__":
    main()
