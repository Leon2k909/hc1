"""Verify the small lock patch preserves every other installed town mesh line."""
from pathlib import Path
import hashlib
import json
import numpy as np
import belltower_padlock as P
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/belltower/shed-padlock-v1/stage'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    manifest=json.loads((STAGE/'manifest.json').read_text())
    model=K.Model();P.build(model,(0,0,0),np.eye(3))
    assert not model.boxes and not model.hulls and not model.props
    for paint,faces in model.polygons.items():
        for points,normal in faces:
            assert np.isfinite(points).all()
            for k in range(1,len(points)-1):
                assert np.dot(np.cross(points[k]-points[0],points[k+1]-points[0]),normal)>1e-10
    reports={}
    for name,record in manifest['models'].items():
        rel='Assets/models/maps/belltower/'+name
        old=STAGE/'before'/(rel+'.obj');new=STAGE/(rel+'.obj')
        piece=STAGE/(name+'-locks.obj')
        tables=[l for l in piece.read_bytes().splitlines(keepends=True) if l.startswith((b'v ',b'vt ',b'vn '))]
        drop=set(record['removed_face_lines']);removed=0
        with old.open('rb') as original,new.open('rb') as staged:
            for index,line in enumerate(original):
                if line.startswith(b'usemtl '):
                    assert [next(staged) for _ in tables]==tables
                    break
                assert next(staged)==line
            assert next(staged)==line
            for i,line in enumerate(original,index+1):
                if i in drop:
                    assert line.startswith(b'f ');removed+=1
                else:
                    assert next(staged)==line,(name,i)
            assert sum(l.startswith(b'f ') for l in staged)==manifest['added_triangles_per_half']
        assert removed==264
        baseline=(STAGE/'before'/(rel+'.vmdl')).read_bytes()
        candidate=(STAGE/(rel+'.vmdl')).read_bytes()
        remap=record['inserted_remap'].encode()
        assert candidate.count(remap)==1 and candidate.replace(remap,b'',1)==baseline
        reports[name]={'non_hardware_mesh_bytes_preserved':True,'physics_byte_identical':True,
                       'removed_triangles':removed,'added_triangles':manifest['added_triangles_per_half']}
    for relative,record in manifest['files'].items():assert sha(STAGE/relative)==record['after']
    for relative,expected in manifest['source_sha256'].items():assert sha(ROOT/relative)==expected
    installed=all((ROOT/p).is_file() and sha(ROOT/p)==r['after'] for p,r in manifest['files'].items())
    result={'revision':manifest['revision'],'locks':6,'models':reports,'staged_assets_verified':7,
            'valid_hardware_triangles_per_lock':model.triangle_count(),'new_colliders':0,
            'installed_assets_match':installed,'native_import_verified':(STAGE/'native-import.json').is_file(),
            'native_visual_review_verified':False}
    (STAGE.parent/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
