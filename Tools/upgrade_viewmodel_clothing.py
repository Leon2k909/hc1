"""Rebuild high-detail first-person fabric and glove atlases from existing UV maps.

Uses the original engine normal maps to retain seams/folds and adds restrained
material microstructure without altering UV islands or glove transparency.
"""
from pathlib import Path
import argparse
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "Assets/materials/operators/first_person"


def upgrade(name, normal_source, fabric=False):
    source = ASSETS / name
    image = Image.open(source)
    alpha = image.getchannel("A") if image.mode == "RGBA" else None
    rgb = image.convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS)
    # Restore existing high-frequency edges (stitched seams and cloth panels).
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.1, percent=80, threshold=3))
    if alpha is not None:
        # Never create new open holes or lose any original finger-opening opacity.
        rgb.putalpha(alpha.resize((2048, 2048), Image.Resampling.LANCZOS))
    rgb.save(source, optimize=True)

    # Work in tangent-normal vector space, not color space.
    old = np.array(Image.open(normal_source).convert("RGB").resize((2048, 2048), Image.Resampling.BICUBIC), dtype=np.float32)
    n = old / 127.5 - 1.0
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 0.0001)
    yy, xx = np.indices((2048, 2048), dtype=np.float32)
    # The weave stays smaller than cloth seams; worn leather has nonperiodic pores.
    if fabric:
        dx = 0.022 * np.sin(xx * 2.0 * np.pi / 6.0) + 0.010 * np.sin(yy * 2.0 * np.pi / 11.0)
        dy = 0.022 * np.sin(yy * 2.0 * np.pi / 6.0) + 0.010 * np.sin(xx * 2.0 * np.pi / 11.0)
    else:
        rng = np.random.default_rng(4127)
        pore = rng.normal(size=(2048, 2048)).astype(np.float32)
        # Fine leather pores, band-limited to avoid sparkling/aliasing.
        pore_img = Image.fromarray(np.clip(pore * 30 + 128, 0, 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(1.3))
        pore = (np.asarray(pore_img, dtype=np.float32) - 128) / 30
        gy, gx = np.gradient(pore)
        dx, dy = np.clip(gx * 0.23, -0.045, 0.045), np.clip(gy * 0.23, -0.045, 0.045)
    n[:, :, 0] += dx
    n[:, :, 1] += dy
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 0.0001)
    normal_name = "fp_army_shirt_normal.png" if fabric else "fp_fingerless_gloves_normal.png"
    target = ASSETS / normal_name
    Image.fromarray(np.clip((n + 1) * 127.5 + 0.5, 0, 255).astype(np.uint8), "RGB").save(target, optimize=True)
    print(f"{source}: {rgb.size}; {target}: 2048x2048")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--normals", required=True, type=Path, help="Engine-exported normal-map folder")
    args = p.parse_args()
    upgrade("fp_army_shirt_color.png", args.normals / "fp_shirt_source_normal.png", True)
    upgrade("fp_fingerless_gloves_albedo.png", args.normals / "fp_gloves_source_normal.png")
