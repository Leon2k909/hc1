import sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(root/'Tools'))
import belltower_map as B
wall=B.Model()
B.town_walls(wall)
for points,normal in wall.polygons['ivy_climb']:
    p=np.array(points)
    print('ivy world bounds',np.min(p,axis=0)[[1,0,2]]*(1,-1,1),np.max(p,axis=0)[[1,0,2]]*(1,-1,1))
