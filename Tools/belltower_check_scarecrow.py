"""Verify the staged scarecrow surgery against the exact installed-town backup."""
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
import belltower_map as B
import belltower_scarecrow as S
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/scarecrow-v1'
STAGE=OUT/'stage'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    manifest=json.loads((STAGE/'manifest.json').read_text())
    models={}
    for name,record in manifest['models'].items():
        relative=f'Assets/models/maps/belltower/{name}.obj'
        before=STAGE/'before'/relative;after=STAGE/relative
        drop=set(record['removed_face_lines']);assert len(drop)==86
        extra=[];prefix=0
        with before.open('rb') as original,after.open('rb') as updated:
            for line in original:
                if line.startswith(b'usemtl '):break
                assert next(updated)==line,(name,prefix,'existing table changed');prefix+=1
            while True:
                current=next(updated)
                if current.startswith(b'usemtl '):break
                assert current.startswith((b'v ',b'vt ',b'vn '));extra.append(current)
            assert line==current
            for index,line in enumerate(itertools.chain((line,),original),prefix):
                if index in drop:assert line.startswith(b'f ');continue
                if index==prefix:continue
                assert next(updated)==line,(name,index,'non-scarecrow face changed')
            tail=list(updated)
        assert len(extra)==record['inserted_table_lines']
        assert len(tail)==record['appended_face_lines']
        assert sum(l.startswith(b'f ') for l in tail)==manifest['new_triangles_per_half']==7480
        vertices=np.array([list(map(float,l.split()[1:])) for l in extra if l.startswith(b'v ')])
        assert np.isfinite(vertices).all()
        assert 83.9<np.ptp(vertices[:,1])<84.3
        assert 60<np.ptp(vertices[:,0])<62
        original=(STAGE/'before'/relative).with_suffix('.vmdl').read_bytes()
        updated=(STAGE/relative).with_suffix('.vmdl').read_bytes()
        extra_remaps=record['vmdl_added_remaps'].encode()
        assert updated.count(extra_remaps)==1 and updated.replace(extra_remaps,b'',1)==original
        old_mtl=(STAGE/'before'/relative).with_suffix('.mtl').read_bytes()
        new_mtl=(STAGE/relative).with_suffix('.mtl').read_bytes()
        expected=b''.join(f'newmtl {paint}\nKd 1 1 1\nd 1\n'.encode() for paint in S.MATERIALS)
        assert new_mtl==old_mtl+expected
        models[name]={'all_non_scarecrow_obj_bytes_preserved':True,'vmdl_physics_byte_identical':True,
            'removed_triangles':86,'added_triangles':7480,'staged_obj_sha256':sha(after)}
    local=K.Model();S.build(local,B.Place((0,0,0),0))
    assert not local.boxes and not local.hulls and not local.props
    assert local.triangle_count()==7480
    for faces in local.polygons.values():
        for points,n in faces:
            assert np.isfinite(points).all() and np.isfinite(n).all()
            for i in range(1,len(points)-1):
                assert np.dot(np.cross(points[i]-points[0],points[i+1]-points[0]),n)>1e-9
    for key,value in manifest['texture_sha256'].items():assert sha(ROOT/key)==value,key
    for key,value in manifest['source_sha256'].items():assert sha(ROOT/key)==value,key
    installed={p:sha(ROOT/p)==v['after'] if (ROOT/p).exists() else False for p,v in manifest['files'].items()}
    result={'revision':'scarecrow-v1','models':models,'source_geometry_and_normals_verified':True,
        'texture_pixels_unchanged':True,'new_collision_shapes':0,'new_scene_objects':0,
        'installed_assets':installed,'all_assets_installed':all(installed.values()),
        'native_standalone_preview_verified':(OUT/'native-thumbnail/asset_thumbnail.png').is_file(),
        'native_town_compile_verified':False}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('source_geometry_and_normals_verified','texture_pixels_unchanged',
        'all_assets_installed','native_standalone_preview_verified')}))


if __name__=='__main__':main()
