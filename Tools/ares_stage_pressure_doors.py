"""Extract only the three installed pressure hatches into dedicated imports."""
import argparse
import importlib.util
import inspect
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import ares_map as A
import ares_pressure_door as D
from ares_pressure_materials import write_materials
from ares_pressure_capture import placements
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ares/airlock-door-v1'


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stage',required=True);args=ap.parse_args()
    assert re.fullmatch(r'stage-[a-z0-9-]+',args.stage)
    stage=OUT/args.stage;stage.mkdir(parents=True,exist_ok=False)
    sources={p:Patch.sha(ROOT/p) for p in ('Tools/ares_airlock.py','Tools/ares_pressure_door.py',
        'Tools/ares_pressure_materials.py','Tools/ares_pressure_capture.py','Tools/ares_stage_pressure_doors.py',
        'Tools/map_kit.py','Tools/riverdale_parts.py','Tools/boxyard_map.py',
        'Sources/Ares/pressure-doors-v2/previous-airlock.py')}
    snippets={'Tools/ares_map.py':[inspect.getsource(A.configure)]}
    original='Assets/models/maps/ares/ares_hall.obj';document='Assets/models/maps/ares/ares_hall.vmdl'
    raw=(ROOT/document).read_bytes().decode();a,b=span(raw,'_class = "RenderMeshList"');render=raw[a:b]
    assert render.count('filename = "models/maps/ares/ares_hall.obj"')==1
    assert 'pressure-doors-v2' not in render
    protected={p:Patch.sha(ROOT/p) for p in (original,'Assets/models/maps/ares/ares_hall.mtl',
        'Assets/scenes/maps/Ares/ares.scene','Assets/models/maps/ares/ares_hall_hulls_metal.obj',
        'Assets/models/maps/ares/ares_hall_hulls_default.obj')}
    files={};details=[];old=K.Model();pieces=[]
    legacy_spec=importlib.util.spec_from_file_location('ares_pressure_legacy',ROOT/'Sources/Ares/pressure-doors-v2/previous-airlock.py')
    legacy=importlib.util.module_from_spec(legacy_spec);legacy_spec.loader.exec_module(legacy)

    def record(relative):
        target=ROOT/relative;staged=stage/relative;before=Patch.sha(target) if target.exists() else None
        backup=stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup);assert Patch.sha(backup)==before
        files[relative]={'before':before,'after':Patch.sha(staged),'source':staged.relative_to(ROOT).as_posix(),
                         'backup':backup.relative_to(ROOT).as_posix() if before else None}

    specs=placements()
    for spec in specs:
        kwargs={k:v for k,v in spec.items() if k!='name'}
        legacy.pressure_door(old,**kwargs)
        new=K.Model();detail=D.pressure_door(new,**kwargs)
        assert not new.boxes and not new.hulls
        for paint,rows in new.polygons.items():
            for index,(points,normal) in enumerate(rows):
                assert np.isfinite(points).all() and np.isfinite(normal).all()
                assert np.linalg.norm(normal)>.99
                ns=new.polygon_normals.get((paint,index))
                if ns is not None:assert np.isfinite(ns).all()
        A.configure(new)
        assert all(new.material_overrides[k]==v for k,v in D.MATERIALS.items())
        assert new.triangle_count()<40000
        piece=f'Assets/models/maps/ares/pressure-doors-v2/{spec["name"].replace("-","_")}.obj'
        (stage/piece).parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(stage/piece,new,'ares_pressure_'+spec['name']);record(piece);record(piece[:-4]+'.mtl')
        pieces.append(piece);details.append({**spec,**detail})
        print(json.dumps(details[-1]),flush=True)
    assert old.triangle_count()==3954 and not old.boxes and not old.hulls
    lookup,polygons=Patch.lookup_polygons(old)
    base='Assets/models/maps/ares/pressure-doors-v2/hall_base.obj'
    extraction,found=Patch.replace_obj(ROOT/original,stage/'proof/combined.obj',stage/base,lookup,stage/pieces[0])
    Patch.coverage(found,lookup,polygons);assert extraction['removed_triangles']==3954
    # The old doors were appended after the original hall. Their unused final
    # attribute tables start a new, empty mesh in Source 2's OBJ importer.
    # Remove only that unused suffix; all retained geometry and indices stay exact.
    retained=(stage/base).read_bytes().splitlines(keepends=True)
    last_face=max(i for i,line in enumerate(retained) if line.startswith(b'f '))
    tail=retained[last_face+1:]
    assert all(line.startswith((b'v ',b'vt ',b'vn ',b'usemtl ',b'g ')) or not line.strip() for line in tail)
    kept=retained[:last_face+1]
    counts=[sum(line.startswith(prefix) for line in kept) for prefix in (b'v ',b'vt ',b'vn ')]
    for line in kept:
        if line.startswith(b'f '):
            assert all(0<int(value)<=count for token in line.split()[1:] for value,count in zip(token.split(b'/'),counts))
    (stage/base).write_bytes(b''.join(kept))
    extraction['unused_trailing_attribute_group_removed']=True
    extraction['base_import_sha256']=Patch.sha(stage/base)
    record(base)
    base_mtl='Assets/models/maps/ares/pressure-doors-v2/ares_hall.mtl'
    shutil.copy2(ROOT/'Assets/models/maps/ares/ares_hall.mtl',stage/base_mtl);record(base_mtl)
    i,j=span(render,'_class = "RenderMeshFile"');template=render[i:j]
    new_render=render.replace('filename = "models/maps/ares/ares_hall.obj"',
        'filename = "models/maps/ares/pressure-doors-v2/hall_base.obj"')
    nodes=[]
    for spec,piece in zip(specs,pieces):
        node=re.sub(r'name = "[^"]+"',f'name = "pressure_{spec["name"].replace("-","_")}"',template,count=1)
        node=re.sub(r'filename = "[^"]+"',f'filename = "{piece[7:]}"',node,count=1)
        nodes.append(node)
    end=new_render.rfind(']');prefix=new_render[:end].rstrip()
    new_render=prefix+('' if prefix.endswith(',') else ',')+'\n'+',\n'.join(nodes)+'\n'+new_render[end:]
    updated=raw[:a]+new_render+raw[b:]
    index=updated.index('[',updated.index('remaps ='))+1
    remaps=''.join(f'\n{{ from = "{p}.vmat" to = "{v}" }},' for p,v in D.MATERIALS.items())
    updated=updated[:index]+remaps+'\n'+updated[index:]
    marker='_class = "PhysicsShapeList"';assert raw[raw.index(marker):]==updated[updated.index(marker):]
    (stage/document).parent.mkdir(parents=True,exist_ok=True);(stage/document).write_bytes(updated.encode());record(document)
    trial='Assets/models/maps/ares/pressure-doors-v2/trial_hall.vmdl'
    (stage/trial).write_bytes(updated.encode());record(trial)
    material='Assets/materials/ares/pressure-doors-v2';write_materials(stage/material)
    for file in sorted((stage/material).iterdir()):record(file.relative_to(stage).as_posix())
    manifest={'revision':'ares-pressure-doors-v2','stage':args.stage,'files':files,'source_sha256':sources,
        'protected_sha256':protected,'required_source_snippets':snippets,'sections':details,
        'materials':D.MATERIALS,'new_triangles':sum(d['triangles'] for d in details),
        'physics_bytes_exact':True,'original_obj_indices_preserved':True,'collision_envelopes_preserved':True,
        'base_import':base,'trial_document':trial,**extraction}
    for group in (sources,protected):
        for p,h in group.items():assert Patch.sha(ROOT/p)==h,('Shared input changed',p)
    for p,item in files.items():
        assert Patch.sha(ROOT/item['source'])==item['after']
        assert (Patch.sha(ROOT/p) if (ROOT/p).exists() else None)==item['before'],('Target changed',p)
    assert placements()==specs
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Compile and inspect the independent trial before publishing the live hall.
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage,'preview':True})+'\n')
    print(json.dumps({'doors':3,'triangles':manifest['new_triangles'],'old_removed':3954,
                      'files':len(files),'physics_preserved':True}),flush=True)


if __name__=='__main__':main()
