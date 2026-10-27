"""Preserve source needle values and repair zero derived opaque normals."""
from collections import defaultdict
import math

def read_faces(path):
    vertices=[];uvs=[];normals=[];faces=defaultdict(list);paint=None
    for line in path.read_text().splitlines():
        f=line.split()
        if not f:continue
        if f[0]=='v':vertices.append(' '.join(f[1:]))
        elif f[0]=='vt':uvs.append(' '.join(f[1:]))
        elif f[0]=='vn':normals.append(' '.join(f[1:]))
        elif f[0]=='usemtl':paint=f[1]
        elif f[0]=='f':
            assert len(f)==4,'Expected triangulated source'
            refs=[tuple(int(i)-1 for i in item.split('/')) for item in f[1:]]
            faces[paint].append(tuple((vertices[v],uvs[t],normals[n]) for v,t,n in refs))
    return faces


def write_faces(path,faces):
    values=[];indices={};groups=[]
    for paint,rows in sorted(faces.items()):
        groups.append('usemtl '+paint)
        for row in rows:
            # Collapsing a thin double-sided dead branch can average opposite
            # custom normals to zero. Repair those derived opaque corners from
            # the valid triangle plane; needle-chart normals remain untouched.
            if not paint.endswith('_twig') and any(sum(float(x)**2 for x in n.split())<1e-8 for v,t,n in row):
                points=[tuple(map(float,v.split())) for v,t,n in row]
                a=[x-y for x,y in zip(points[1],points[0])];b=[x-y for x,y in zip(points[2],points[0])]
                normal=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
                length=math.sqrt(sum(x*x for x in normal));assert length>1e-12
                text=' '.join(f'{x/length:.8f}' for x in normal)
                row=tuple((v,t,text if sum(float(x)**2 for x in n.split())<1e-8 else n) for v,t,n in row)
            refs=[]
            for value in row:
                if value not in indices:indices[value]=len(values)+1;values.append(value)
                i=indices[value];refs.append(f'{i}/{i}/{i}')
            groups.append('f '+' '.join(refs))
    lines=['# Preserved source needle charts and reduced opaque branches',f'mtllib {path.stem}.mtl',f'o {path.stem}']
    lines+=['v '+v for v,t,n in values]+['vt '+t for v,t,n in values]+['vn '+n for v,t,n in values]+groups
    path.write_text('\n'.join(lines)+'\n')


