"""Render independent crown/shadow passes to locate construction artifacts."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'Tools'))
import belltower_photographic_canopy as C
import numpy as np
from PIL import Image

C.numba.set_num_threads(2)
out = ROOT/'output/belltower/quality/canopy-photo-v1-diagnostic'
out.mkdir(exist_ok=True)
crowns = C.T.swatch_crowns()
size, span = 768, 1600.
step = span/(size-1)
top, cov = np.zeros((size, size)), np.zeros((size, size))
colour = np.zeros((size, size, 3))
cid = np.full((size, size), -1, np.int64)
C.photographic_tops(crowns, 0, span, step, step, step, top, colour, cov, cid, C.V._GRADIENTS)
shadow = np.zeros_like(top)
C.P._shadows(crowns, 0, span, step, step, step, top, cid, shadow)
unshadowed = colour+C.P.WOOD_FLOOR*(1-cov[..., None])
shaded = unshadowed*(1-shadow[..., None]*(1-C.P.SHADOW_TINT))
Image.fromarray(C.P.srgb8(unshadowed)).save(out/'without-shadow.png')
Image.fromarray(C.P.srgb8(shaded)).save(out/'with-shadow.png')
Image.fromarray(np.uint8(np.clip(shadow, 0, 1)*255)).save(out/'shadow.png')
palette = np.random.default_rng(913).uniform(.15, 1, (len(crowns)+1, 3))
palette[0] = 0
Image.fromarray(np.uint8(palette[cid+1]*255)).save(out/'crown-owners.png')
np.savez_compressed(out/'buffers.npz', top=top, cov=cov, cid=cid, shadow=shadow)
report = {'crowns_sha256':hashlib.sha256(crowns.tobytes()).hexdigest(),
          'image_matches_v1_swatch':np.array_equal(np.asarray(Image.open(out/'with-shadow.png')), np.asarray(Image.open(ROOT/'output/belltower/quality/canopy-photo-v1-swatch/photographic.png'))),
          'state':'offline diagnostic; no live assets changed'}
(out/'diagnostic.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
