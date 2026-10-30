"""Fill installed shutter recesses, without regenerating the town or saving its scene."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/shop-thresholds'
HOOK='slab_at( model, wall, o.r0 - .25, o.r1 + .25, -4.5, .25, o.z0 - .75, o.z0 + .125, "ashlar_grey" )'
MARKER=b'# belltower-shop-thresholds-v1\n'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def openings(path):
    vertices=[None];paint=None;rows=[];seen=set()
    for line in path.open('rb'):
        if line.startswith(b'v '):
            y,z,x=map(float,line.split()[1:]);vertices.append(np.array((x,y,z)))
        elif line.startswith(b'usemtl '):paint=line.split()[1]
        elif line.startswith(b'f ') and paint==b'roller_grey':
            pts=[vertices[int(t.split(b'/')[0])] for t in line.split()[1:]]
            assert len(pts)==3
            bottom=min(p[2] for p in pts);top=max(p[2] for p in pts)
            low=[p for p in pts if abs(p[2]-bottom)<.001]
            if len(low)!=2 or top-bottom<40:continue
            normal=np.cross(pts[1]-pts[0],pts[2]-pts[0]);normal/=np.linalg.norm(normal)
            assert abs(normal[2])<.001 and max(abs(normal[:2]))>.999
            key=tuple(sorted(tuple(p) for p in low));assert key not in seen;seen.add(key)
            rows.append((low,normal))
    assert rows,'No shutter bases found.'
    return rows


def append(source,target,fragment):
    counts=Counter()
    for line in source.open('rb'):
        key=line.split(maxsplit=1)[0] if line.strip() else b''
        if key in (b'v',b'vt',b'vn'):counts[key]+=1
    tables=[];faces=[]
    for line in fragment.open('rb'):
        if line.startswith((b'v ',b'vt ',b'vn ')):tables.append(line)
        elif line.startswith(b'usemtl '):faces.append(line)
        elif line.startswith(b'f '):
            tokens=[b'/'.join(str(int(v)+counts[k]).encode() for k,v in zip((b'v',b'vt',b'vn'),t.split(b'/'))) for t in line.split()[1:]]
            faces.append(b'f '+b' '.join(tokens)+b'\n')
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    with target.open('ab') as f:f.write(MARKER);f.writelines(tables);f.writelines(faces)
    with target.open('rb') as f:assert hashlib.sha256(f.read(source.stat().st_size)).hexdigest()==sha(source)


def main():
    stage=OUT/'stage-v1';stage.mkdir(parents=True,exist_ok=False)
    files={};reports={};protected={}
    for side in ('west','east'):
        doc=ROOT/f'Assets/models/maps/belltower/belltower_{side}.vmdl'
        candidates=re.findall(r'filename\s*=\s*"([^"]+roller_grey\.obj)"',doc.read_text())
        assert len(candidates)==1
        source=ROOT/'Assets'/candidates[0];relative=source.relative_to(ROOT).as_posix()
        assert MARKER not in source.read_bytes(),'Thresholds already installed.'
        model=K.Model();rows=openings(source);details=[]
        for (a,b),normal in rows:
            along=(b-a)/np.linalg.norm(b-a)
            # The front is 4 inches outside the shutter; overlap both jambs and
            # the paving slightly. The top clears the coplanar ground by 1/8 inch.
            corners=[p+normal*d+along*s for p in (a,b) for d in (-.5,4.25) for s in (-.25,.25)]
            plan=np.array([(-p[1],p[0],p[2]) for p in corners])
            lo,hi=plan.min(axis=0),plan.max(axis=0);lo[2]=a[2]-.75;hi[2]=a[2]+.125
            model.box(lo,hi,'ashlar_grey')
            for p in ((a+b)/2,(a+b)/2+normal*4):
                q=np.array((-p[1],p[0],a[2]+.1));assert np.all(q>=lo) and np.all(q<=hi)
            details.append({'edge':[a.tolist(),b.tolist()],'outward':normal.tolist()})
        assert not model.boxes and not model.hulls
        fragment=stage/f'proof/{side}.obj';fragment.parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(fragment,model,f'belltower_{side}')
        target=stage/relative;append(source,target,fragment)
        backup=stage/'before'/relative;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
        files[relative]={'before':sha(source),'after':sha(target),'source':target.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix(),'original_bytes':source.stat().st_size}
        protected[doc.relative_to(ROOT).as_posix()]=sha(doc)
        material=source.parent/'materials.mtl'
        assert 'newmtl ashlar_grey' in material.read_text()
        protected[material.relative_to(ROOT).as_posix()]=sha(material)
        for path in doc.parent.glob(f'belltower_{side}_hulls_*.obj'):protected[path.relative_to(ROOT).as_posix()]=sha(path)
        reports[side]={'thresholds':len(rows),'triangles_added':model.triangle_count(),'openings':details}
    assert HOOK in (ROOT/'Tools/belltower_map.py').read_text()
    manifest={'revision':'belltower-shop-thresholds-v1','files':files,'protected_sha256':protected,
        'source_sha256':{p:sha(ROOT/p) for p in ('Tools/belltower_shop_thresholds.py','Tools/map_kit.py')},
        'generator_hook':HOOK,'reports':reports,'thresholds':sum(r['thresholds'] for r in reports.values()),
        'original_geometry_bytes_exact':True,'collision_unchanged':True,'scene_not_modified':True}
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'compile.json').write_text(json.dumps({'calls':[{'name':'asset_compile','arguments':{
        'path':f'models/maps/belltower/belltower_{side}.vmdl','full':False}} for side in ('west','east')]}))
    (OUT/'info.json').write_text(json.dumps({'calls':[{'name':'asset_info','arguments':{
        'path':f'models/maps/belltower/belltower_{side}.vmdl'}} for side in ('west','east')]}))
    print(json.dumps({side:{k:v for k,v in report.items() if k!='openings'} for side,report in reports.items()}))


if __name__=='__main__':main()
