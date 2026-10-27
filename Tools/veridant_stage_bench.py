"""Stage only the four existing promenade benches in the active render import."""
import argparse
import importlib.util
import inspect
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import veridant_bench as B
import veridant_map as V
import veridant_parts as P
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/bench-v2'
SOURCE=ROOT/'Sources/Veridant/bench-v2'


def placements():
    # These are the four existing calls in promenade(); no map generation here.
    return [{'c':[-1600.,float(n+150)],'along':[0.,1.],'length':72.,'z0':0.}
            for k,n in enumerate(np.arange(V.PROM[2]+120,V.PROM[3],300.)) if k%2==0]


def remaining_legacy_faces(path,old):
    """Read-only check of original bench triangles in a concurrently edited base."""
    lookup,_=Patch.lookup_polygons(old)
    positions={p for paint,vertices in lookup for p in vertices}
    paints={paint for paint,vertices in lookup};sparse={};index=0;paint=None;count=0
    for line in Path(path).open('rb'):
        if line.startswith(b'v '):
            index+=1;p=Patch.point(line[2:].decode())
            if p in positions:sparse[index]=p
        elif line.startswith(b'usemtl '):paint=line.split()[1]
        elif line.startswith(b'f ') and paint in paints:
            ids=[int(t.split(b'/')[0]) for t in line.split()[1:]]
            if all(i in sparse for i in ids) and (paint,frozenset(sparse[i] for i in ids)) in lookup:count+=1
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',required=True)
    args=parser.parse_args();assert re.fullmatch('stage-[a-z0-9-]+',args.stage)
    stage=OUT/args.stage;assert not stage.exists();stage.mkdir()
    specs=placements();assert len(specs)==4
    source_paths=('Tools/veridant_bench.py','Tools/veridant_stage_bench.py','Tools/map_kit.py',
                  'Tools/riverdale_parts.py','Tools/railhead_stage_extinguisher.py',
                  'Sources/Veridant/bench-v2/previous-bench.py',
                  'Sources/Veridant/bench-v2/imagegen-prompts.json',
                  'Sources/Veridant/bench-v2/teak-albedo-generated-v1.png',
                  'Sources/Veridant/bench-v2/concrete-albedo-generated-v1.png')
    sources={p:Patch.sha(ROOT/p) for p in source_paths}
    snippets={'Tools/veridant_parts.py':[inspect.getsource(P.bench)],
              'Tools/veridant_map.py':['if paint.startswith( "vr_bench_" ) and paint in model.material_overrides:',
                                      'P.bench( m, ( -1600, n + 150 ), ( 0, 1 ), 72 )']}
    document=Path('Assets/models/maps/veridant/veridant_dress.vmdl')
    raw=(ROOT/document).read_text();a,b=span(raw,'_class = "RenderMeshList"');render=raw[a:b]
    already_installed='bench-v2/' in render
    imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',render)
    base=Path('Assets')/next(p for p in imports if p.endswith('dress-base.obj'))
    assert base.as_posix()=='Assets/models/maps/veridant/chair-v2/dress-base.obj'
    protected={p:Patch.sha(ROOT/p) for p in ('Assets/scenes/maps/Veridant/veridant.scene',
                 'Assets/models/maps/veridant/veridant_dress.obj')}
    for path in imports:
        if 'Assets/'+path!=base.as_posix() and 'bench-v2/' not in path:protected['Assets/'+path]=Patch.sha(ROOT/'Assets'/path)
    if already_installed:
        # This pass writes only our own textures and mesh. Unrelated imports
        # may continue updating; they are not inputs to this replacement.
        protected={p:h for p,h in protected.items() if p.endswith('.scene')}
    files={}

    def record(relative):
        relative=Path(relative);original=ROOT/relative;target=stage/relative
        before=Patch.sha(original) if original.exists() else None
        backup=stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,backup)
            assert Patch.sha(backup)==before
        files[relative.as_posix()]={'before':before,'after':Patch.sha(target),
            'source':target.relative_to(ROOT).as_posix(),'backup':backup.relative_to(ROOT).as_posix() if before else None}

    materials=Path('Assets/materials/veridant/bench-v2');B.write_materials(stage/materials)
    for path in sorted((stage/materials).iterdir()):record(path.relative_to(stage))
    spec=importlib.util.spec_from_file_location('legacy_bench',SOURCE/'previous-bench.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    old=K.Model();new=K.Model();details=[]
    for place in specs:
        legacy.bench(old,**place)
        start=new.triangle_count();result=B.build_into(new,**place,collision=False)
        detail={**place,**result,'triangles':new.triangle_count()-start};details.append(detail)
        print(json.dumps(detail),flush=True)
    assert old.triangle_count()==288 and len(old.boxes)==4 and not old.hulls
    assert not new.boxes and not new.hulls and new.triangle_count()<65000
    for paint,rows in new.polygons.items():
        for index,(points,normal) in enumerate(rows):
            assert np.isfinite(points).all() and np.isfinite(normal).all()
            for j in range(1,len(points)-1):
                assert np.linalg.norm(np.cross(points[j]-points[0],points[j+1]-points[0]))>1e-10,(paint,index,j)
            normals=new.polygon_normals.get((paint,index))
            if normals is not None:
                assert np.isfinite(normals).all()
                assert np.max(np.abs(np.linalg.norm(normals,axis=1)-1.))<1e-5
    points=np.vstack([pts for rows in new.polygons.values() for pts,n in rows])
    assert points[:,0].min()>=-1609 and points[:,0].max()<=-1591
    assert points[:,2].min()>=-1e-8 and points[:,2].max()<18.10
    piece=Path('Assets/models/maps/veridant/bench-v2/benches.obj')
    (stage/piece).parent.mkdir(parents=True,exist_ok=True)
    K.write_obj(stage/piece,new,'veridant_benches');record(piece);record(piece.with_suffix('.mtl'))
    if already_installed:
        first=json.loads((OUT/'stage-v1/manifest.json').read_text())
        assert first['base_import']==base.as_posix()
        # Other prop work can legitimately remove unrelated faces from the
        # shared base after our first import. Preserve that current file and
        # verify the old bench faces remain absent instead of reverting it.
        assert remaining_legacy_faces(ROOT/base,old)==0
        result={key:first[key] for key in ('removed_triangles','unrelated_obj_bytes_exact','retained_bytes_sha256')}
        result['retained_bytes_sha256']=Patch.sha(ROOT/base)
        result['initial_bench_removal_manifest']='output/veridant/bench-v2/stage-v1/manifest.json'
        assert imports.count(piece.relative_to('Assets').as_posix())==1
    else:
        lookup,polygons=Patch.lookup_polygons(old)
        result,found=Patch.replace_obj(ROOT/base,stage/'proof/combined.obj',stage/base,lookup,stage/piece)
        Patch.coverage(found,lookup,polygons);assert result['removed_triangles']==288;record(base)
        i,j=span(render,'_class = "RenderMeshFile"');node=render[i:j]
        node=re.sub(r'name = "[^"]+"','name = "veridant_promenade_benches_v2"',node,count=1)
        node=re.sub(r'filename = "[^"]+"',f'filename = "{piece.relative_to("Assets").as_posix()}"',node,count=1)
        end=render.rfind(']');prefix=render[:end].rstrip()
        replacement=prefix+('' if prefix.endswith(',') else ',')+'\n'+node+'\n'+render[end:]
        updated=raw[:a]+replacement+raw[b:]
        remaps=''.join(f'{{ from = "{paint}.vmat" to = "{resource}" }},\n' for paint,resource in B.MATERIALS.items())
        i=updated.index('[',updated.index('remaps ='))+1;updated=updated[:i]+'\n'+remaps+updated[i:]
        marker='_class = "PhysicsShapeList"';assert raw[raw.index(marker):]==updated[updated.index(marker):]
        (stage/document).write_text(updated);record(document)
    manifest={'revision':'veridant-bench-v2','stage':args.stage,'files':files,
        'source_sha256':sources,'required_source_snippets':snippets,'protected_sha256':protected,
        'base_import':base.as_posix(),'benches':details,'placements':specs,'benches_updated':4,
        'new_triangles':new.triangle_count(),'physics_bytes_exact':True,'scene_unchanged':True,
        'collision_envelopes_preserved':True,'own_assets_only':already_installed,**result}
    (stage/'plan-draft.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for group in (sources,protected):
        for p,h in group.items():assert Patch.sha(ROOT/p)==h,('Shared input changed',p)
    for p,parts in snippets.items():assert all(part in (ROOT/p).read_text() for part in parts)
    for p,item in files.items():
        assert Patch.sha(ROOT/item['source'])==item['after']
        assert (Patch.sha(ROOT/p) if (ROOT/p).exists() else None)==item['before'],('Shared target changed',p)
    assert placements()==specs
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    script=(ROOT/'Sources/Veridant/backbar-v1/import.cs.txt').read_text()
    script=script.replace('backbar-v1','bench-v2').replace('veridant_buildings','veridant_dress')
    script=script.replace('lounger-v2/veridant_dress-base.obj','chair-v2/dress-base.obj')
    script=script.replace('SectionsUpdated=3,Bottles=manifest["bottles"].GetValue<int>()',
                          'BenchesUpdated=4,Triangles=manifest["new_triangles"].GetValue<int>()')
    script=script.replace('.backbar-incoming','.bench-incoming')
    script=script.replace('// Publish the shelf-only extraction and three independent back-bar imports.',
                          '// Publish only the four existing promenade benches; preserve all other imports and physics.')
    script=script.replace('var imported=new System.Collections.Generic.List<string>();',
        'if(manifest["own_assets_only"]?.GetValue<bool>() == true)\n{\n'
        '    foreach(var pair in files)\n'
        '        if(!pair.Key.StartsWith("Assets/materials/veridant/bench-v2/",StringComparison.Ordinal)\n'
        '           &&!pair.Key.StartsWith("Assets/models/maps/veridant/bench-v2/",StringComparison.Ordinal))\n'
        '            throw new InvalidOperationException("Refinement must stay inside bench assets.");\n'
        '    var currentModel=System.IO.File.ReadAllText(System.IO.Path.Combine(root,document));\n'
        '    if(!currentModel.Contains("models/maps/veridant/bench-v2/benches.obj",StringComparison.Ordinal))\n'
        '        throw new InvalidOperationException("Bench import is no longer installed.");\n'
        '}\nvar imported=new System.Collections.Generic.List<string>();')
    (SOURCE/'import.cs.txt').write_text(script)
    compile_calls={'calls':[{'name':'asset_compile','arguments':{'path':resource,'full':False}}
                         for resource in B.MATERIALS.values()] +
                         [{'name':'asset_compile','arguments':{'path':document.relative_to('Assets').as_posix(),'full':False}}]}
    (OUT/'compile-request.json').write_text(json.dumps(compile_calls,indent=2)+'\n')
    print(json.dumps({'benches':4,'triangles':new.triangle_count(),'files':len(files),'only_old_bench_faces_removed':288}))


if __name__=='__main__':main()
