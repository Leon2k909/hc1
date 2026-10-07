"""Give the rotunda cutout a transparent texture border to prevent mip wrapping.

Run once after an unpadded bake. The bake script applies the same padding itself.
"""
from pathlib import Path
from PIL import Image

folder = Path(__file__).resolve().parent.parent / "Assets/materials/railhead"
source = Image.open(folder / "rotunda_impostor.png").convert("RGBA")
alpha = source.getchannel("A")
if not alpha.crop((0, 0, 2048, 32)).getbbox() and not alpha.crop((0, 992, 2048, 1024)).getbbox():
    print("Already padded; no change.")
    raise SystemExit(0)
picture = Image.new("RGBA", (2048, 1024))
picture.paste(source.resize((1920, 960), Image.Resampling.LANCZOS), (64, 32))
picture.save(folder / "rotunda_impostor.png")
mask = picture.getchannel("A").point(lambda a: 255 if a >= 204 else 0)
mask.save(folder / "rotunda_impostor_alpha.png")
assert not mask.crop((0, 0, 2048, 16)).getbbox()
assert not mask.crop((0, 1008, 2048, 1024)).getbbox()
print("Transparent borders verified; cutout packed with 64 x 32 pixel padding.")
