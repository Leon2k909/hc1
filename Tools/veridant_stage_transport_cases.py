"""Replace only authored hard-case triangles in the active render imports."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import veridant_transport_case as C
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/cases-v3'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',required=True)
    args=parser.parse_args();assert args.stage.replace('-','').isalnum()
    stage=OUT/args.stage;assert not stage.exists();stage.mkdir()
    sources={p:Patch.sha(ROOT/p) for p in ('Tools/veridant_transport_case.py','Tools/veridant_case_placements.py',
        'Tools/veridant_stage_transport_cases.py','Tools/veridant_parts.py',
        'Tools/riverdale_parts.py','Tools/map_kit.py','Tools/railhead_stage_extinguisher.py',
        'Sources/Veridant/cases-v3/previous-parts.py','output/veridant/cases-v3/placements.json')}
    rows=json.loads((OUT/'placements.json').read_text());assert len(rows)==82
    spec=importlib.util.spec_from_file_location('previous_case_parts',ROOT/'Sources/Veridant/cases-v3/previous-parts.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    protected={'Assets/scenes/maps/Veridant/veridant.scene':Patch.sha(ROOT/'Assets/scenes/maps/Veridant/veridant.scene')}
    files={};models={};base_paths=[]

    def record(relative):
        relative=Path(relative);source=ROOT/relative;target=stage/relative
        before=Patch.sha(source) if source.exists() else None
        backup=stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
            assert Patch.sha(backup)==before
        files[relative.as_posix()]={'before':before,'after':Patch.sha(target),
            'source':target.relative_to(ROOT).as_posix(),'backup':backup.relative_to(ROOT).as_posix() if before else None}

    material=Path('Assets/materials/veridant/cases-v3');C.write_materials(stage/material)
    for p in sorted((stage/material).iterdir()):record(p.relative_to(stage))
    for name in ('veridant_buildings','veridant_dress'):
        items=[r for r in rows if r['model']==name];old=K.Model()
        for r in items:legacy.hard_case(old,r['centre'],r['size'],r['along'],r['paint'],r['z0'],r['surface'],r['seed'])
        document=Path(f'Assets/models/maps/veridant/{name}.vmdl');raw=(ROOT/document).read_text()
        a,b=span(raw,'_class = "RenderMeshList"');render=raw[a:b]
        imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',render)
        assert 'cases-v3/' not in render
        candidates=[p for p in imports if p.endswith('-base.obj')]
        assert len(candidates)==1,candidates
        base=Path('Assets')/candidates[0];base_paths.append(base.as_posix())
        for p in imports:
            if p!=candidates[0]:protected['Assets/'+p]=Patch.sha(ROOT/'Assets'/p)
        canonical=f'Assets/models/maps/veridant/{name}.obj';protected[canonical]=Patch.sha(ROOT/canonical)
        pieces=[];counts=[];all_boxes=[]
        for chunk,start in enumerate(range(0,len(items),16)):
            new=K.Model()
            for r in items[start:start+16]:
                before=new.triangle_count()
                C.build_into(new,r['centre'],r['size'],r['along'],r['paint'],r['z0'],r['surface'],r['seed'])
                counts.append(new.triangle_count()-before)
            assert new.triangle_count()<65000
            all_boxes.extend(new.boxes)
            for paint,polygons in new.polygons.items():
                for index,(points,normal) in enumerate(polygons):
                    assert np.isfinite(points).all() and np.isfinite(normal).all()
                    if (paint,index) in new.polygon_normals:assert np.isfinite(new.polygon_normals[(paint,index)]).all()
            piece=Path(f'Assets/models/maps/veridant/cases-v3/{name}-{chunk}.obj')
            (stage/piece).parent.mkdir(parents=True,exist_ok=True)
            K.write_obj(stage/piece,new,name+'_transport_cases');record(piece);record(piece.with_suffix('.mtl'))
            pieces.append(piece)
        assert len(old.boxes)==len(all_boxes)==len(items)
        for old_box,new_box in zip(old.boxes,all_boxes):
            assert old_box[3]==new_box[3]
            assert all(np.array_equal(x,y) for x,y in zip(old_box[:3],new_box[:3]))
        lookup,polygons=Patch.lookup_polygons(old)
        result,found=Patch.replace_obj(ROOT/base,stage/'proof'/f'{name}-combined.obj',stage/base,lookup,stage/pieces[0])
        Patch.coverage(found,lookup,polygons)
        assert result['removed_triangles']==old.triangle_count()
        record(base)
        # Reuse the existing import transform and preserve every old node.
        i,j=span(render,'_class = "RenderMeshFile"');template=render[i:j]
        nodes=[]
        for index,piece in enumerate(pieces):
            node=re.sub(r'name = "[^"]+"',f'name = "{name}_transport_cases_{index}"',template,count=1)
            node=re.sub(r'filename = "[^"]+"',f'filename = "{piece.relative_to("Assets").as_posix()}"',node,count=1)
            nodes.append(node)
        end=render.rfind(']');prefix=render[:end].rstrip()
        updated_render=prefix+('' if prefix.endswith(',') else ',')+'\n'+',\n'.join(nodes)+'\n'+render[end:]
        updated=raw[:a]+updated_render+raw[b:]
        remaps=''.join(f'{{ from = "{paint}.vmat" to = "{resource}" }},\n' for paint,resource in C.MATERIALS.items())
        index=updated.index('[',updated.index('remaps ='))+1;updated=updated[:index]+'\n'+remaps+updated[index:]
        x,y=span(raw,'_class = "PhysicsShapeList"');i,j=span(updated,'_class = "PhysicsShapeList"')
        assert raw[x:y]==updated[i:j]
        (stage/document).write_text(updated);record(document)
        models[name]={**result,'cases':len(items),'new_triangles':sum(counts),'triangles_per_case':counts,
                      'physics_bytes_exact':True,'collision_boxes_identical':True,'base_import':base.as_posix(),
                      'replacement_imports':[p.relative_to('Assets').as_posix() for p in pieces],
                      'original_obj_indices_preserved':True}
        print(json.dumps({'model':name,'cases':len(items),'old_triangles':old.triangle_count(),
                          'new_triangles':sum(counts),'physics_preserved':True,'unrelated_bytes_preserved':True}),flush=True)
    # Other tasks edit unrelated map construction concurrently. Recheck the
    # actual case poses instead of locking the entire map source file.
    import veridant_map
    importlib.reload(veridant_map)
    from veridant_case_placements import placements
    assert placements()==rows,'Authored case layout changed.'
    manifest={'revision':'veridant-transport-cases-v3','stage':args.stage,'files':files,'models':models,
              'source_sha256':sources,'protected_sha256':protected,'base_imports':base_paths,
              'cases_replaced':82,'physics_bytes_exact':True,'scene_unchanged':True,
              'unrelated_obj_bytes_exact':True,'original_obj_indices_preserved':True,
              'case_layout_replayed_and_verified':True,
              'layout_source_sha256_at_verification':Patch.sha(ROOT/'Tools/veridant_map.py')}
    (stage/'plan-draft.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for group in (sources,protected):
        for p,h in group.items():assert Patch.sha(ROOT/p)==h,('Shared input changed',p)
    for p,item in files.items():
        assert Patch.sha(ROOT/item['source'])==item['after']
        assert (Patch.sha(ROOT/p) if (ROOT/p).exists() else None)==item['before'],('Shared target changed',p)
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'files':len(files),'cases':82,'stage':args.stage}),flush=True)


if __name__=='__main__':main()
