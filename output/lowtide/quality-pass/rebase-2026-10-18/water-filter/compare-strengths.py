from pathlib import Path
import sys, json
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT/'Tools'))
import lowtide_water_filter_review as R
import lowtide_water_filter as W
out = Path(__file__).resolve().parent/'strength-review'
out.mkdir(exist_ok=True)
rgb = np.asarray(Image.open(R.BRICK).convert('RGB'), np.float32)/255
brick = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
inputs = R.water_inputs(R.CASES['bank'], brick)
_, _, _, _, projection = R.camera(R.CASES['bank'], R.WIDTH, R.HEIGHT)
dy, dx = np.gradient(inputs['uv'], axis=(0, 1))
dimensions = np.array(inputs['chain'][0].shape[1::-1])
footprint = np.maximum(np.linalg.norm(dx*dimensions, axis=-1), np.linalg.norm(dy*dimensions, axis=-1))
for strength in (.08, .12, .20):
    inputs['lod'] = R.mip_lod(inputs['rough'], footprint, dimensions, projection, len(inputs['chain']), strength)
    R.display(R.compose(inputs, True), f'FILTER STRENGTH {strength:g} | SYNTHETIC FIXTURE').save(out/f'bank-{strength:.2f}.png')
    print(f'Rendered {strength:g}', flush=True)
W.write(out/'provenance.json', json.dumps(dict(kind='Synthetic CPU filter-strength comparison', native_engine_capture=False,
    material_roughness=R.material_roughness(), original_strength=W.FILTER_STRENGTH, variants=[.08,.12,.20],
    limitation='Fixed fixture ripples, not the live ocean normal maps or shoreline'), indent=2)+'\n')
