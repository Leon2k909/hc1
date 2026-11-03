from pathlib import Path
import json,collections
ROOT=Path(__file__).resolve().parents[3]
for name in ('orion_launch_control','orion_fuel'):
    src=ROOT/f'Assets/models/maps/orion/{name}.obj'
    lines=src.read_text().splitlines();verts=[tuple(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')]
    paint='';pts=[]
    for l in lines:
        if l.startswith('usemtl '):paint=l.split()[1]
        if l.startswith('f ') and paint=='oa_chair':pts.extend(verts[int(t.split('/')[0])-1] for t in l.split()[1:])
    print(json.dumps(dict(model=name,chair_vertices=len(pts),heights=sorted(set(round(p[1],1) for p in pts)),bounds=[min(p[0] for p in pts),max(p[0] for p in pts),min(p[2] for p in pts),max(p[2] for p in pts)])))
