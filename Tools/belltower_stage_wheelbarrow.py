"""Stage only the two wheelbarrows, preserving unrelated OBJ bytes and all physics."""
import argparse
import ast
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil
import belltower_map as B
import belltower_gardens as G
import belltower_wheelbarrow as W
import map_kit as K
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/wheelbarrow-v2'
PRIVATE='Assets/models/maps/belltower/wheelbarrow-v2'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def point(values):return tuple(round(float(x)*1000) for x in values)


def signatures(path):
    vertices=[None];paint=None;result=Counter()
    for line in path.open('rb'):
        if line.startswith(b'v '):vertices.append(point(line.split()[1:]))
        elif line.startswith(b'usemtl '):paint=line.split()[1]
        elif line.startswith(b'f '):
            ids=[int(v.split(b'/')[0]) for v in line.split()[1:]]
            result[(paint,frozenset(vertices[i] for i in ids))]+=1
    return result


def strip(source,wanted,stage):
    positions={p for paint,pts in wanted for p in pts};paints={p for p,pts in wanted}
    sparse={};index=0;paint=None;removed=set();found=Counter();faces=0
    before=sha(source)
    for number,line in enumerate(source.open('rb')):
        if line.startswith(b'v '):
            index+=1;p=point(line.split()[1:])
            if p in positions:sparse[index]=p
        elif line.startswith(b'usemtl '):paint=line.split()[1]
        elif line.startswith(b'f '):
            faces+=1
            if paint not in paints:continue
            ids=[int(v.split(b'/')[0]) for v in line.split()[1:]]
            if all(i in sparse for i in ids):
                signature=(paint,frozenset(sparse[i] for i in ids))
                if signature in wanted:removed.add(number);found[signature]+=1
    if not removed:return None,found
    relative=source.relative_to(ROOT).as_posix();target=stage/relative;backup=stage/'before'/relative
    target.parent.mkdir(parents=True,exist_ok=True);backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,backup);digest=hashlib.sha256()
    with target.open('wb') as stream:
        for number,line in enumerate(source.open('rb')):
            if number not in removed:stream.write(line);digest.update(line)
    assert sha(source)==sha(backup)==before and sha(target)==digest.hexdigest()
    return {'before':before,'after':sha(target),'source':target.relative_to(ROOT).as_posix(),
        'backup':backup.relative_to(ROOT).as_posix(),'removed_old_wheelbarrow_triangles':len(removed),
        'all_retained_bytes_exact':True,'triangles_before':faces,'triangles_after':faces-len(removed)},found


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',default='stage-v1');args=ap.parse_args()
    assert re.fullmatch(r'stage-[a-z0-9-]+',args.stage)
    stage=OUT/args.stage;stage.mkdir(parents=True,exist_ok=False)
    previous=ROOT/'Sources/Belltower/props/wheelbarrow-v2/previous-gardens.py'
    tree=ast.parse(previous.read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='wheelbarrow')
    namespace=dict(vars(G));exec(compile(ast.Module(body=[function],type_ignores=[]),str(previous),'exec'),namespace)
    old,new=K.Model(),K.Model();p=B.Place((-1520.,-1180.,B.GARDEN_Z),20.)
    namespace['wheelbarrow'](old,p);old.tile_overrides.update(B.Detail.TILES);geometry=W.build(new,p)
    assert not old.boxes and not old.hulls and not new.boxes and not new.hulls
    files={};protected={};models={};preview_files=[]
    def record(relative):
        relative=Path(relative).as_posix()
        source=stage/relative;target=ROOT/relative;backup=stage/'before'/relative
        before=sha(target) if target.exists() else None
        if before:backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
        files[relative]={'before':before,'after':sha(source),'source':source.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}
    material='Assets/materials/belltower/wheelbarrow-v2';W.write_materials(stage/material)
    for path in sorted((stage/material).iterdir()):record(path.relative_to(stage).as_posix())
    for side,old_model,new_model in (('west',old,new),('east',old.mirrored(B.EAST_PAINTS),new.mirrored(B.EAST_PAINTS))):
        print(json.dumps({'staging_side':side}),flush=True)
        folder=stage/PRIVATE;folder.mkdir(parents=True,exist_ok=True)
        fragment=f'{PRIVATE}/{side}.obj';K.write_obj(stage/fragment,new_model,f'belltower_{side}')
        record(fragment);record(str(Path(fragment).with_suffix('.mtl')))
        proof=stage/f'proof/{side}-old.obj';proof.parent.mkdir(exist_ok=True);K.write_obj(proof,old_model,f'belltower_{side}')
        wanted=signatures(proof)
        canonical=ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        row,found=strip(canonical,wanted,stage);assert found==wanted,('Canonical old wheelbarrow mismatch',side,sum(found.values()),sum(wanted.values()))
        files[canonical.relative_to(ROOT).as_posix()]=row
        document=canonical.with_suffix('.vmdl');raw=document.read_bytes().decode('utf8');a,b=span(raw,'_class = "RenderMeshList"')
        imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',raw[a:b]);found_parts=Counter();parts=[]
        for resource in imports:
            if not any(name in Path(resource).name for name in ('iron_black','iron_green','furniture_wood')):continue
            source=ROOT/'Assets'/resource;row,found=strip(source,wanted,stage);found_parts.update(found)
            if row:files[source.relative_to(ROOT).as_posix()]=row;parts.append(resource)
        assert found_parts==wanted,('Installed old wheelbarrow mismatch',side,sum(found_parts.values()),sum(wanted.values()))
        # Copy the existing render-file schema, preserving its engine-specific import settings.
        render=raw[a:b];start,end=span(render,'_class = "RenderMeshFile"');node=render[start:end]
        node=re.sub(r'name = "[^"]+"',f'name = "wheelbarrow_v2_{side}"',node,count=1)
        node=re.sub(r'filename = "[^"]+"',f'filename = "{fragment[7:]}"',node,count=1)
        at=render.rfind(']');prefix=render[:at].rstrip()
        updated_render=prefix+('' if prefix.endswith(',') else ',')+'\n'+node+'\n'+render[at:]
        updated=raw[:a]+updated_render+raw[b:]
        remaps=''.join(f'{{ from = "{paint}.vmat" to = "{material}" }},\n' for paint,material in W.MATERIALS.items())
        at=updated.index('[',updated.index('remaps ='))+1;updated=updated[:at]+'\n'+remaps+updated[at:]
        marker='_class = "PhysicsShapeList"';assert raw[raw.index(marker):]==updated[updated.index(marker):]
        relative=document.relative_to(ROOT).as_posix();(stage/relative).write_bytes(updated.encode('utf8'));record(relative)
        trial=updated
        for resource in parts:
            base=Path(resource).name;preview=f'{PRIVATE}/preview-{side}-{base}'
            shutil.copy2(stage/'Assets'/resource,stage/preview);record(preview);preview_files.append(preview)
            # Existing files name a shared MTL; retain that exact resolved dependency beside the preview.
            data=(stage/preview).read_bytes()
            mtllib=next(line.split(maxsplit=1)[1].decode() for line in data.splitlines() if line.startswith(b'mtllib '))
            dep=(Path(preview).parent/mtllib).as_posix()
            if dep not in files:
                shutil.copy2((ROOT/'Assets'/resource).parent/mtllib,stage/dep);record(dep)
            trial=trial.replace('filename = "'+resource+'"','filename = "'+preview[7:]+'"')
        trial_path=f'{PRIVATE}/trial_{side}.vmdl';(stage/trial_path).write_bytes(trial.encode('utf8'));record(trial_path)
        for resource in imports:
            full='Assets/'+resource
            if full not in files:protected[full]=sha(ROOT/full)
        models[side]={'document':relative,'trial':trial_path,'parts':parts,'removed_triangles':sum(wanted.values()),
            'new_triangles':new_model.triangle_count(),'physics_suffix_exact':True}
    protected['Assets/scenes/maps/Belltower/belltower.scene']=sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')
    protected['Assets/materials/belltower/furniture_wood.vmat']=sha(ROOT/'Assets/materials/belltower/furniture_wood.vmat')
    sources=['Tools/belltower_wheelbarrow.py','Tools/belltower_stage_wheelbarrow.py','Tools/belltower_gardens.py',
        'Tools/belltower_furniture.py','Tools/map_kit.py','Tools/riverdale_parts.py',previous.relative_to(ROOT).as_posix()]
    result={'revision':'belltower-wheelbarrow-v2','stage':args.stage,'files':files,'protected_sha256':protected,
        'source_sha256':{p:sha(ROOT/p) for p in sources},'materials':W.MATERIALS,'models':models,'geometry':geometry,
        'required_source_snippets':{'Tools/belltower_map.py':['p = Place( ( -1520, -1180, z ), 20 )\n    Gardens.wheelbarrow( model, p )']},
        'scene_unchanged':True,'all_physics_unchanged':True}
    for p,d in files.items():assert (sha(ROOT/p) if (ROOT/p).exists() else None)==d['before'],p
    (stage/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage,'preview':True})+'\n')
    (OUT/'compile-trials.json').write_text(json.dumps({'calls':[{'name':'asset_compile','arguments':{'path':v,'full':False}} for p,v in W.MATERIALS.items() if p!='bw2_wood']+
        [{'name':'asset_compile','arguments':{'path':m['trial'][7:],'full':False}} for m in models.values()]}))
    (OUT/'compile-live.json').write_text(json.dumps({'calls':[{'name':'asset_compile','arguments':{'path':m['document'][7:],'full':False}} for m in models.values()]}))
    print(json.dumps({'files':len(files),'old_triangles_per_wheelbarrow':len(list(wanted.elements())),**geometry}),flush=True)


if __name__=='__main__':main()
