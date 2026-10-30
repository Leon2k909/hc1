"""Stage the case-only render imports; preserve every other import and physics byte."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import veridant_case_detail as C
from veridant_case_placements import placements
from belltower_safe_imports import span, sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/cases-v4'


def inspect_geometry(rows):
    reports=[]
    for size in sorted({tuple(r['size']) for r in rows}):
        model=K.Model();C.build_into(model,(0,0),size)
        pts=np.vstack([p for group in model.polygons.values() for p,n in group])
        assert np.isfinite(pts).all() and len(model.boxes)==1
        assert np.all(pts[:,:2].max(0)<=np.array(size[:2])/2+.6)
        assert np.all(pts[:,:2].min(0)>=-np.array(size[:2])/2-.6)
        assert pts[:,2].min()>=-.001 and pts[:,2].max()<=size[2]+.001
        for normals in model.polygon_normals.values():
            assert np.isfinite(normals).all()
            assert np.allclose(np.linalg.norm(normals,axis=1),1,atol=1e-6)
        reports.append({'size':size,'triangles':model.triangle_count(),
                        'bounds':[pts.min(0).tolist(),pts.max(0).tolist()]})
    return reports


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage');parser.add_argument('--preview',action='store_true')
    parser.add_argument('--reuse-stage',help='Reuse owned generated meshes while rebasing model documents on current shared files.')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    rows=placements();assert len(rows)==82
    baseline=json.loads((ROOT/'output/veridant/cases-v3/placements.json').read_text())
    assert rows==baseline,'Case placement changed; inspect before rebuilding.'
    checks=inspect_geometry(rows)
    chunk_size=min(8,64000//max(r['triangles'] for r in checks))
    print(json.dumps({'sizes_checked':len(checks),'triangles_per_case':checks[0]['triangles'],
                      'max_triangles':max(r['triangles'] for r in checks)}),flush=True)
    if args.preview:
        folder=OUT/'preview';folder.mkdir(exist_ok=True)
        C.write_materials(folder/'materials');m=K.Model();C.build_into(m,(0,0),(46,28,24),paint='vr_case_olive')
        K.write_obj(folder/'case.obj',m,'case')
        (folder/'geometry-check.json').write_text(json.dumps(checks,indent=2)+'\n')
        print(json.dumps({'preview':str(folder),'geometry_checks':checks}),flush=True)
        return
    assert args.stage and re.fullmatch(r'stage-[a-z0-9-]+',args.stage)
    stage=OUT/args.stage;assert not stage.exists();stage.mkdir()
    source_paths=('Tools/veridant_case_detail.py','Tools/veridant_stage_case_detail.py',
                  'Tools/veridant_transport_case.py','Tools/veridant_case_placements.py',
                  'Tools/riverdale_parts.py','Tools/map_kit.py',
                  'Sources/Veridant/cases-v4/previous-generator.py')
    sources={p:sha(ROOT/p) for p in source_paths}
    protected={'Assets/scenes/maps/Veridant/veridant.scene':sha(ROOT/'Assets/scenes/maps/Veridant/veridant.scene')}
    spec=importlib.util.spec_from_file_location('previous_case_generator',ROOT/'Sources/Veridant/cases-v4/previous-generator.py')
    previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
    reuse=None
    if args.reuse_stage:
        assert re.fullmatch(r'stage-[a-z0-9-]+',args.reuse_stage)
        reuse=OUT/args.reuse_stage
        assert reuse.exists() and reuse!=stage
        # A shared source change invalidated the prior publication, not these
        # owned meshes. Require the generator to predate every reused output,
        # recheck topology/materials/counts, and hash each exact reused byte.
        assert not (reuse/'manifest.json').exists()
    reused={}
    files={};models={}
    def record(path):
        path=Path(path);target=ROOT/path;staged=stage/path
        before=sha(target) if target.exists() else None
        backup=stage/'before'/path
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
            assert sha(backup)==before
        files[path.as_posix()]={'before':before,'after':sha(staged),
            'source':staged.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}
    material=Path('Assets/materials/veridant/cases-v4');C.write_materials(stage/material)
    for p in sorted((stage/material).iterdir()):record(p.relative_to(stage))
    for name in ('veridant_buildings','veridant_dress'):
        document=Path(f'Assets/models/maps/veridant/{name}.vmdl')
        raw=(ROOT/document).read_text();a,b=span(raw,'_class = "RenderMeshList"');render=raw[a:b]
        imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',render)
        old_imports=[p for p in imports if p.startswith('models/maps/veridant/cases-v3/') or p.startswith('models/maps/veridant/cases-v4/')]
        if any('/cases-v4/' in p for p in old_imports):
            assert all('/cases-v4/' in p for p in old_imports) and 2<=len(old_imports)<=20,old_imports
        else:assert len(old_imports)==(2 if name.endswith('buildings') else 4),old_imports
        for p in imports:
            if '/cases-v4/' not in p:protected['Assets/'+p]=sha(ROOT/'Assets'/p)
        canonical=f'Assets/models/maps/veridant/{name}.obj';protected[canonical]=sha(ROOT/canonical)
        items=[r for r in rows if r['model']==name];counts=[];pieces=[];boxes=[];old_boxes=[]
        # Small dedicated imports avoid the model compiler's large-mesh limit.
        for index,start in enumerate(range(0,len(items),chunk_size)):
            piece=Path(f'Assets/models/maps/veridant/cases-v4/{name}-{index}.obj')
            if reuse:
                source=reuse/piece;mtl=source.with_suffix('.mtl')
                assert source.stat().st_mtime_ns>(ROOT/'Tools/veridant_case_detail.py').stat().st_mtime_ns
                text=source.read_text();faces=[line for line in text.splitlines() if line.startswith('f ')]
                paints={line.split()[1] for line in text.splitlines() if line.startswith('usemtl ')}
                assert paints<=set(C.MATERIALS) and all(len(line.split())==4 for line in faces)
                expected={tuple(r['size']):r['triangles'] for r in checks}
                chunk_counts=[expected[tuple(r['size'])] for r in items[start:start+chunk_size]]
                assert len(faces)==sum(chunk_counts)<65000
                (stage/piece).parent.mkdir(parents=True,exist_ok=True)
                for p in (piece,piece.with_suffix('.mtl')):
                    source=reuse/p;h=sha(source);shutil.copy2(source,stage/p)
                    assert sha(source)==sha(stage/p)==h
                    reused[p.as_posix()]={'source':source.relative_to(ROOT).as_posix(),'sha256':h}
                    record(p)
                counts.extend(chunk_counts);pieces.append(piece)
                continue
            m=K.Model()
            for r in items[start:start+chunk_size]:
                # The previous generator's unchanged collision formula, without
                # rebuilding its discarded render geometry for every instance.
                old=K.Model();f=np.array((*r['along'],0.));f/=np.linalg.norm(f);s=np.cross((0,0,1),f)
                size=np.array(r['size']);base=np.array((*r['centre'],r['z0']))
                old.oriented_box(base+np.array((0,0,size[2]/2)),(f,s,np.array((0,0,1.))),size,{},r['surface'])
                old_boxes.extend(old.boxes)
                count=m.triangle_count()
                C.build_into(m,r['centre'],r['size'],r['along'],r['paint'],r['z0'],r['surface'],r['seed'])
                counts.append(m.triangle_count()-count)
            assert m.triangle_count()<65000,m.triangle_count()
            boxes.extend(m.boxes)
            (stage/piece).parent.mkdir(parents=True,exist_ok=True)
            K.write_obj(stage/piece,m,name+'_cases_v4');record(piece);record(piece.with_suffix('.mtl'));pieces.append(piece)
        assert (len(boxes)==len(old_boxes)==len(items)) if not reuse else (len(boxes)==len(old_boxes)==0)
        for old,new in zip(old_boxes,boxes):
            assert old[3]==new[3]
            assert all(np.array_equal(x,y) for x,y in zip(old[:3],new[:3]))
        # Replace only the former dedicated case nodes. Keep all other nodes,
        # transforms, and the complete model physics suffix byte-for-byte.
        ranges=[];template=None
        for old_path in old_imports:
            i,j=span(render,f'filename = "{old_path}"');ranges.append((i,j))
            if template is None:template=render[i:j]
        updated_render=render
        for i,j in sorted(ranges,reverse=True):
            end=j
            while end<len(updated_render) and updated_render[end].isspace():end+=1
            if end<len(updated_render) and updated_render[end]==',':end+=1
            updated_render=updated_render[:i]+updated_render[end:]
        nodes=[]
        for index,piece in enumerate(pieces):
            node=re.sub(r'name = "[^"]+"',f'name = "{name}_cases_v4_{index}"',template,count=1)
            node=re.sub(r'filename = "[^"]+"',f'filename = "{piece.relative_to("Assets").as_posix()}"',node,count=1)
            nodes.append(node)
        end=updated_render.rfind(']');prefix=updated_render[:end].rstrip()
        updated_render=prefix+('' if prefix.endswith(',') else ',')+'\n'+',\n'.join(nodes)+'\n'+updated_render[end:]
        updated=raw[:a]+updated_render+raw[b:]
        for paint,path in C.MATERIALS.items():
            pattern=r'\{\s*from = "'+re.escape(paint)+r'\.vmat"\s+to = "[^"]+"\s*\}'
            replacement=f'{{ from = "{paint}.vmat" to = "{path}" }}'
            if re.search(pattern,updated):updated,n=re.subn(pattern,replacement,updated);assert n==1
            else:
                pos=updated.index('[',updated.index('remaps ='))+1
                updated=updated[:pos]+'\n'+replacement+',\n'+updated[pos:]
        marker='_class = "PhysicsShapeList"'
        assert raw[raw.index(marker):]==updated[updated.index(marker):]
        assert [p for p in imports if p not in old_imports]==[p for p in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',updated_render) if '/cases-v4/' not in p]
        (stage/document).parent.mkdir(parents=True,exist_ok=True);(stage/document).write_text(updated);record(document)
        models[name]={'cases':len(items),'new_triangles':sum(counts),'triangles_per_case':counts,
                      'replacement_imports':[p.relative_to('Assets').as_posix() for p in pieces],
                      'replaced_imports':old_imports,'physics_bytes_exact':True,'collision_boxes_identical':True,
                      'unrelated_imports_exact':True}
        print(json.dumps({'model':name,**models[name]}),flush=True)
    manifest={'revision':'veridant-transport-cases-v4','stage':args.stage,'files':files,'models':models,
              'source_sha256':sources,'protected_sha256':protected,'cases_replaced':82,'geometry_checks':checks,
              'case_layout_replayed_and_verified':True,'physics_bytes_exact':True,'scene_unchanged':True,
              'reused_owned_geometry':reused}
    (stage/'plan-draft.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for group in (sources,protected):
        for p,h in group.items():assert sha(ROOT/p)==h,('Shared input changed',p)
    for p,item in files.items():
        assert sha(ROOT/item['source'])==item['after']
        assert (sha(ROOT/p) if (ROOT/p).exists() else None)==item['before'],('Shared target changed',p)
    assert placements()==rows
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'stage':args.stage,'files':len(files),'cases':82}),flush=True)


if __name__=='__main__':main()
