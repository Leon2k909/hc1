"""Verify the installed crate-only mesh splice and untouched collision/scene."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/crates-v2'
STAGE=OUT/'stage-refined'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def inspect(name, record, triangles):
    rel=f'Assets/models/maps/belltower/{name}'
    original=STAGE/'before'/(rel+'.obj');current=ROOT/(rel+'.obj')
    drop=set(record['removed_face_lines']);prefix=0;counts={'v':0,'vt':0,'vn':0};added={'v':0,'vt':0,'vn':0}
    with original.open('rb') as a,current.open('rb') as b:
        for line in a:
            if line.startswith(b'usemtl '):break
            assert next(b)==line,(name,prefix,'original table changed')
            prefix+=1
            for key in counts:
                if line.startswith(key.encode()+b' '):counts[key]+=1
        for incoming in b:
            if incoming.startswith(b'usemtl '):break
            assert incoming.startswith((b'v ',b'vt ',b'vn '))
            for key in added:
                if incoming.startswith(key.encode()+b' '):added[key]+=1
        assert incoming==line and counts==record['old_vertex_counts']
        assert prefix not in drop
        for index,line in enumerate(a,prefix+1):
            if index in drop:
                assert line.startswith(b'f ')
            else:assert next(b)==line,(name,index,'non-crate mesh byte changed')
        tail=list(b)
    assert sum(x.startswith(b'f ') for x in tail)==triangles
    for line in tail:
        if line.startswith(b'f '):
            for token in line.split()[1:]:
                indices=list(map(int,token.split(b'/')))
                assert all(counts[key]<i<=counts[key]+added[key] for key,i in zip(counts,indices))
    before=(STAGE/'before'/(rel+'.vmdl')).read_bytes()
    after=(ROOT/(rel+'.vmdl')).read_bytes();extra=record['vmdl_inserted_remap'].encode()
    assert after.replace(extra,b'',1)==before
    assert (ROOT/(rel+'.mtl')).read_bytes()==(STAGE/'before'/(rel+'.mtl')).read_bytes()+record['mtl_suffix'].encode()
    return {'non_crate_obj_bytes_preserved':True,'physics_byte_identical':True,'original_vertex_counts':counts,
            'added_vertex_counts':added,'removed_crate_triangles':len(drop),'added_crate_triangles':triangles}


def main():
    manifest=json.loads((STAGE/'manifest.json').read_text())
    installed=json.loads((OUT/'local-install.json').read_text())
    for p,r in manifest['files'].items():assert sha(ROOT/p)==r['after'],p
    assert sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')==installed['scene_sha256']
    models={name:inspect(name,r,manifest['added_triangles_per_half']) for name,r in manifest['models'].items()}
    result={'revision':'crate-joinery-v2','crates':2*manifest['crates_per_half'],'models':models,
            'scene_unchanged':True,'new_colliders':0,'new_scene_objects':0,'texture_pixels_changed':False,
            'native_final_compile_verified':False,'native_final_map_review_verified':False,
            'native_prototype_review':'output/belltower/crates-v2/native-preview-thumbnails/after.png',
            'limitation':'Editor closed before final refined model compilation/map review. Standalone compiler lacked the mounted asset configuration.'}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('crates','scene_unchanged','new_colliders','native_final_compile_verified','native_final_map_review_verified')}))


if __name__=='__main__':main()
