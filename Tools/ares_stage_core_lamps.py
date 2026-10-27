"""Replace exactly the upper core ring's 24 floating lamp boxes; preserve other bytes."""
import argparse
import inspect
import json
from pathlib import Path
import shutil
import numpy as np
import ares_map as A
import ares_core_lamps as L
import map_kit as K
from railhead_stage_extinguisher import sha,lookup_polygons,replace_obj,coverage

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ares/core-lamp-mounts-v1'


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stage',required=True);args=ap.parse_args()
    assert args.stage.replace('-','').isalnum()
    stage=OUT/args.stage;stage.mkdir(exist_ok=False,parents=True)
    source='Assets/models/maps/ares/ares_reactor.obj';before=sha(ROOT/source)
    protected_paths=['Assets/models/maps/ares/ares_reactor.vmdl','Assets/models/maps/ares/ares_reactor.mtl']
    protected_paths += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/ares').glob('ares_reactor_hulls_*.obj')]
    protected_paths += [f'Assets/materials/ares/{m}.vmat' for m in ('ar_steel','ar_gunmetal','ar_led_warm')]
    protected={p:sha(ROOT/p) for p in protected_paths}
    sources={p:sha(ROOT/p) for p in ('Tools/ares_core_lamps.py','Tools/ares_stage_core_lamps.py','Tools/map_kit.py','Tools/riverdale_parts.py')}
    hook='    from ares_core_lamps import flared_ring_lamps\n    flared_ring_lamps( m )'
    assert hook in (ROOT/'Tools/ares_map.py').read_text()
    snippets={'Tools/ares_map.py':[hook,inspect.getsource(A.reactor)]}
    old=K.Model();L.legacy_lamps(old);new=K.Model();reports=L.flared_ring_lamps(new);A.configure(new)
    assert old.triangle_count()==288 and not old.boxes and not old.hulls
    assert not new.boxes and not new.hulls and new.triangle_count()<15000
    for paint,rows in new.polygons.items():
        for i,(points,normal) in enumerate(rows):
            assert np.isfinite(points).all() and np.isfinite(normal).all()
            ns=new.polygon_normals.get((paint,i))
            if ns is not None:assert np.isfinite(ns).all()
    piece=stage/'proof/new-lamps.obj';piece.parent.mkdir()
    K.write_obj(piece,new,'ares_reactor')
    lookup,faces=lookup_polygons(old)
    target=stage/source
    result,found=replace_obj(ROOT/source,target,stage/'proof/retained.obj',lookup,piece)
    coverage(found,lookup,faces);assert result['removed_triangles']==288
    backup=stage/'before'/source;backup.parent.mkdir(parents=True);shutil.copy2(ROOT/source,backup)
    assert sha(backup)==before and sha(ROOT/source)==before
    for group in (protected,sources):
        for p,h in group.items():assert sha(ROOT/p)==h,('Input changed',p)
    manifest={'revision':'ares-core-lamp-mounts-v1','stage':args.stage,'fixtures':24,
              'files':{source:{'before':before,'after':sha(target),'source':target.relative_to(ROOT).as_posix(),
                               'backup':backup.relative_to(ROOT).as_posix()}},
              'protected_sha256':protected,'source_sha256':sources,'required_source_snippets':snippets,
              'new_triangles':new.triangle_count(),'mounts':reports,**result,
              'scene_sha256_at_staging':sha(ROOT/'Assets/scenes/maps/Ares/ares.scene'),
              'scene_edited':False,'collision_changed':False,'materials_changed':False}
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'fixtures':24,'removed_triangles':288,'new_triangles':new.triangle_count(),
                      'unrelated_obj_bytes_exact':True,'physics_and_materials_unchanged':True}))


if __name__=='__main__':main()
