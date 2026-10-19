import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'Tools'))
import belltower_map as B
import belltower_wall_cleanup as W
m=B.Model()
B.town_walls(m,trim_buried=False)
smallest=float('inf')
changed=0
for paint in ('rubble','ashlar','ashlar_grey'):
    for points, normal in m.polygons[paint]:
        pieces=W.visible_pieces(points)
        old_area=W.polygon_area(points)
        new_area=sum(W.polygon_area(p) for p in pieces)
        assert new_area<=old_area+.001
        if abs(new_area-old_area)<.001:
            continue
        changed+=1
        for piece in pieces:
            for k in range(1,len(piece)-1):
                cross=np.cross(piece[k]-piece[0],piece[k+1]-piece[0])
                assert np.dot(cross,normal)>1e-5, (paint,piece,normal)
                smallest=min(smallest,np.linalg.norm(cross)*.5)
threshold=[p for p,n in m.polygons['ashlar'] if n[2]>.9 and all(abs(v[2])<.001 for v in p)]
assert threshold and all(len(W.visible_pieces(p))==1 and np.allclose(W.visible_pieces(p)[0],p) for p in threshold)
print({'changed_polygons_per_half':changed,'smallest_changed_triangle_square_inches':smallest,'winding_and_gate_threshold_passed':True})
