"""Isolate and replace only the pergola's six double-sided flower panels."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import veridant_parts as P
import veridant_bougainvillea as B
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/pergola-flowers-v2'
FOLDER=Path('Assets/models/maps/veridant/pergola-flowers-v2')
VM=Path('Assets/models/maps/veridant/veridant_foliage.vmdl')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',required=True);parser.add_argument('--previous-stage')
    args=parser.parse_args();assert args.stage.replace('-','').isalnum()
    stage=OUT/args.stage;assert not stage.exists();stage.mkdir()
    inputs={p:Patch.sha(ROOT/p) for p in ('Tools/veridant_bougainvillea.py','Tools/veridant_stage_flowers.py',
        'Tools/map_kit.py','Tools/riverdale_parts.py','Tools/railhead_stage_extinguisher.py',
        'Sources/Veridant/pergola-flowers-v2/previous-bougainvillea.py')}
    protected_paths=['Assets/scenes/maps/Veridant/veridant.scene',
        'Assets/models/maps/veridant/veridant_foliage.obj','Assets/models/maps/veridant/veridant_foliage.mtl',
        'Assets/materials/veridant/vr_foliage.vmat','Assets/materials/veridant/vr_foliage_color.png']
    previous=None
    if args.previous_stage:
        assert args.previous_stage.replace('-','').isalnum()
        previous=json.loads((OUT/args.previous_stage/'manifest.json').read_text())
        protected_paths.extend([VM.as_posix(),(FOLDER/'foliage-base.obj').as_posix(),(FOLDER/'veridant_foliage.mtl').as_posix()])
    protected={p:Patch.sha(ROOT/p) for p in protected_paths}
    files={}

    def record(relative):
        relative=Path(relative);target=stage/relative;original=ROOT/relative
        before=Patch.sha(original) if original.exists() else None
        backup=stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,backup)
            assert Patch.sha(backup)==before
        files[relative.as_posix()]={'before':before,'after':Patch.sha(target),
            'source':target.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}

    new=K.Model();B.build_into(new,(-460,-1176,120),(1,0,0),200,60,seed=5)
    assert not new.boxes and not new.hulls and new.triangle_count()<70000
    for paint,rows in new.polygons.items():
        for index,(points,normal) in enumerate(rows):
            assert np.isfinite(points).all() and np.isfinite(normal).all()
            if (paint,index) in new.polygon_normals:assert np.isfinite(new.polygon_normals[(paint,index)]).all()
    leaf=FOLDER/'flowers.obj';(stage/leaf).parent.mkdir(parents=True,exist_ok=True)
    K.write_obj(stage/leaf,new,'veridant_flowers');record(leaf);record(leaf.with_suffix('.mtl'))
    material_folder=Path('Assets/materials/veridant/pergola-flowers-v2')
    B.write_materials(stage/material_folder)
    for p in (stage/material_folder).iterdir():record(p.relative_to(stage))
    proof={}
    if previous:
        assert Patch.sha(ROOT/leaf)==previous['files'][leaf.as_posix()]['after']
        proof=previous['retained_geometry_proof']
    else:
        legacy={**vars(P)}
        path=ROOT/'Sources/Veridant/pergola-flowers-v2/previous-bougainvillea.py'
        exec(compile(path.read_text(),str(path),'exec'),legacy)
        old=K.Model();legacy['bougainvillea'](old,(-460,-1176,120),(1,0,0),200,60,seed=5)
        assert old.triangle_count()==24 and not old.boxes and not old.hulls
        # Count both opposing faces explicitly; a shared triangle key appears
        # twice because each card is visible from both sides.
        wanted=Counter()
        for paint,rows in old.polygons.items():
            for points,normal in rows:
                vertices=[Patch.point(K.obj_vector(K.to_world(p))) for p in points]
                for j in range(1,len(vertices)-1):
                    tri=(vertices[0],vertices[j],vertices[j+1])
                    wanted[(paint.encode(),frozenset(tri))]+=1
        assert sum(wanted.values())==24
        source=ROOT/'Assets/models/maps/veridant/veridant_foliage.obj'
        base=FOLDER/'foliage-base.obj';merged=stage/'proof/merged.obj'
        result,found=Patch.replace_obj(source,merged,stage/base,wanted,stage/leaf)
        assert found==wanted
        assert result['removed_triangles']==24
        record(base)
        mtl=FOLDER/'veridant_foliage.mtl';shutil.copyfile(source.with_suffix('.mtl'),stage/mtl);record(mtl)
        raw=(ROOT/VM).read_text();a,b=span(raw,'_class = "RenderMeshList"');render=raw[a:b]
        original='models/maps/veridant/veridant_foliage.obj'
        assert render.count('filename = "'+original+'"')==1
        x,y=span(render,'_class = "RenderMeshFile"');template=render[x:y]
        render=render.replace('filename = "'+original+'"','filename = "'+base.relative_to('Assets').as_posix()+'"',1)
        node=re.sub(r'name = "[^"]+"','name = "pergola_flowers_v2"',template,count=1)
        node=re.sub(r'filename = "[^"]+"','filename = "'+leaf.relative_to('Assets').as_posix()+'"',node,count=1)
        at=render.rfind(']');prefix=render[:at].rstrip()
        render=prefix+('' if prefix.endswith(',') else ',')+'\n'+node+'\n'+render[at:]
        updated=raw[:a]+render+raw[b:]
        remaps=''.join('{ from = "'+p+'.vmat" to = "'+r+'" },\n' for p,r in B.MATERIALS.items())
        at=updated.index('[',updated.index('remaps ='))+1
        updated=updated[:at]+'\n'+remaps+updated[at:]
        assert ',,' not in updated
        assert 'PhysicsShape' not in raw and 'PhysicsShape' not in updated
        (stage/VM).write_text(updated);record(VM)
        proof={**result,'original_vertex_indices_preserved':True,'panels_removed':6,'physics_unchanged':True}
    for group in (inputs,protected):
        for relative,digest in group.items():assert Patch.sha(ROOT/relative)==digest,relative
    for relative,item in files.items():
        assert Patch.sha(ROOT/item['source'])==item['after']
        assert (Patch.sha(ROOT/relative) if (ROOT/relative).exists() else None)==item['before']
    manifest={'revision':'veridant-pergola-flowers-v2','stage':args.stage,'files':files,
        'source_sha256':inputs,'protected_sha256':protected,'retained_geometry_proof':proof,
        'new_triangles':new.triangle_count(),'planting':new.bougainvillea_stats,
        'scene_unchanged':True,'collision_unchanged':True,'old_atlas_unchanged':True}
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({k:manifest[k] for k in ('stage','new_triangles','planting','retained_geometry_proof')}))


if __name__=='__main__':main()
