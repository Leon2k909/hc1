from pathlib import Path
import json
import sys
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw

root=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(root/'Tools'))
import lowtide_concrete_wear as C
settings=json.loads((C.SOURCE/'wear-layout.json').read_text())
shapes,_=C.collision(1,settings)
bounds=settings['bounds_plan_inches']
occupied=C.occupancy(shapes,bounds,(760,1550))
distance=ndimage.distance_transform_edt(~occupied)
points=sorted(set(tuple(p) for route in settings['routes'] for p in (route['start'],route['end'])))
points += [(650,650),(650,660),(670,670),(640,650),(700,680),(690,650),(710,700),(650,1100),(760,960)]
print(json.dumps([dict(point=p,clearance=round(float(C.values(distance,np.asarray([p]),bounds)[0]),2)) for p in points],indent=2))
image=Image.fromarray(np.where(occupied[...,None],np.array((45,50,52)),np.array((224,222,214))).astype(np.uint8))
draw=ImageDraw.Draw(image)
for x in range(0,760,100): draw.line((x,0,x,1550),fill=(160,158,151),width=1)
for y in range(0,1550,100): draw.line((0,y,760,y),fill=(160,158,151),width=1)
for p in points:
    x,y=C.to_pixel(p,bounds,(760,1550))
    draw.ellipse((x-4,y-4,x+4,y+4),fill=(170,60,35))
    draw.text((x+6,y-4),str(p),fill=(155,45,25))
image.save(C.OUT/'layout-inspection.png')
