"""Stage only the two dedicated scarecrow imports, preserving the town and scene."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil
import numpy as np
import belltower_map as B
import belltower_detail as D
import belltower_scarecrow as S
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/scarecrow-v2'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--revision',type=int,default=1);args=ap.parse_args()
    stage=OUT/f'stage-r{args.revision}';stage.mkdir(parents=True,exist_ok=False)
    sources=['Tools/belltower_scarecrow.py','Tools/belltower_scarecrow_v2.py',
        'Tools/belltower_stage_scarecrow_v2.py','Tools/belltower_furniture.py','Tools/map_kit.py']
    input_hashes={p:sha(ROOT/p) for p in sources}
    new=K.Model();S.build(new,B.Place((-1590,-1345,B.GARDEN_Z),0));D.configure(new)
    assert not new.boxes and not new.hulls and not new.props
    assert 10000<new.triangle_count()<60000,new.triangle_count()
    triangle_areas=[]
    for paint,polys in new.polygons.items():
        for i,(pts,normal) in enumerate(polys):
            assert np.isfinite(pts).all() and np.isfinite(normal).all()
            for k in range(1,len(pts)-1):
                cross=np.cross(pts[k]-pts[0],pts[k+1]-pts[0]);area=np.linalg.norm(cross)/2
                assert area>1e-10,(paint,pts)
                assert np.dot(cross,normal)>0,(paint,pts,normal)
                triangle_areas.append(float(area))
            normals=new.polygon_normals.get((paint,i))
            if normals is not None:assert np.isfinite(normals).all()
    files={};models={}
    for side in ('west','east'):
        document=f'Assets/models/maps/belltower/belltower_{side}.vmdl'
        relative=f'Assets/models/maps/belltower/pending-garden-v1/{side}/belltower_{side}-scarecrow.obj'
        raw=(ROOT/document).read_text()
        assert raw.count('filename = "'+relative[7:]+'"')==1,'Dedicated scarecrow import changed.'
        expected_aliases=[]
        for paint,path in S.MATERIALS.items():
            alias=f'{{ from = "{paint}.vmat" to = "{path}" }}'
            assert raw.count(alias)==1,alias
            expected_aliases.append(alias)
        piece=new if side=='west' else new.mirrored(B.EAST_PAINTS)
        target=stage/relative;target.parent.mkdir(parents=True)
        K.write_obj(target,piece,'belltower_'+side+'-scarecrow')
        # Export exactly the established material set, including the timber frame.
        old_mtl=(ROOT/relative).with_suffix('.mtl').read_text()
        new_mtl=target.with_suffix('.mtl').read_text()
        assert set(re.findall(r'^newmtl (.+)$',old_mtl,re.M))==set(re.findall(r'^newmtl (.+)$',new_mtl,re.M))
        for path in (target,target.with_suffix('.mtl')):
            rel=path.relative_to(stage).as_posix();original=ROOT/rel
            backup=stage/'before'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,backup)
            assert sha(original)==sha(backup)
            files[rel]={'before':sha(backup),'after':sha(path),'source':path.relative_to(ROOT).as_posix(),
                        'backup':backup.relative_to(ROOT).as_posix()}
        models[document]={'mesh':relative,'required_aliases':expected_aliases,
            'sha256_at_stage':sha(ROOT/document),'document_is_not_an_import_target':True}
    assert all(sha(ROOT/p)==h for p,h in input_hashes.items()),'Source changed while staging.'
    assert all(sha(ROOT/p)==v['before'] for p,v in files.items()),'Shared scarecrow changed while staging.'
    result={'revision':'scarecrow-v2','stage':stage.name,'files':files,'models':models,
        'source_sha256':input_hashes,'required_source_snippets':{'Tools/belltower_map.py':[inspect.getsource(B.Place)]},
        'material_paths':sorted(set(new.material_overrides.values())),
        'triangles_per_instance':new.triangle_count(),'instances':2,'new_scene_objects':0,'new_collision_shapes':0,
        'all_triangles_have_area_and_outward_winding':True,'minimum_triangle_area':min(triangle_areas),
        'scene_sha256_at_stage':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')}
    (stage/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':stage.name})+'\n')
    (OUT/'compile.json').write_text(json.dumps({'calls':[
        {'name':'asset_compile','arguments':{'path':p[7:],'full':False}} for p in models]}))
    (OUT/'info.json').write_text(json.dumps({'calls':[
        {'name':'asset_info','arguments':{'path':p[7:]}} for p in models]}))
    print(json.dumps({'stage':stage.name,'triangles':new.triangle_count(),'files':len(files),
                      'material_set_unchanged':True,'modeldoc_and_scene_targets':0}))


if __name__=='__main__':main()
