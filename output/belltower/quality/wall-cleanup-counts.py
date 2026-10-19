import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'Tools'))
import belltower_map as B
import belltower_wall_cleanup as W
m=B.Model()
B.town_walls(m,trim_buried=False)
before=after=0
for paint in ('rubble','ashlar','ashlar_grey'):
    for points,normal in m.polygons[paint]:
        pieces=W.visible_pieces(points)
        delta=sum(len(p)-2 for p in pieces)-(len(points)-2)
        area=W.polygon_area(points)-sum(W.polygon_area(p) for p in pieces)
        if area>.001:
            print(paint,'normal',normal,'bounds',np.min(points,axis=0),np.max(points,axis=0),'pieces',[len(p) for p in pieces],'delta',delta)
            before+=len(points)-2
            after+=sum(len(p)-2 for p in pieces)
print('CHANGED TRIANGLES',before,after)
