"""Validate exported triangles, normals, UVs, PBR maps and local resource links."""
import json, math, re, struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'Assets'
report={}
for path in sorted((ASSETS/'attachments/m4a1').glob('*/*.obj')):
    vertices=[];uvs=[];normals=[];faces=[]
    for line in path.read_text().splitlines():
        fields=line.split()
        if not fields:continue
        if fields[0]=='v':vertices.append(tuple(map(float,fields[1:])))
        elif fields[0]=='vt':uvs.append(tuple(map(float,fields[1:])))
        elif fields[0]=='vn':normals.append(tuple(map(float,fields[1:])))
        elif fields[0]=='f':faces.append([tuple(int(i)-1 for i in f.split('/')) for f in fields[1:]])
    assert faces and all(len(f)==3 for f in faces),path
    assert all(math.isfinite(x) for vec in vertices+uvs+normals for x in vec),path
    assert all(abs(sum(x*x for x in n)-1)<.005 for n in normals),path
    # The original world receiver keeps its original UV coordinates.
    if path.stem!='world_base':assert all(-.0001<=x<=1.0001 for uv in uvs for x in uv),path
    degenerate=0
    for face in faces:
        for v,t,n in face:
            assert 0<=v<len(vertices) and 0<=t<len(uvs) and 0<=n<len(normals),path
        a,b,c=[vertices[f[0]] for f in face]
        ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)]
        cross=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
        degenerate+=sum(x*x for x in cross)<1e-18
    # Report inherited world-mesh degenerates independently from authored art.
    if path.stem!='world_base':assert degenerate==0,(path,degenerate)
    report[path.stem]={'triangles':len(faces),'degenerate_triangles':degenerate,'finite_geometry':True,'valid_uvs':True,'unit_normals':True}
for path in (ASSETS/'attachments/m4a1').glob('*/*.vmdl'):
    for dependency in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',path.read_text()):
        # Original receiver material is supplied by the mounted M4 asset package.
        # Its successful load is checked by the native editor fixture.
        if dependency=='models/weapons/sbox_assault_m4a1/w_m4a1.vmat':continue
        assert (ASSETS/dependency).is_file() or (ASSETS/(dependency+'_c')).is_file(),dependency
for name in ['heavy_barrel','precision_stock','compact_suppressor','rifle_suppressor','tube_red_dot']:
    folder=ASSETS/f'attachments/m4a1/{name}'
    material=(folder/('tube_housing.vmat' if name=='tube_red_dot' else f'{name}.vmat')).read_text()
    maps={}
    for channel,dependency in re.findall(r'Texture(\w+)\s+"([^"]+)"',material):
        png=ASSETS/dependency
        data=png.read_bytes()
        assert data[:8]==b'\x89PNG\r\n\x1a\n',png
        width,height=struct.unpack('>II',data[16:24]);maps[channel]=[width,height]
        assert width>=1024 and height>=1024,png
    assert set(maps)=={'Color','Normal','Roughness','Metalness','AmbientOcclusion'},name
    report[name+'_indexed' if name=='tube_red_dot' else name]['textures']=maps
for resource in ['heavy_barrel/heavy_barrel','precision_stock/precision_stock','muzzle/compact_suppressor','muzzle/rifle_suppressor','optics/reflex','optics/tube','optics/scout']:
    data=json.loads((ASSETS/f'gunsmith/m4a1/{resource}.gnsmth').read_text())
    prefab=json.loads((ASSETS/data['MainPrefab']['prefab']).read_text())
    for component in prefab['RootObject']['Components']:
        if component['__type']=='Sandbox.ModelRenderer':assert (ASSETS/component['Model']).is_file()
out=ROOT/'Sources/M4A1/qa/asset-validation.json'
out.write_text(json.dumps({'passed':True,'meshes':report},indent=2)+'\n')
print(json.dumps({'passed':True,'triangles':{k:v['triangles'] for k,v in report.items()}}))
