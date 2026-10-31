# Turn the old flashbang's compiled maps back into plain maps Blender can use, only to render the "before".
# s&box packs them: hemi-octahedral normal in RG with roughness in B, metalness in the colour map's alpha.
#   python old_maps.py <work dir>
import os
import sys

import numpy as np
from PIL import Image

d = os.path.join(sys.argv[1], "old")
c = np.asarray(Image.open(os.path.join(d, "v_flash_grenade_color.png")).convert("RGBA"), np.float32) / 255
n = np.asarray(Image.open(os.path.join(d, "v_flash_grenade_normal.png")).convert("RGBA"), np.float32) / 255
Image.fromarray((c[..., :3] * 255 + 0.5).astype(np.uint8)).save(os.path.join(d, "old_color.png"))
Image.fromarray((c[..., 3] * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(d, "old_metal.png"))
Image.fromarray((n[..., 2] * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(d, "old_rough.png"))
x, y = n[..., 0] * 2 - 1, n[..., 1] * 2 - 1
tx, ty = (x + y) * 0.5, (x - y) * 0.5
v = np.stack((tx, ty, 1 - np.abs(tx) - np.abs(ty)), -1)
v /= np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-6)
Image.fromarray(((v * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)).save(os.path.join(d, "old_normal_gl.png"))
print("metal mean", c[..., 3].mean(), "rough mean", n[..., 2].mean(), "normal z mean", v[..., 2].mean())
