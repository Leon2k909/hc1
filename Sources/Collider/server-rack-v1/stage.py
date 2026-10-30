"""Replace only the pictured east cabinet in the installed combined detail mesh."""
from pathlib import Path
import hashlib
import json
import re
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_server_rack as R
import collider_map as M

OUT=ROOT/'output/collider-server-rack-20261027'
STAGE=OUT/'stage-v1'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    assert not STAGE.exists(), 'Use a fresh stage for revisions'
    assets=STAGE/'assets/models/maps/collider'
    assets.mkdir(parents=True)
    relative='models/maps/collider/collider_detail.obj'
    source=ROOT/'Assets'/relative
    original_bytes=source.read_bytes()
    lines=original_bytes.decode().splitlines(keepends=True)
    vs,uvs,normals=[],[],[]
    retained=[];removed=[];paint=None
    for line_no,line in enumerate(lines,1):
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uvs.append(line)
        elif line.startswith('vn '):normals.append(line)
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            points=np.array([vs[int(w.split('/')[0])-1] for w in line.split()[1:]])
            lo,hi=points.min(0),points.max(0)
            if np.all(lo>=[402,43,-.1]) and np.all(hi<=[458,115,139]):
                removed.append({'line':line_no,'material':paint,'face':line.rstrip()});continue
            assert not (np.all(hi>=[402,43,-.1]) and np.all(lo<=[458,115,139])), 'A neighbouring face crosses the cabinet bounds'
        retained.append(line)
    assert len(removed)==276, f'Unexpected east rack geometry: {len(removed)}'
    model=K.Model();R.build(model,collision=False);M.configure(model)
    generated=STAGE/'generated/collider_detail.obj';generated.parent.mkdir()
    K.write_obj(generated,model,'collider_detail')
    offsets=(len(vs),len(uvs),len(normals));extra=['\n# Collider east server rack v1\no collider_east_server_rack_v1\n']
    added=0
    for line in generated.read_text().splitlines(keepends=True):
        if line.startswith(('#','mtllib ','o ')):continue
        if line.startswith('f '):
            line='f '+' '.join('/'.join(str(int(v)+offsets[k]) for k,v in enumerate(w.split('/'))) for w in line.split()[1:])+'\n'
            added+=1
        extra.append(line)
    (assets/'collider_detail.obj').write_text(''.join(retained+extra),newline='')
    original_mtl=(ROOT/'Assets/models/maps/collider/collider_detail.mtl').read_bytes()
    assert set(model.polygons)<=set(re.findall(r'newmtl (\S+)',original_mtl.decode()))
    # Change only the east rack box. Other physics and all material bindings stay exact.
    document_path=ROOT/'Assets/models/maps/collider/collider_detail.vmdl'
    document_bytes=document_path.read_bytes()
    old_doc=document_bytes.decode()
    pattern=r'\{\s*_class = "PhysicsShapeBox"[^}]*\}'
    boxes=list(re.finditer(pattern,old_doc))
    candidates=[m for m in boxes if 'origin = [ 80.0000, -430.0000, 69.0000 ]' in m[0]]
    assert len(candidates)==1
    old=candidates[0][0]
    new=old.replace('origin = [ 80.0000, -430.0000, 69.0000 ]','origin = [ -60.0000, -430.0000, 42.0000 ]').replace(
        'dimensions = [ 48.0000, 60.0000, 138.0000 ]','dimensions = [ 28.0000, 44.0000, 84.0000 ]')
    assert new!=old
    new_doc=old_doc[:candidates[0].start()]+new+old_doc[candidates[0].end():]
    assert len(list(re.finditer(pattern,new_doc)))==len(boxes)
    (assets/'collider_detail.vmdl').write_text(new_doc,newline='')
    assert source.read_bytes()==original_bytes, 'Shared detail mesh changed while staging'
    assert document_path.read_bytes()==document_bytes, 'Shared physics changed while staging'
    files=[]
    for ext in ('.obj','.vmdl'):
        rel='models/maps/collider/collider_detail'+ext
        target=ROOT/'Assets'/rel;staged=STAGE/'assets'/rel;backup=STAGE/'before'/rel
        expected=original_bytes if ext=='.obj' else document_bytes
        assert target.read_bytes()==expected, 'Shared rack target changed before backup'
        backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(expected)
        files.append({'relative':rel,'before':sha(target),'after':sha(staged)})
    # Deliberately exclude the independently edited structure/machine assets.
    protected=['scenes/maps/Collider/collider.scene','models/maps/collider/collider_detail.mtl',
        'models/maps/collider/collider_detail_hulls_metal.obj','models/maps/collider/collider_glass.obj','models/maps/collider/collider_glass.vmdl']
    manifest={'revision':'collider-east-server-rack-v1','files':files,'oldRackPosition':[430,80,0],
        'newRackPosition':[430,-60,0],'newSize':R.SIZE,'removedTriangles':len(removed),'addedTriangles':added,
        'beforeTriangles':sum(s.startswith('f ') for s in lines),'afterTriangles':sum(s.startswith('f ') for s in retained)+added,
        'removedFaces':removed,'oldPhysicsBox':old,'newPhysicsBox':new,
        'protected':{p:sha(ROOT/'Assets'/p) for p in protected if (ROOT/'Assets'/p).exists()},
        'source':{'Tools/collider_server_rack.py':sha(ROOT/'Tools/collider_server_rack.py')}}
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('removedFaces','protected','oldPhysicsBox','newPhysicsBox','source')}))


if __name__=='__main__':build()
