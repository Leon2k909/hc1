import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'Tools'))
import reefhall_map as R
import reefhall_consoles as C
import reefhall_monitors as M

OUT = Path(__file__).resolve().parent
before = json.loads((OUT/'before/report.json').read_text())
after = json.loads((OUT/'staging/report.json').read_text())
for key in ('boxes','hulls','collision_sha256','lights'):
    assert before[key] == after[key], (key,before[key],after[key])
for path in (OUT/'before').glob('*hulls*.obj'):
    assert path.read_bytes() == (OUT/'staging'/path.name).read_bytes(), path

def obj_faces(path):
    verts,uvs,normals = [None],[None],[None]
    groups = {}
    degenerate = {}
    paint = None
    for line in path.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] in ('v','vt','vn'):
            target = {'v':verts,'vt':uvs,'vn':normals}[parts[0]]
            target.append(tuple(map(float,parts[1:])))
        elif parts[0] == 'usemtl':
            paint = parts[1]
        elif parts[0] == 'f':
            ids = [list(map(int,s.split('/'))) for s in parts[1:]]
            face = tuple((verts[i],uvs[j],normals[k]) for i,j,k in ids)
            points = np.asarray([p[0] for p in face])
            assert np.isfinite(points).all(), paint
            area = np.linalg.norm(np.cross(points[1]-points[0],points[2]-points[0]))
            if area <= 1e-8:
                degenerate[paint] = degenerate.get(paint,0)+1
            groups.setdefault(paint,[]).append(face)
    return groups,degenerate

old,old_degenerate = obj_faces(OUT/'before/reefhall_control.obj')
new,new_degenerate = obj_faces(OUT/'staging/reefhall_control.obj')
assert old_degenerate == new_degenerate, (old_degenerate,new_degenerate)
for paint,faces in old.items():
    if paint not in ('rh_console_bezel','rh_console_edge'):
        assert faces == new[paint], paint
assert len(new['rh_console_lcd']) == 32
counts = {0:0,1:0}
for centre,length in (((2600,-260),280),((2600,260),280),((2220,0),180)):
    for i in range(int(length/44)):
        counts[M.variant(i,centre)] += 1
assert counts == {0:8,1:8}, counts

preview = R.Model()
C.configure(preview)
fr = R.Frame((0,0),(1,0))
for u,kind in ((-23,0),(23,1)):
    M.build(preview,fr,u,0,kind)
    R.uv_quad(preview,C.SCREEN,[(u-18.2,8.74,44.3),(u+18.2,8.74,44.3),
                              (u+18.2,8.74,64.775),(u-18.2,8.74,64.775)],
              [(0,0),(0.5,0),(0.5,0.5),(0,0.5)],(0,-1,0))
R.K.write_model(OUT/'studio','models/maps/reefhall','monitor_pair',preview)
result = dict(after,variants={'charcoal':counts[0],'aluminium':counts[1]},
              lcd_triangles_unchanged=32,other_surfaces_unchanged=True,
              collision_hull_files_identical=True,monitor_zero_area_triangles=0,
              preexisting_zero_area_triangles_unchanged=old_degenerate)
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
