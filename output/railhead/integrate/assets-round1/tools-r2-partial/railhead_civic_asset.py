"""Pack the generated civic hall cutout and rebuild only Railhead's skyline."""
from pathlib import Path
import sys
from PIL import Image
import railhead_backdrop as B

root = Path(__file__).resolve().parent.parent
source = Image.open(sys.argv[1]).convert("RGBA")
# Texture dimensions are powers of two; the card preserves the source's 3:2 ratio.
source = source.resize((2048, 1024), Image.Resampling.LANCZOS)
folder = root / "Assets/materials/railhead"
source.save(folder / "civic_impostor.png")
mask = source.getchannel("A").point(lambda a: 255 if a >= 200 else 0)
Image.merge("RGB", (mask, mask, mask)).save(folder / "civic_impostor_alpha.png")
model = B.skyline()
count = B.K.write_model(root / "Assets/models/maps/railhead",
                       "models/maps/railhead", "railhead_skyline", model)
print(f"Skyline rebuilt: {count} triangles. Original minster retained in generator.")
