from pathlib import Path
from collections import defaultdict
p=Path(__file__).resolve().parents[1]/'Assets/models/props/shared/veridant_fountain_reference_top_v4/crown.obj'
v=[];t=[];n=[];groups=defaultdict(list);material='crown_surface'
for line in p.read_text().splitlines():
    if line.startswith('v '):v.append(line)
    elif line.startswith('vt '):t.append(line)
    elif line.startswith('vn '):n.append(line)
    elif line.startswith('usemtl '):material=line.split()[1]
    elif line.startswith('f '):groups[material].append(line.split()[1:])
lookup={};verts=[];faces=defaultdict(list)
for mat,items in groups.items():
    for face in items:
        ids=[]
        for item in face:
            a,b,c=map(int,item.split('/'));key=(v[a-1],t[b-1],n[c-1])
            if key not in lookup:lookup[key]=len(verts)+1;verts.append(key)
            i=lookup[key];ids.append(f'{i}/{i}/{i}')
        faces[mat].append('f '+' '.join(ids))
out=['mtllib crown.mtl']
for k in range(3):out.extend(v[k] for v in verts)
for mat,items in faces.items():out.append('usemtl '+mat);out.extend(items)
p.write_text('\n'.join(out))
print(len(verts),sum(map(len,faces.values())))
