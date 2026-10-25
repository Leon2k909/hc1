"""Stage upholstery realism on the existing eight loungers and reusable prop.

Only the dedicated render imports are replaced. Verify every old triangle in
those leaf meshes and leave shared map sources and other imports untouched.
No scene, model-document, material remap, placement or collision edits.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import numpy as np
import map_kit as K
import veridant_lounger as L
from veridant_stage_lounger import placements
import railhead_stage_extinguisher as Patch

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/lounger-v3'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',required=True)
    parser.add_argument('--previous-stage')
    args=parser.parse_args();assert args.stage.replace('-','').isalnum()
    stage=OUT/args.stage;assert not stage.exists();stage.mkdir()
    inputs={p:Patch.sha(ROOT/p) for p in ('Tools/veridant_lounger.py','Tools/veridant_lounger_soft.py',
        'Tools/veridant_stage_soft_loungers.py','Tools/riverdale_parts.py','Tools/map_kit.py',
        'Tools/railhead_stage_extinguisher.py','Sources/Veridant/lounger-v3/previous-lounger.py')}
    previous=None
    if args.previous_stage:
        assert args.previous_stage.replace('-','').isalnum()
        previous_path=OUT/args.previous_stage/'manifest.json'
        previous=json.loads(previous_path.read_text())
        inputs[previous_path.relative_to(ROOT).as_posix()]=Patch.sha(previous_path)
    protected_paths=['Assets/scenes/maps/Veridant/veridant.scene',
        'Assets/models/maps/veridant/veridant_dress.vmdl',
        'Assets/models/maps/veridant/veridant_buildings.vmdl',
        'Assets/models/props/veridant/lounger-v2/lounger.vmdl']
    # Follow current imports so adjacent chair, table and doorway work survives.
    import re
    from belltower_safe_imports import span
    for resource in protected_paths[1:3]:
        raw=(ROOT/resource).read_text();a,b=span(raw,'_class = "RenderMeshList"')
        imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',raw[a:b])
        assert any('lounger-v2/' in p and p.endswith('-replacements.obj') for p in imports)
        protected_paths.extend('Assets/'+p for p in imports if not ('lounger-v2/' in p and p.endswith('-replacements.obj')))
    protected_paths.extend(('Assets/models/maps/veridant/veridant_dress.obj',
                            'Assets/models/maps/veridant/veridant_buildings.obj'))
    protected={p:Patch.sha(ROOT/p) for p in protected_paths}
    spec=importlib.util.spec_from_file_location('previous_lounger',ROOT/'Sources/Veridant/lounger-v3/previous-lounger.py')
    old_source=importlib.util.module_from_spec(spec);spec.loader.exec_module(old_source)
    files={};models={}

    def record(relative):
        relative=Path(relative);target=stage/relative;source=ROOT/relative
        before=Patch.sha(source) if source.exists() else None
        backup=stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
            assert Patch.sha(backup)==before
        files[relative.as_posix()]={'before':before,'after':Patch.sha(target),
            'source':target.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}

    material_dir=Path('Assets/materials/veridant/lounger-v2')
    L.write_materials(stage/material_dir)
    for p in (stage/material_dir).iterdir():record(p.relative_to(stage))
    specs=placements()
    for name,items in (('veridant_dress',specs[:5]),('veridant_buildings',specs[5:])):
        old,new=K.Model(),K.Model();counts=[]
        for centre,facing,z in items:
            old_source.build_into(old,centre,facing,z)
            before=new.triangle_count();L.build_into(new,centre,facing,z)
            counts.append(new.triangle_count()-before)
        assert len(old.boxes)==len(new.boxes)==len(items) and not old.hulls and not new.hulls
        for a,b in zip(old.boxes,new.boxes):
            assert a[3]==b[3]
            assert all(np.array_equal(x,y) for x,y in zip(a[:3],b[:3]))
        assert max(counts)<16000 and new.triangle_count()<80000
        for paint,rows in new.polygons.items():
            for index,(points,normal) in enumerate(rows):
                assert np.isfinite(points).all() and np.isfinite(normal).all()
                if (paint,index) in new.polygon_normals:
                    normals=np.array(new.polygon_normals[(paint,index)])
                    assert np.isfinite(normals).all() and np.allclose(np.linalg.norm(normals,axis=1),1)
        relative=Path(f'Assets/models/maps/veridant/lounger-v2/{name}-replacements.obj')
        target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(target,new,'veridant_loungers_v2');record(relative);record(relative.with_suffix('.mtl'))
        if previous:
            assert Patch.sha(ROOT/relative)==previous['files'][relative.as_posix()]['after']
            old_count=previous['models'][name]['new_triangles']
            result={'removed_triangles':old_count,'previous_published_mesh_hash_verified':True}
        else:
            lookup,faces=Patch.lookup_polygons(old)
            retained=stage/'proof'/f'{name}-retained.obj'
            result,found=Patch.replace_obj(ROOT/relative,stage/'proof'/f'{name}-replacement-proof.obj',retained,lookup,target)
            Patch.coverage(found,lookup,faces)
            assert result['removed_triangles']==old.triangle_count()
            assert not any(line.startswith(b'f ') for line in retained.open('rb'))
            old_count=old.triangle_count()
        # Existing model documents already remap exactly these seven paints.
        assert set(new.polygons)==set(old.polygons)
        models[name]={**result,'placements':len(items),'old_triangles':old_count,
                      'new_triangles':new.triangle_count(),'triangles_per_instance':counts,
                      'collision_boxes_unchanged':True,'original_indices_preserved':True}
        print(json.dumps({name:models[name]}),flush=True)
    reusable=K.Model();L.build_into(reusable,(0,0),(1,0))
    relative=Path('Assets/models/props/veridant/lounger-v2/lounger.obj')
    (stage/relative).parent.mkdir(parents=True,exist_ok=True)
    K.write_obj(stage/relative,reusable,'lounger');record(relative);record(relative.with_suffix('.mtl'))
    manifest={'revision':'veridant-soft-loungers-v3','stage':args.stage,'files':files,'models':models,
              'source_sha256':inputs,'protected_sha256':protected,'placements_replaced':8,
              'physics_unchanged':True,'scene_unchanged':True,'material_remaps_unchanged':True,
              'shared_map_meshes_unchanged':True,'unrelated_obj_records_exact':True,
              'original_obj_indices_preserved':True}
    for group in (inputs,protected):
        for path,digest in group.items():assert Patch.sha(ROOT/path)==digest,('Shared input changed',path)
    for relative,item in files.items():
        assert Patch.sha(ROOT/item['source'])==item['after']
        assert (Patch.sha(ROOT/relative) if (ROOT/relative).exists() else None)==item['before']
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'stage':args.stage,'files':len(files),'placements':8,'models':models}),flush=True)


if __name__=='__main__':main()
