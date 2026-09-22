"""Write compact indexed OBJ sources with one material batch per surface."""
from pathlib import Path
import json,math
ROOT=Path(__file__).resolve().parents[2];folder=ROOT/'Assets/attachments/m4a1/optics'
report={}
for name,source_name in [('reflex','reflex_source'),('scout','scout_optimized')]:
    positions=[];uvs=[];normals=[];batches={};material='';lookup={};values=[]
    for line in (ROOT/f'Sources/M4A1/{source_name}.obj').read_text().splitlines():
        f=line.split()
        if not f:continue
        if f[0]=='v':positions.append(f[1:])
        elif f[0]=='vt':uvs.append(f[1:])
        elif f[0]=='vn':normals.append(f[1:])
        elif f[0]=='usemtl':material=f[1]
        elif f[0]=='f':
            face=[]
            for item in f[1:]:
                v,t,n=(int(i)-1 for i in item.split('/'))
                key=tuple(positions[v]+uvs[t]+normals[n])
                if key not in lookup:lookup[key]=len(values)+1;values.append(key)
                face.append(lookup[key])
            a,b,c=[list(map(float,values[index-1][:3])) for index in face]
            ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)]
            cross=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
            if sum(x*x for x in cross)>=1e-18:batches.setdefault(material,[]).append(face)
    if name=='scout':
        # The donor has opaque rear caps and curved front glass intended for a
        # missing render-camera shader. Replace both with one clear rear lens.
        batches.pop('material',None);batches.pop('material_002',None)
        indices=[];segments=64
        points=[(-.0425439,1.0682995)]+[(-.0425439+.447*math.cos(i*math.tau/segments),1.0682995+.447*math.sin(i*math.tau/segments)) for i in range(segments)]
        for y,z in points:
            values.append(tuple(str(x) for x in [y,z,-4.65,(y+.0425439)/.894+.5,(z-1.0682995)/.894+.5,0,0,-1]))
            indices.append(len(values))
        batches['material_002']=[[indices[0],indices[(i+1)%segments+1],indices[i+1]] for i in range(segments)]
    # A centered reticle uses the clear aperture, not the donor texture atlas.
    lens_material='reflex_glass' if name=='reflex' else 'material_002'
    lens_vertices={index for face in batches[lens_material] for index in face}
    low=[min(float(values[index-1][axis]) for index in lens_vertices) for axis in (0,1)]
    high=[max(float(values[index-1][axis]) for index in lens_vertices) for axis in (0,1)]
    for index in lens_vertices:
        value=list(values[index-1])
        value[3:5]=[f'{(float(value[axis])-low[axis])/(high[axis]-low[axis]):.8f}' for axis in (0,1)]
        values[index-1]=tuple(value)
    out=[f'mtllib {name}.mtl',f'o {name}']
    for val in values:out.extend(['v '+' '.join(val[:3]),'vt '+' '.join(val[3:5]),'vn '+' '.join(val[5:])])
    for mat,faces in sorted(batches.items(),key=lambda pair:0 if pair[0] in ['reflex_glass','material_002'] else 1):
        out.append('usemtl '+mat)
        out.extend('f '+' '.join(f'{i}/{i}/{i}' for i in face) for face in faces)
    target=f'{name}_indexed.obj';(folder/target).write_text('\n'.join(out)+'\n')
    (folder/f'{name}.mtl').write_text('\n'.join(f'newmtl {material}\nKd 1 1 1' for material in batches)+'\n')
    vmdl=folder/f'{name}.vmdl';vmdl.write_text(vmdl.read_text().replace(f'/{source_name}.obj',f'/{target}'))
    if name=='scout' and 'optic_lens_baffle.vmat' not in vmdl.read_text():
        vmdl.write_text(vmdl.read_text().replace('remaps = [','remaps = [ { from = "optic_lens_baffle.vmat" to = "attachments/m4a1/optics/scout_lens_baffle.vmat" },',1))
    report[name]={'triangles':sum(len(f) for f in batches.values()),'vertices':len(values),'material_batches':len(batches)}
(ROOT/'Sources/M4A1/qa/optics').mkdir(parents=True,exist_ok=True)
(ROOT/'Sources/M4A1/qa/optics/mesh-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
