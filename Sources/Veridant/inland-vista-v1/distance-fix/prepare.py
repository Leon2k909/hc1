"""Measure generated alpha only; retain the original raster byte for byte."""
from pathlib import Path
import json
import shutil
import numpy as np
from PIL import Image
from scipy.ndimage import label

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
generation = json.loads((HERE / 'generation.json').read_text(encoding='utf-8'))
target = ROOT / generation['selected']
shutil.copy2(generation['original'], target)
with Image.open(target) as im:
    size = list(im.size)
    alpha = np.asarray(im.getchannel('A'))
labels, count = label(alpha > 140)
components = sorted(range(1, count + 1), key=lambda k: np.count_nonzero(labels == k), reverse=True)[:3]
components.sort(key=lambda k: np.nonzero(labels == k)[0].min())
panels = []
for component in components:
    rows, columns = np.nonzero(labels == component)
    top, bottom = int(rows.min()), int(rows.max())
    feet, tops = [], []
    for x in np.linspace(8, size[0]-9, 145):
        ys = np.nonzero(labels[:, int(x)] == component)[0]
        feet.append(float(ys.max()) if len(ys) else float(bottom))
        tops.append(float(ys.min()) if len(ys) else float(top))
    panels.append({'uv_rect_px': [8, top-3, size[0]-8, bottom+3],
                   'minimum_foot_row': min(feet), 'foot_rows': feet, 'top_rows':tops})
metadata = {'source': target.relative_to(ROOT).as_posix(), 'size': size, 'panels': panels}
(HERE / 'texture.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
print(json.dumps({'size': size, 'rectangles': [p['uv_rect_px'] for p in panels]}, indent=2))
scrub = json.loads((HERE / 'scrub-generation.json').read_text(encoding='utf-8'))
target = ROOT / scrub['selected']
shutil.copy2(scrub['original'],target)
with Image.open(target) as im:
    size=list(im.size); alpha=np.asarray(im.getchannel('A'))
rectangles=[]
for row in range(2):
    for col in range(4):
        x0,x1=int(col*size[0]/4),int((col+1)*size[0]/4)
        y0,y1=int(row*size[1]/2),int((row+1)*size[1]/2)
        ys,xs=np.nonzero(alpha[y0:y1,x0:x1]>140)
        rectangles.append([x0+int(xs.min()),y0+int(ys.min()),x0+int(xs.max())+1,y0+int(ys.max())+1])
(HERE/'scrub-texture.json').write_text(json.dumps({'source':scrub['selected'],'size':size,'rectangles':rectangles},indent=2),encoding='utf-8')
