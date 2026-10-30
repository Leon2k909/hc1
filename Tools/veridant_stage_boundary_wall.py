"""Scope and stage only Veridant's two closed forecourt gate assemblies."""
import argparse
import inspect
import json
from pathlib import Path
import re
import shutil
import numpy as np

import map_kit as K
import veridant_map as V
import veridant_boundary_wall as G
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/boundary-wall-v1'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',required=True);args=parser.parse_args()
    assert re.fullmatch('stage-[a-z0-9-]+',args.stage)
    stage=OUT/args.stage;assert not stage.exists();stage.mkdir(parents=True)
    document=Path('Assets/models/maps/veridant/veridant_dress.vmdl')
    raw=(ROOT/document).read_text();a,b=span(raw,'_class = "RenderMeshList"')
    render=raw[a:b];installed='gates-v1' in render
    imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',render)
    base=Path('Assets')/next(p for p in imports if p.endswith('dress-base.obj'))
    sources={p:Patch.sha(ROOT/p) for p in ('Tools/veridant_boundary_wall.py',
             'Tools/veridant_stage_boundary_wall.py','Tools/map_kit.py',
             'Tools/riverdale_parts.py','Tools/railhead_stage_extinguisher.py')}
    snippets={'Tools/veridant_map.py':[inspect.getsource(V.forecourt),
        'if paint.startswith( "vr_gate_" ) and paint in model.material_overrides:']}
    protected={p:Patch.sha(ROOT/p) for p in ('Assets/scenes/maps/Veridant/veridant.scene',
        'Assets/models/maps/veridant/veridant_dress.obj',
        'Assets/models/maps/veridant/veridant_buildings.vmdl',
        'Assets/models/maps/veridant/veridant_foliage.vmdl')}
    for p in imports:
        if Path('Assets')/p!=base and 'gates-v1' not in p:
            protected['Assets/'+p]=Patch.sha(ROOT/'Assets'/p)
    files={}
    def record(relative):
        relative=Path(relative);target=ROOT/relative;backup=stage/'before'/relative
        before=Patch.sha(target) if target.exists() else None
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
            assert Patch.sha(backup)==before
        files[relative.as_posix()]={'before':before,'after':Patch.sha(stage/relative),
            'source':(stage/relative).relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}
    material=Path('Assets/materials/veridant/gates-v1');G.write_materials(stage/material)
    for p in sorted((stage/material).iterdir()):record(p.relative_to(stage))
    old=K.Model();new=K.Model();details=[]
    for north in (-300.,500.):
        G.old_into(old,V.PLAY[1],north);details.append(G.build_into(new,V.PLAY[1],north))
    assert not new.boxes and not new.hulls
    assert old.triangle_count()==72
    assert new.triangle_count()<15000
    for paint,rows in new.polygons.items():
        for i,(pts,norm) in enumerate(rows):
            assert np.isfinite(pts).all() and np.isfinite(norm).all()
            if (paint,i) in new.polygon_normals:assert np.isfinite(new.polygon_normals[paint,i]).all()
    piece=Path('Assets/models/maps/veridant/gates-v1/gates.obj')
    (stage/piece).parent.mkdir(parents=True,exist_ok=True)
    K.write_obj(stage/piece,new,'veridant_closed_gates');record(piece);record(piece.with_suffix('.mtl'))
    if installed:
        # Subsequent art refinement touches only this task's own asset files.
        assert render.count('models/maps/veridant/gates-v1/gates.obj')==1
        protected[base.as_posix()]=Patch.sha(ROOT/base)
        protected[document.as_posix()]=Patch.sha(ROOT/document)
        result={'removed_triangles':0,'unrelated_obj_bytes_exact':True,
                'retained_bytes_sha256':Patch.sha(ROOT/base)}
    else:
        lookup,polygons=Patch.lookup_polygons(old)
        result,found=Patch.replace_obj(ROOT/base,stage/'proof/combined.obj',stage/base,lookup,stage/piece)
        Patch.coverage(found,lookup,polygons);assert result['removed_triangles']==72
        record(base)
        i,j=span(render,'_class = "RenderMeshFile"');node=render[i:j]
        node=re.sub(r'name = "[^"]+"','name = "veridant_closed_gates"',node,count=1)
        node=re.sub(r'filename = "[^"]+"',f'filename = "{piece.relative_to("Assets").as_posix()}"',node,count=1)
        end=render.rfind(']');prefix=render[:end].rstrip()
        new_render=prefix+('' if prefix.endswith(',') else ',')+'\n'+node+'\n'+render[end:]
        updated=raw[:a]+new_render+raw[b:]
        remaps=''.join(f'{{ from = "{paint}.vmat" to = "{path}" }},\n' for paint,path in G.MATERIALS.items())
        index=updated.index('[',updated.index('remaps ='))+1
        updated=updated[:index]+'\n'+remaps+updated[index:]
        marker='_class = "PhysicsShapeList"'
        assert raw[raw.index(marker):]==updated[updated.index(marker):]
        (stage/document).write_text(updated);record(document)
    manifest={'revision':'veridant-boundary-wall-v1','stage':args.stage,'files':files,
        'source_sha256':sources,'required_source_snippets':snippets,
        'protected_sha256':protected,'base_import':base.as_posix(),
        'gates':details,'gates_replaced':2,'new_triangles':new.triangle_count(),**result,
        'physics_bytes_exact':True,'scene_unchanged':True,'lights_unchanged':True}
    for group in (sources,protected):
        for p,h in group.items():assert Patch.sha(ROOT/p)==h,('Shared input changed',p)
    for p,parts in snippets.items():assert all(part in (ROOT/p).read_text() for part in parts),p
    for p,item in files.items():
        assert Patch.sha(ROOT/item['source'])==item['after']
        assert (Patch.sha(ROOT/p) if (ROOT/p).exists() else None)==item['before'],p
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'gates':2,'old_triangles':72,'new_triangles':new.triangle_count(),
        'files':len(files),'base_import':base.as_posix(),'physics_bytes_exact':True}))


if __name__=='__main__':main()
