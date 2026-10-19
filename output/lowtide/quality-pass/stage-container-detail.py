from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import lowtide_container as C
import lowtide_map as LT
from importlib.machinery import SourceFileLoader
prepare=SourceFileLoader('prepare_container_detail',str(Path(__file__).with_name('prepare-container-detail.py'))).load_module()
OUT=Path(__file__).resolve().parent/'container-detail'
before=json.loads((OUT/'before.json').read_text())
stage=OUT/'stage/models/maps/lowtide'
stage.mkdir(parents=True,exist_ok=True)
def digest(data): return hashlib.sha256(data).hexdigest()
report={}
changes={}
previous=json.loads((OUT/'manifest.json').read_text()) if (OUT/'manifest.json').exists() else None
for name,records in C.layouts().items():
    source=ROOT/'Assets/models/maps/lowtide'/f'{name}.obj'
    live=source.read_bytes()
    old_live=before['models'][name]['old_sha256']
    if digest(live)!=old_live:
        previous_change=previous['changes'][f'models/maps/lowtide/{name}.obj'] if previous else {}
        assert digest(live) in (previous_change.get('before'),previous_change.get('after')), 'Unexpected live change'
    raw=(OUT/'before'/source.name).read_bytes()
    assert digest(raw)==before['models'][name]['old_sha256'],name
    text=raw.decode()
    old=prepare.faces((OUT/(name+'-old.obj')).read_text())
    new=K.Model()
    for args,kwargs in records: C.build(new,*args,**kwargs)
    LT.configure(new)
    model_path=OUT/(name+'-new.obj')
    K.write_obj(model_path,new,name)
    replacement=model_path.read_text()
    new_faces=prepare.faces(replacement)
    # Check finite, correctly oriented surface and smooth normals before export.
    for material,items in new.polygons.items():
        for index,(points,normal) in enumerate(items):
            points=np.asarray(points)
            assert np.isfinite(points).all()
            cross=np.cross(points[1]-points[0],points[2]-points[0])
            assert np.linalg.norm(cross)>1e-8,(material,index,'degenerate')
            assert np.dot(cross,normal)>0,(material,index,'winding')
            normals=new.polygon_normals.get((material,index))
            if normals is not None:
                assert all(abs(np.linalg.norm(n)-1)<1e-6 and np.dot(n,normal)>0 for n in normals)
    counts=Counter()
    positions=[]
    material=None
    remove=old.copy()
    kept=[]
    for line in text.splitlines():
        fields=line.split()
        if fields and fields[0] in ('v','vt','vn'):
            counts[fields[0]]+=1
            if fields[0]=='v': positions.append(tuple(float(v) for v in fields[1:]))
        elif fields and fields[0]=='usemtl': material=fields[1]
        elif fields and fields[0]=='f':
            key=(material,tuple(positions[int(x.split('/')[0])-1] for x in fields[1:]))
            if remove[key]>0:
                remove[key]-=1
                continue
        kept.append(line)
    assert sum(remove.values())==0
    attributes=[line for line in replacement.splitlines() if line.startswith(('v ','vt ','vn '))]
    appended=[]
    for line in replacement.splitlines():
        if line.startswith('usemtl '): appended.append(line)
        elif line.startswith('f '):
            entries=[]
            for point in line.split()[1:]:
                a,b,c=map(int,point.split('/'))
                entries.append(f'{a+counts["v"]}/{b+counts["vt"]}/{c+counts["vn"]}')
            appended.append('f '+' '.join(entries))
    output=('\n'.join(kept+attributes+appended)+'\n').encode()
    target=stage/f'{name}.obj'
    target.write_bytes(output)
    expected=prepare.faces(text)-old+new_faces
    assert prepare.faces(output.decode())==expected
    # Every pre-existing attribute and every face outside the four props remains verbatim.
    assert [s for s in kept if s.startswith(('v ','vt ','vn '))]==[s for s in text.splitlines() if s.startswith(('v ','vt ','vn '))]
    for material in new.polygons:
        assert f'from = "{material}.vmat"' in source.with_suffix('.vmdl').read_text(),material
    changes[f'models/maps/lowtide/{name}.obj']={'before':digest(live),'after':digest(output)}
    report[name]={'removed':sum(old.values()),'added':sum(new_faces.values()),'other_triangles_preserved':sum(prepare.faces(text).values())-sum(old.values())}
manifest={'changes':changes,'protected':before['protected'],'models':report,'geometry':'Rounded folded sheet edges, bevelled structural rails and locking brackets, hollow corner castings with three open lifting apertures each. Existing materials, source textures, placement and collision retained.'}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'models':report,'protected':len(before['protected'])},indent=2))
