"""Compact the baked Patrol mesh without changing positions, UVs or shading."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'Assets/attachments/m4a1/tube_red_dot'
source=folder/'tube_red_dot.obj'
archive=ROOT/'Sources/M4A1/tube_red_dot_baked.obj'
if source.is_file():
    archive.write_bytes(source.read_bytes())
positions=[];uvs=[];normals=[];lookup={};values=[];batches={};material=''
for line in archive.read_text().splitlines():
    f=line.split()
    if not f:continue
    if f[0]=='v':positions.append(f[1:])
    elif f[0]=='vt':uvs.append(f[1:])
    elif f[0]=='vn':normals.append(f[1:])
    elif f[0]=='usemtl':material=f[1]
    elif f[0]=='f':
        face=[]
        for item in f[1:]:
            v,t,n=(int(x)-1 for x in item.split('/'))
            key=tuple(positions[v]+uvs[t]+normals[n])
            if key not in lookup:lookup[key]=len(values)+1;values.append(key)
            face.append(lookup[key])
        batches.setdefault(material,[]).append(face)
lines=['mtllib tube_red_dot.mtl','o tube_red_dot']
for value in values:lines.extend(['v '+' '.join(value[:3]),'vt '+' '.join(value[3:5]),'vn '+' '.join(value[5:])])
for material,faces in batches.items():
    lines.append('usemtl '+material)
    lines.extend('f '+' '.join(f'{i}/{i}/{i}' for i in face) for face in faces)
(folder/'tube_red_dot_indexed.obj').write_text('\n'.join(lines)+'\n')
vmdl=folder/'tube_red_dot.vmdl'
material=folder/'tube_red_dot.vmat'
if material.exists():(folder/'tube_housing.vmat').write_bytes(material.read_bytes())
vmdl.write_text(vmdl.read_text().replace('/tube_red_dot.obj','/tube_red_dot_indexed.obj').replace('/tube_red_dot.vmat','/tube_housing.vmat'))
# Keep the full bake in Sources and import only the indexed game mesh.
if source.exists():source.unlink()
if material.exists():material.unlink()
print({'triangles':sum(len(f) for f in batches.values()),'vertices':len(values),'batches':len(batches)})
