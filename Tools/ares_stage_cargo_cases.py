"""Stage scoped Ares case replacement assets and deterministic scene instances."""
import argparse
from collections import Counter
import inspect
import json
from pathlib import Path
import re
import shutil
import numpy as np

import ares_map as A
import ares_cargo_case as C
import map_kit as K
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ares/crate-v2'


def placements():
    rows=[];original=A.case
    def capture(m,e,n,z,heading,size=A.AM.CASE,front='front_text',side='side_logo',top='top_ribs',collide=True):
        rows.append({'e':float(e),'n':float(n),'z':float(z),'heading':float(heading),
                     'size':list(size),'front':front,'side':side,'top':top,'collide':collide})
    try:
        A.case=capture;A.dressing(K.Model())
    finally:A.case=original
    return rows


def strip_cases(source,target,model):
    # Stacked cases can have coincident trim triangles. Match their exact
    # multiplicity, rather than assuming every old polygon is unique.
    expected=Counter()
    for paint,rows in model.polygons.items():
        for points,normal in rows:
            vertices=[Patch.point(K.obj_vector(K.to_world(p))) for p in points]
            for i in range(1,len(vertices)-1):
                expected[(paint.encode(),frozenset((vertices[0],vertices[i],vertices[i+1])))]+=1
    positions={p for paint,triangle in expected for p in triangle}
    paints={paint for paint,triangle in expected}
    sparse={};count=0;paint=None;found=Counter();retained=[]
    original=Patch.sha(source)
    for line in source.open('rb'):
        if line.startswith(b'v '):
            count+=1;point=Patch.point(line[2:].decode())
            if point in positions:sparse[count]=point
        elif line.startswith(b'usemtl '):paint=line.split()[1]
        elif line.startswith(b'f ') and paint in paints:
            indices=[int(p.split(b'/')[0]) for p in line.split()[1:]]
            if all(i in sparse for i in indices):
                signature=(paint,frozenset(sparse[i] for i in indices))
                if signature in expected:
                    found[signature]+=1;continue
        retained.append(line)
    assert found==expected,('Case triangle multiplicity differs',sum(found.values()),sum(expected.values()))
    assert sum(found.values())==model.triangle_count()
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b''.join(retained))
    assert Patch.sha(source)==original
    return {'removed_triangles':sum(found.values()),'unrelated_obj_bytes_exact':True,
            'retained_bytes_sha256':Patch.sha(target),'original_vertex_indices_preserved':True,
            'coincident_case_triangles_handled':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',required=True)
    args=parser.parse_args();assert re.fullmatch('stage-[a-z0-9-]+',args.stage)
    stage=OUT/args.stage;assert not stage.exists();stage.mkdir(parents=True)
    sources={p:Patch.sha(ROOT/p) for p in ('Tools/ares_cargo_case.py','Tools/ares_case_shell.py',
        'Tools/ares_stage_cargo_cases.py','Tools/map_kit.py','Tools/riverdale_parts.py',
        'Sources/Ares/crate-v2/original-case.py.txt')}
    source_hooks={ 'Tools/ares_map.py': [inspect.getsource(A.case),inspect.getsource(A.case_stack),
        'world["Children"].append( scene_group( ids, case_props ) )'] }
    assert 'append_instance' in inspect.getsource(A.case), 'Install the source regeneration hook first.'
    specs=placements();assert len(specs)==132
    namespace=dict(vars(A));exec((ROOT/'Sources/Ares/crate-v2/original-case.py.txt').read_text(),namespace)
    legacy=namespace['case'];old=K.Model();props=[]
    for index,item in enumerate(specs):
        legacy(old,**item)
        capture=K.Model();C.append_instance(capture,**item)
        assert len(capture.props)==1 and len(capture.boxes)==1 and not capture.polygons
        props.extend(capture.props)
        old_box=old.boxes[-1];new_box=capture.boxes[0]
        for a,b in zip(old_box[:3],new_box[:3]):assert np.allclose(a,b)
        assert old_box[3]==new_box[3]
    assert len(old.boxes)==132 and not old.hulls
    document=Path('Assets/models/maps/ares/ares_dressing.vmdl')
    document_bytes=(ROOT/document).read_bytes()
    text=document_bytes.decode('utf-8');a,b=span(text,'_class = "RenderMeshList"')
    imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text[a:b])
    assert imports==['models/maps/ares/ares_dressing.obj'],imports
    canonical=Path('Assets')/imports[0]
    protected={canonical.as_posix():Patch.sha(ROOT/canonical),
               'Assets/scenes/maps/Ares/ares.scene':Patch.sha(ROOT/'Assets/scenes/maps/Ares/ares.scene')}
    for path in (ROOT/'Assets/models/maps/ares').glob('*'):
        if path.suffix in ('.vmdl','.obj','.mtl') and path!=ROOT/document:
            protected[path.relative_to(ROOT).as_posix()]=Patch.sha(path)
    for path in (ROOT/'Assets/materials/ares').iterdir():
        if path.is_file() and path.suffix in ('.vmat','.png','.jpg','.tga'):
            protected[path.relative_to(ROOT).as_posix()]=Patch.sha(path)
    files={}
    def record(relative,phase='assets'):
        relative=Path(relative);source=ROOT/relative;target=stage/relative
        before=Patch.sha(source) if source.exists() else None;backup=stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,backup)
        files[relative.as_posix()]={'before':before,'after':Patch.sha(target),'phase':phase,
            'source':target.relative_to(ROOT).as_posix(),'backup':backup.relative_to(ROOT).as_posix() if before else None}
    materials=Path('Assets/materials/ares/crate-v2');C.write_materials(stage/materials)
    for p in sorted((stage/materials).iterdir()):record(p.relative_to(stage))
    models=Path('Assets/models/props/ares/crate-v2');model_reports=C.write_models(stage/models)
    for p in sorted((stage/models).iterdir()):record(p.relative_to(stage))
    base=Path('Assets/models/maps/ares/crate-v2/dressing-base.obj')
    detail=strip_cases(ROOT/canonical,stage/base,old)
    assert detail['removed_triangles']==old.triangle_count()==12408
    record(base)
    mtl=base.with_name('ares_dressing.mtl')
    shutil.copyfile((ROOT/canonical).with_suffix('.mtl'),stage/mtl);record(mtl)
    revised=text.replace('filename = "models/maps/ares/ares_dressing.obj"',
                         'filename = "models/maps/ares/crate-v2/dressing-base.obj"')
    assert revised!=text
    marker='_class = "PhysicsShapeList"';assert text[text.index(marker):]==revised[revised.index(marker):]
    (stage/document).parent.mkdir(parents=True,exist_ok=True);(stage/document).write_bytes(revised.encode('utf-8'));record(document,'integration')
    group=C.scene_group(A.ids,props);assert len(group['Children'])==132
    group_path=stage/'scene-group.json';group_path.write_text(json.dumps(group,indent=2)+'\n')
    (stage/'placements.json').write_text(json.dumps(specs,indent=2)+'\n')
    manifest={'revision':'ares-cargo-case-v2','stage':args.stage,'files':files,
              'source_sha256':sources,'required_source_snippets':source_hooks,
              'protected_sha256':protected,'case_count':132,'models':model_reports,
              'scene_group':group_path.relative_to(ROOT).as_posix(),'scene_group_sha256':Patch.sha(group_path),
              'original_scene_sha256':protected['Assets/scenes/maps/Ares/ares.scene'],
              'scene_parent_guid':A.ids('world'),'scene_group_guid':group['__guid'],
              'base_import':base.as_posix(),'collision_preserved':True,**detail,
              'original_triangles_removed':old.triangle_count(),'shared_models':4,'lods_per_model':3}
    for group_hashes in (sources,protected):
        for p,h in group_hashes.items():assert Patch.sha(ROOT/p)==h,('Shared input changed',p)
    for p,parts in source_hooks.items():
        current=(ROOT/p).read_text();assert all(part in current for part in parts),p
    for p,item in files.items():
        assert (Patch.sha(ROOT/p) if (ROOT/p).exists() else None)==item['before'],p
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'cases':132,'shared_models':4,'models':model_reports,
        'files':len(files),'removed_old_triangles':old.triangle_count(),'collision_preserved':True},indent=2))


if __name__=='__main__':main()
