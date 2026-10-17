"""Make a stable opaque steel-on-dark grating from Riverdale's existing textures.

The grating has a dark steel tray under it on the main hall floor; alpha-tested bars
at 1.2 in pitch shimmer badly on camera motion. Mipmap-filtering an opaque composite
keeps the industrial pattern while eliminating stochastic alpha coverage changes.

    python Tools/riverdale_grating_stable.py --out output/riverdale/aaa/grating-stage
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "Assets/materials/riverdale"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve() / "materials/riverdale"
    out.mkdir(parents=True, exist_ok=True)
    colour = np.asarray(Image.open(SOURCE / "rv_grating_color.jpg").convert("RGB"), dtype=np.float32)
    coverage = np.asarray(Image.open(SOURCE / "rv_grating_trans.png").convert("L"), dtype=np.float32) / 255.0
    # Raised bars stay metallic; holes resolve to a dark, rough drainage tray.
    # Opaque coverage enables ordinary mip filters for stable minification.
    dark = np.array([20, 23, 25], dtype=np.float32)
    # No binary cutout: distant bars average smoothly and won't shimmer.
    result = colour * coverage[..., None] + dark * (1 - coverage[..., None])
    Image.fromarray(np.uint8(np.clip(np.rint(result), 0, 255)), "RGB").save(out / "rv_grating_stable_color.png", optimize=True)
    source_vmat = (SOURCE / "rv_grating.vmat").read_text(encoding="utf-8")
    text = source_vmat.replace('    F_ALPHA_TEST "1"\n', '')
    text = text.replace('    TextureTranslucency "materials/riverdale/rv_grating_trans.png"\n', '')
    text = text.replace('    g_flAlphaTestReference "0.150"\n', '')
    text = text.replace('    g_flAntiAliasedEdgeStrength "1"\n', '')
    text = text.replace('rv_grating_color.jpg', 'rv_grating_stable_color.png')
    (out / "rv_grating_stable.vmat").write_text(text, encoding="utf-8")
    print("staged an opaque, mip-filtered grating material")


if __name__ == "__main__":
    main()
