"""Replace only Veridant's old ivy cards, preserving current foliage imports."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import re
import shutil
import ast
import numpy as np
import map_kit as K
import veridant_parts as P
import veridant_map as V
import veridant_ivy as I
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/ivy-v2'
FOLDER=Path('Assets/models/maps/veridant/ivy-v2')
DOCUMENT=Path('Assets/models/maps/veridant/veridant_foliage.vmdl')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def placements():
    calls=[];old=P.ivy
    def record(model,at,right,w,h,seed=0,off=1.2):calls.append((at,right,w,h,seed,off))
    P.ivy=record
    try:
        V.ops(K.Model(),K.Model(),K.Model())
        V.resort_finish(K.Model(),K.Model())
    finally:P.ivy=old
    return calls


def build(stage_name):
    assert re.fullmatch('stage-[a-z0-9-]+',stage_name)
    stage=OUT/stage_name;assert not stage.exists();stage.mkdir(parents=True)
    source_paths=['Tools/veridant_ivy.py','Tools/veridant_stage_ivy.py','Tools/veridant_parts.py',
        'Tools/veridant_map.py','Tools/veridant_materials.py','Tools/map_kit.py','Tools/riverdale_parts.py',
        'Sources/Veridant/ivy-v2/leaf-source.png','Sources/Veridant/ivy-v2/previous-ivy.py.txt']
    inputs={p:sha(ROOT/p) for p in source_paths}
    document=(ROOT/DOCUMENT).read_text()
    imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',document)
    base=Path('Assets')/next(p for p in imports if p.endswith('foliage-base.obj'))
    assert 'ivy-v2' not in base.as_posix(),'Use a fresh revision against the preserved pre-ivy baseline.'
    # Retain every other model import, the old atlas and the source scene.
    protected_paths=[Path('Assets')/p for p in imports]
    protected_paths += [Path('Assets/scenes/maps/Veridant/veridant.scene'),
        Path('Assets/models/maps/veridant/veridant_foliage.obj'),
        Path('Assets/materials/veridant/vr_foliage.vmat'),Path('Assets/materials/veridant/vr_foliage_color.png'),
        Path('Assets/materials/veridant/vr_foliage_trans.png')]
    protected={p.as_posix():sha(ROOT/p) for p in protected_paths}
    calls=placements()
    namespace={**vars(P)}
    previous=(ROOT/'Sources/Veridant/ivy-v2/previous-ivy.py.txt').read_text()
    node=next(n for n in ast.parse(previous).body if isinstance(n,ast.FunctionDef) and n.name=='ivy')
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<original-ivy>','exec'),namespace)
    old,new=K.Model(),K.Model()
    for at,right,w,h,seed,off in calls:
        namespace['ivy'](old,at,right,w,h,seed,off)
        I.build_into(new,at,right,w,h,seed,off)
    assert not old.boxes and not old.hulls and not new.boxes and not new.hulls
    for paint,rows in new.polygons.items():
        for points,normal in rows:
            assert np.isfinite(points).all() and np.isfinite(normal).all()
            for j in range(1,len(points)-1):assert np.linalg.norm(np.cross(points[j]-points[0],points[j+1]-points[0]))>1e-8
    leaf=FOLDER/'ivy.obj';(stage/leaf).parent.mkdir(parents=True,exist_ok=True)
    K.write_obj(stage/leaf,new,'veridant_ivy_v2')
    wanted=Counter()
    for paint,rows in old.polygons.items():
        for points,normal in rows:
            vertices=[Patch.point(K.obj_vector(K.to_world(p))) for p in points]
            for j in range(1,len(vertices)-1):wanted[(paint.encode(),frozenset((vertices[0],vertices[j],vertices[j+1])))]+=1
    new_base=FOLDER/'foliage-base.obj'
    proof,found=Patch.replace_obj(ROOT/base,stage/'proof/combined.obj',stage/new_base,wanted,stage/leaf)
    assert found==wanted,(sum(found.values()),sum(wanted.values()))
    old_mtl=re.search(r'^mtllib\s+(.+)$',(ROOT/base).read_text(),re.MULTILINE)[1].strip()
    shutil.copyfile((ROOT/base).parent/old_mtl,stage/FOLDER/old_mtl)
    I.write_materials(stage/'Assets'/I.RESOURCE)
    a,b=span(document,'_class = "RenderMeshList"');render=document[a:b]
    x,y=span(render,'_class = "RenderMeshFile"');template=render[x:y]
    assert render.count('filename = "'+base.relative_to('Assets').as_posix()+'"')==1
    render=render.replace('filename = "'+base.relative_to('Assets').as_posix()+'"',
        'filename = "'+new_base.relative_to('Assets').as_posix()+'"',1)
    node=re.sub(r'name = "[^"]+"','name = "veridant_ivy_v2"',template,count=1)
    node=re.sub(r'filename = "[^"]+"','filename = "'+leaf.relative_to('Assets').as_posix()+'"',node,count=1)
    at=render.rfind(']');prefix=render[:at].rstrip()
    render=prefix+('' if prefix.endswith(',') else ',')+'\n'+node+'\n'+render[at:]
    updated=document[:a]+render+document[b:]
    remaps=''.join('{ from = "'+p+'.vmat" to = "'+r+'" },\n' for p,r in I.MATERIALS.items())
    at=updated.index('[',updated.index('remaps ='))+1
    updated=updated[:at]+'\n'+remaps+updated[at:]
    assert 'PhysicsShape' not in document and 'PhysicsShape' not in updated
    (stage/DOCUMENT).write_text(updated,encoding='utf-8')
    files={}
    for p in sorted((stage/'Assets').rglob('*')):
        if not p.is_file():continue
        relative=p.relative_to(stage);before=sha(ROOT/relative);backup=stage/'before'/relative
        if before:backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,backup)
        files[relative.as_posix()]={'before':before,'after':sha(p),'source':p.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}
    for group in (inputs,protected):
        for p,value in group.items():assert sha(ROOT/p)==value,p
    manifest={'revision':'veridant-ivy-v2','stage':stage_name,'files':files,'source_sha256':inputs,
        'protected_sha256':protected,'retained_geometry_proof':proof,'base_import':base.as_posix(),
        'new_triangles':new.triangle_count(),'planting':new.ivy_stats,'placements':calls,
        'scene_unchanged':True,'collision_unchanged':True,'old_atlas_unchanged':True}
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2,default=lambda v:v.tolist())+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':stage_name})+'\n')
    print(json.dumps({k:manifest[k] for k in ('stage','new_triangles','planting','retained_geometry_proof')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',default='stage-v1');a=p.parse_args();build(a.stage)
