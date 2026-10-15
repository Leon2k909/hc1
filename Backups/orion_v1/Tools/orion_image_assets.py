"""Encode the selected image-generated sky for s&box's linear-light sky compiler.

This preserves the PNG source; it only converts the color encoding and file
format. Run before the native import. Prompts are in Sources/Orion/.
"""
from pathlib import Path
import numpy as np
from PIL import Image
from orion_reflections import write_exr, decode_aces

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/"output/orion/stage/materials/orion"

def main():
    source=STAGE/"sky/orion_sky_v2.png"
    if not source.exists():
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_bytes((ROOT/"Assets/materials/orion/sky/orion_sky_v2.png").read_bytes())
    # Use the existing sky pipeline's inverse display transform so that the
    # engine's ACES output reproduces the source at the authored exposure.
    rgb=np.asarray(Image.open(source).convert("RGB"),np.float32)
    if rgb.shape[1]!=2*rgb.shape[0]:
        raise ValueError("The sky source must use a 2:1 equirectangular projection")
    linear=decode_aces(rgb,exposure=1.2)
    write_exr(source.with_suffix(".exr"),linear)
    source.with_suffix(".vmat").write_text('"Layer0"\n{\n    shader "shaders/sky.shader"\n    F_TEXTURE_FORMAT2 "6"\n    g_flBrightnessExposureBias "0"\n    g_flRenderOnlyExposureBias "0"\n    SkyTexture "materials/orion/sky/orion_sky_v2.exr"\n}\n')
    concrete=STAGE/"or_concrete.vmat"
    concrete.write_text(concrete.read_text().replace("or_concrete_color.jpg","or_concrete_color_v2.png"))
    print(f"Staged {rgb.shape[1]}x{rgb.shape[0]} sky EXR and concrete v2 material reference")

if __name__=="__main__":main()
