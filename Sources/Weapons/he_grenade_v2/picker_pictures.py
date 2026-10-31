# Shrink the "picture" renders into the skin picker's images: python picker_pictures.py <render dir> <project root>
import os
import sys

from PIL import Image

render, root = sys.argv[1], sys.argv[2]
out = os.path.join(root, "Assets", "ui", "weapons", "grenades")
for variant, name in (("before", "skin_he_standard.png"), ("after", "skin_he_k31.png")):
    im = Image.open(os.path.join(render, f"picture-{variant}.png")).convert("RGBA")
    im.resize((256, 256), Image.LANCZOS).save(os.path.join(out, name), compress_level=9)
    print(name, im.size, "alpha corner", im.getpixel((0, 0))[3], "alpha centre", im.getpixel((im.width // 2, im.height // 2))[3])
