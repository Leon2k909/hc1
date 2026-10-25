"""Extract the three existing shelf sections and publish scoped replacements."""
import argparse
import importlib.util
import inspect
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import veridant_parts as P
import veridant_map as V
import veridant_backbar as B
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/backbar-v1'


def units():
    result=[];previous=P.counter_shelves
    def capture(m,lo,hi,z0,face='+e'):result.append({'lo':list(lo),'hi':list(hi),'z0':z0,'face':face})
    try:
        P.counter_shelves=capture
        for region,low,high,doors in ((V.LOUNGE,-520.,-300.,(V.LOUNGE_WEST_DOOR,)),
                                    (V.CAFE,-120.,120.,V.CAFE_WEST_DOORS)):
            e=region[0]+V.T
            V.shelves_beside_doors(None,(e,low),(e+12,high),V.L0,doors)
    finally:P.counter_shelves=previous
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',required=True)
    args=parser.parse_args();assert args.stage.replace('-','').isalnum()
    stage=OUT/args.stage;assert not stage.exists();stage.mkdir()
    source_paths=('Tools/veridant_backbar.py','Tools/veridant_stage_backbar.py','Tools/map_kit.py',
        'Tools/riverdale_parts.py','Tools/railhead_stage_extinguisher.py','Sources/Veridant/backbar-v1/previous-shelves.py')
    sources={p:Patch.sha(ROOT/p) for p in source_paths}
    snippets={'Tools/veridant_parts.py':[inspect.getsource(P.counter_shelves)],
              'Tools/veridant_map.py':['if paint.startswith( ( "vr_backbar_", "vr_transport_" ) ) and paint in model.material_overrides:']}
    specs=units();assert len(specs)==3
    legacy_spec=importlib.util.spec_from_file_location('previous_shelves',ROOT/'Sources/Veridant/backbar-v1/previous-shelves.py')
    legacy=importlib.util.module_from_spec(legacy_spec);legacy_spec.loader.exec_module(legacy)
    document=Path('Assets/models/maps/veridant/veridant_buildings.vmdl');raw=(ROOT/document).read_text()
    a,b=span(raw,'_class = "RenderMeshList"');render=raw[a:b]
    imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',render)
    assert 'backbar-v1/' not in render
    base=Path('Assets')/next(p for p in imports if p.endswith('-base.obj'))
    protected={p:Patch.sha(ROOT/p) for p in ('Assets/scenes/maps/Veridant/veridant.scene',
                'Assets/models/maps/veridant/veridant_buildings.obj')}
    for p in imports:
        if 'Assets/'+p!=base.as_posix():protected['Assets/'+p]=Patch.sha(ROOT/'Assets'/p)
    files={};details=[];old=K.Model();pieces=[]

    def record(relative):
        relative=Path(relative);source=ROOT/relative;target=stage/relative
        before=Patch.sha(source) if source.exists() else None;backup=stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
            assert Patch.sha(backup)==before
        files[relative.as_posix()]={'before':before,'after':Patch.sha(target),
            'source':target.relative_to(ROOT).as_posix(),'backup':backup.relative_to(ROOT).as_posix() if before else None}

    material=Path('Assets/materials/veridant/backbar-v1');B.write_materials(stage/material)
    for p in sorted((stage/material).iterdir()):record(p.relative_to(stage))
    for index,spec in enumerate(specs):
        legacy.counter_shelves(old,**spec);new=K.Model();detail=B.build_into(new,**spec)
        assert not new.boxes and not new.hulls
        for paint,polygons in new.polygons.items():
            for polygon_index,(points,normal) in enumerate(polygons):
                assert np.isfinite(points).all() and np.isfinite(normal).all()
                if (paint,polygon_index) in new.polygon_normals:assert np.isfinite(new.polygon_normals[(paint,polygon_index)]).all()
        points=np.vstack([pts for rows in new.polygons.values() for pts,n in rows])
        assert points[:,1].min()>=spec['lo'][1]-1e-6 and points[:,1].max()<=spec['hi'][1]+1e-6
        assert new.triangle_count()<65000
        piece=Path(f'Assets/models/maps/veridant/backbar-v1/shelves-{index}.obj')
        (stage/piece).parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(stage/piece,new,'veridant_backbar');record(piece);record(piece.with_suffix('.mtl'))
        pieces.append(piece);details.append({**spec,**detail,'triangles':new.triangle_count()})
        print(json.dumps(details[-1]),flush=True)
    assert not old.boxes and not old.hulls and old.triangle_count()==1926
    lookup,polygons=Patch.lookup_polygons(old)
    result,found=Patch.replace_obj(ROOT/base,stage/'proof/combined.obj',stage/base,lookup,stage/pieces[0])
    Patch.coverage(found,lookup,polygons);assert result['removed_triangles']==1926
    record(base)
    i,j=span(render,'_class = "RenderMeshFile"');template=render[i:j];nodes=[]
    for index,piece in enumerate(pieces):
        node=re.sub(r'name = "[^"]+"',f'name = "veridant_backbar_{index}"',template,count=1)
        node=re.sub(r'filename = "[^"]+"',f'filename = "{piece.relative_to("Assets").as_posix()}"',node,count=1)
        nodes.append(node)
    end=render.rfind(']');prefix=render[:end].rstrip()
    new_render=prefix+('' if prefix.endswith(',') else ',')+'\n'+',\n'.join(nodes)+'\n'+render[end:]
    updated=raw[:a]+new_render+raw[b:]
    remaps=''.join(f'{{ from = "{paint}.vmat" to = "{resource}" }},\n' for paint,resource in B.MATERIALS.items())
    i=updated.index('[',updated.index('remaps ='))+1;updated=updated[:i]+'\n'+remaps+updated[i:]
    i=raw.index('_class = "PhysicsShapeList"');j=updated.index('_class = "PhysicsShapeList"')
    assert raw[i:]==updated[j:]
    (stage/document).write_text(updated);record(document)
    assert units()==specs
    manifest={'revision':'veridant-backbar-v1','stage':args.stage,'files':files,'source_sha256':sources,
        'required_source_snippets':snippets,'protected_sha256':protected,'base_import':base.as_posix(),
        'sections':details,'sections_replaced':3,'bottles':sum(d['bottles'] for d in details),
        'new_triangles':sum(d['triangles'] for d in details),**result,
        'physics_bytes_exact':True,'scene_unchanged':True,'doorway_spans_preserved':True,
        'source_configure_preserves_backbar_and_transport_materials':True}
    (stage/'plan-draft.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for group in (sources,protected):
        for p,h in group.items():assert Patch.sha(ROOT/p)==h,('Shared input changed',p)
    for p,item in files.items():
        assert Patch.sha(ROOT/item['source'])==item['after']
        assert (Patch.sha(ROOT/p) if (ROOT/p).exists() else None)==item['before'],('Shared target changed',p)
    for p,parts in snippets.items():
        text=(ROOT/p).read_text()
        assert all(part in text for part in parts)
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'sections':3,'bottles':manifest['bottles'],'triangles':manifest['new_triangles'],
                      'files':len(files),'unrelated_bytes_preserved':True}),flush=True)


if __name__=='__main__':main()
