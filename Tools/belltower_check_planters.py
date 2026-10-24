"""Inspect installed planter mesh bytes without changing assets or the editor.

The final appearance gate is deliberately separate: v1 screenshots do not prove
the later v2 root correction. Native v2 capture evidence is consumed if present.
"""
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
import belltower_check_planter_scene as scene_revision

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/belltower/planter-v2/stage'
BASE=ROOT/'output/belltower/planter-v1/stage/before'
OUT=STAGE.parent


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def inspect_mesh(name,record,triangles):
    relative=f'Assets/models/maps/belltower/{name}'
    baseline=BASE/(relative+'.obj');installed=ROOT/(relative+'.obj')
    drop=set(record['removed_face_lines']);assert len(drop)==36
    extra=[];prefix_count=0;old_counts={'v':0,'vt':0,'vn':0}
    # Stream the large unchanged town, keeping only the small appended tables.
    with baseline.open('rb') as original,installed.open('rb') as current:
        for index,line in enumerate(original):
            if line.startswith(b'usemtl '):break
            assert next(current)==line,(name,index,'original vertex/UV/normal bytes changed')
            prefix_count+=1
            for key in old_counts:
                if line.startswith(key.encode()+b' '):old_counts[key]+=1
        for incoming in current:
            if incoming.startswith(b'usemtl '):break
            assert incoming.startswith((b'v ',b'vt ',b'vn '))
            extra.append(incoming)
        assert incoming==line
        for index,line in enumerate(itertools.chain((line,),original),prefix_count):
            if index in drop:
                assert line.startswith(b'f ')
                continue
            # The first material line was already consumed above.
            if index==prefix_count:continue
            assert next(current)==line,(name,index,'non-planter face bytes changed')
        tail=list(current)
    assert old_counts==record['old_vertex_counts']
    assert sum(line.startswith(b'f ') for line in tail)==triangles
    vertices=np.array([list(map(float,line.split()[1:])) for line in extra if line.startswith(b'v ')])
    used={};paint=None
    for line in tail:
        if line.startswith(b'usemtl '):paint=line[7:].strip().decode()
        elif line.startswith(b'f '):
            used.setdefault(paint,set()).update(int(t.split(b'/')[0])-old_counts['v']-1 for t in line.split()[1:])
    assert set(used)=={'planter_cut_stone','planter_compost','furniture_wood_dark'}
    # OBJ -> plan: east=-x, north=z, height=y.
    plan=np.column_stack((-vertices[:,0],vertices[:,2],vertices[:,1]))
    sign=-1 if name.endswith('west') else 1
    centres=np.array(((sign*1780,330),(sign*1180,330),(sign*870,-80)))
    nearest=np.argmin(np.linalg.norm(plan[:,:2,None]-centres.T[None,:,:],axis=1),axis=1)
    stone_indices=np.array(sorted(used['planter_cut_stone']))
    soil_indices=np.array(sorted(used['planter_compost']))
    root_indices=np.array(sorted(used['furniture_wood_dark']))
    bounds=[]
    for i,centre in enumerate(centres):
        stone=plan[stone_indices[nearest[stone_indices]==i]]
        soil=plan[soil_indices[nearest[soil_indices]==i]]
        root=plan[root_indices[nearest[root_indices]==i]]
        assert np.max(np.abs(stone[:,:2]-centre))<=20.002
        assert stone[:,2].min()>=-.002 and stone[:,2].max()<=28.002
        assert len(np.unique(np.round(stone[stone[:,2]>25.4,2],3)))>=12,'Coping lacks physical edge variation'
        visible_soil=soil[soil[:,2]>22]
        assert np.ptp(visible_soil[:,2])>.8 and visible_soil[:,2].max()<25.6
        assert root[:,2].max()<30.4 and root[:,2].min()>22
        bounds.append({'centre':centre.tolist(),'stone_bounds':[stone.min(axis=0).tolist(),stone.max(axis=0).tolist()],
                       'visible_soil_height_range':[float(visible_soil[:,2].min()),float(visible_soil[:,2].max())],
                       'root_height_range':[float(root[:,2].min()),float(root[:,2].max())]})
    original=(BASE/(relative+'.vmdl')).read_bytes();updated=(ROOT/(relative+'.vmdl')).read_bytes()
    added=record['vmdl_inserted_remaps'].encode()
    assert updated.count(added)==1 and updated.replace(added,b'',1)==original
    old_mtl=(BASE/(relative+'.mtl')).read_bytes();new_mtl=(ROOT/(relative+'.mtl')).read_bytes()
    suffix=b'newmtl planter_cut_stone\nKd 1 1 1\nd 1\nnewmtl planter_compost\nKd 1 1 1\nd 1\n'
    assert new_mtl==old_mtl+suffix
    return {'non_planter_mesh_bytes_preserved':True,'gate_and_firewood_geometry_preserved':True,
            'physics_bytes_preserved':True,'removed_triangles':36,'added_triangles':triangles,'planters':bounds}


def main():
    manifest=json.loads((STAGE/'manifest.json').read_text())
    for path,record in manifest['files'].items():assert sha(ROOT/path)==record['after'],path
    for group in ('source_sha256','texture_sha256'):
        for path,expected in manifest[group].items():assert sha(ROOT/path)==expected,path
    scene_hash=sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')
    revision=None
    if scene_hash!=manifest['scene_sha256']:
        revision=scene_revision.verify(manifest['scene_sha256'])
    models={name:inspect_mesh(name,record,manifest['added_triangles_per_half']) for name,record in manifest['models'].items()}
    report={'revision':'worn-planters-v2','installed_asset_hashes_verified':9,'texture_pixels_unchanged':True,
            'scene_and_foliage_placements_unchanged':revision is None,
            'scene_revision':revision,'models':models,'new_game_objects':0,'new_colliders':0,
            'native_visual_review_verified':False,'native_v2_capture_restoration_verified':False,
            'native_review_scope':'Source and geometry checks only; final v2 captures are required.'}
    captures=ROOT/'output/belltower/quality'/('planter-v2-saved' if revision else 'planter-v2-after')
    required=('context','close','low-angle','west-context')
    if all((captures/(name+'-camera.json')).is_file() for name in required):
        for name in required:
            data=json.loads((captures/(name+'-camera.json')).read_text())
            assert all(data['Restoration'].values()) and data['Capture']['ViewportSettledMilliseconds']==5000
            assert data['Capture']['SourceSceneSha256']==scene_hash
            assert (captures/(name+'.png')).is_file()
        report['native_v2_capture_restoration_verified']=True
        report['native_review_scope']='Capture restoration checked. Human/model image review is recorded separately.'
        review_path=OUT/'native-visual-review.json'
        if review_path.is_file():
            review=json.loads(review_path.read_text())
            assert review['decision']=='accept' and review['scene_sha256']==scene_hash
            assert {Path(r['image']).stem for r in review['images']}==set(required)
            for row in review['images']:
                assert sha(ROOT/row['image'])==row['sha256'] and row['restoration_verified']
            report['native_visual_review_verified']=True
            report['native_review_scope']='Four native images reviewed separately; scene revision and capture restoration verified. Runtime performance unmeasured.'
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'revision':report['revision'],'verified_planters':6,'added_triangles_per_half':manifest['added_triangles_per_half'],
                      'source_and_geometry_verified':True,'native_v2_capture_restoration_verified':report['native_v2_capture_restoration_verified']}))


if __name__=='__main__':main()
