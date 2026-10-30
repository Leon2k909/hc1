"""Stage the three v3 door imports without regenerating the hall or scene."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import ares_map as A
import ares_pressure_formed as D
from ares_pressure_formed_materials import write_materials
from ares_pressure_capture import placements

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ares/pressure-door-v3'
DOCUMENT='Assets/models/maps/ares/ares_hall.vmdl'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def obj_triangles(path):
    return sum(len(line.split())-3 for line in Path(path).open('rb') if line.startswith(b'f '))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stage',required=True)
    ap.add_argument('--geometry-from',help='Reuse verified imports when only materials changed.');args=ap.parse_args()
    assert re.fullmatch(r'stage-[a-z0-9-]+',args.stage)
    stage=OUT/args.stage;stage.mkdir(parents=True,exist_ok=False)
    sources={p:sha(ROOT/p) for p in ('Tools/ares_pressure_formed.py','Tools/ares_pressure_formed_materials.py',
        'Tools/ares_stage_formed_doors.py','Tools/ares_pressure_capture.py','Tools/map_kit.py',
        'Tools/riverdale_parts.py','Tools/boxyard_map.py','Sources/Ares/pressure-doors-v3/concept-v1.png')}
    protected={p:sha(ROOT/p) for p in ('Assets/models/maps/ares/ares_hall.obj','Assets/models/maps/ares/ares_hall.mtl',
        'Assets/models/maps/ares/ares_hall_hulls_metal.obj','Assets/models/maps/ares/ares_hall_hulls_default.obj',
        'Assets/models/maps/ares/pressure-doors-v2/hall_base.obj','Assets/scenes/maps/Ares/ares.scene')}
    files={};details=[];raw=(ROOT/DOCUMENT).read_text();updated=raw
    reuse=None
    if args.geometry_from:
        assert re.fullmatch(r'stage-[a-z0-9-]+',args.geometry_from)
        reuse=json.loads((OUT/args.geometry_from/'manifest.json').read_text())
        for path in ('Tools/ares_pressure_formed.py','Tools/ares_pressure_capture.py','Tools/map_kit.py',
                     'Tools/riverdale_parts.py','Tools/boxyard_map.py'):
            assert sha(ROOT/path)==reuse['source_sha256'][path],('Geometry input changed',path)
        assert reuse['required_source_snippets']['Tools/ares_map.py']==[inspect.getsource(A.configure)]

    def record(path):
        source=stage/path;target=ROOT/path;before=sha(target) if target.exists() else None
        backup=stage/'before'/path
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup);assert sha(backup)==before
        files[path]={'before':before,'after':sha(source),'source':source.relative_to(ROOT).as_posix(),
                     'backup':backup.relative_to(ROOT).as_posix() if before else None}

    for spec in placements():
        name=spec['name'].replace('-','_');relative=f'Assets/models/maps/ares/pressure-doors-v3/{name}.obj'
        (stage/relative).parent.mkdir(parents=True,exist_ok=True)
        if reuse:
            detail=next(x for x in reuse['sections'] if x['name']==spec['name'])
            for suffix in ('.obj','.mtl'):
                path=relative[:-4]+suffix;item=reuse['files'][path]
                assert sha(ROOT/item['source'])==item['after']
                shutil.copy2(ROOT/item['source'],stage/path)
        else:
            model=K.Model();detail=D.pressure_door(model,**{k:v for k,v in spec.items() if k!='name'})
            assert not model.boxes and not model.hulls and model.triangle_count()<100000
            A.configure(model);assert all(model.material_overrides[k]==v for k,v in D.MATERIALS.items())
            for paint,rows in model.polygons.items():
                for i,(points,normal) in enumerate(rows):
                    assert np.isfinite(points).all() and np.isfinite(normal).all()
                    ns=model.polygon_normals.get((paint,i))
                    if ns is not None:assert np.isfinite(ns).all() and np.all(np.linalg.norm(ns,axis=1)>.99)
            count=K.write_obj(stage/relative,model,'ares_pressure_'+name);assert count==model.triangle_count()
        record(relative);record(relative[:-4]+'.mtl')
        old=f'models/maps/ares/pressure-doors-v2/{name}.obj';new=relative[7:]
        if 'filename = "'+old+'"' in updated:
            assert updated.count('filename = "'+old+'"')==1
            updated=updated.replace('filename = "'+old+'"','filename = "'+new+'"')
        else:
            assert updated.count('filename = "'+new+'"')==1
        details.append({**spec,**detail});print(json.dumps(details[-1]),flush=True)
    assert updated.count('materials/ares/pressure-doors-v2/') in (0,13)
    updated=updated.replace('materials/ares/pressure-doors-v2/','materials/ares/pressure-doors-v3/')
    at=updated.index('[',updated.index('remaps ='))+1
    added=''.join('\n{ from = "'+p+'.vmat" to = "'+v+'" },' for p,v in D.MATERIALS.items() if p+'.vmat' not in updated)
    updated=updated[:at]+added+updated[at:]
    # No original hall mesh, physics source, transform, light or scene is rebuilt.
    marker='_class = "PhysicsShapeList"';assert raw[raw.index(marker):]==updated[updated.index(marker):]
    assert updated.count('filename = "models/maps/ares/pressure-doors-v2/hall_base.obj"')==1
    (stage/DOCUMENT).parent.mkdir(parents=True,exist_ok=True);(stage/DOCUMENT).write_text(updated);record(DOCUMENT)
    trial='Assets/models/maps/ares/pressure-doors-v3/trial_hall.vmdl'
    (stage/trial).write_text(updated);record(trial)
    materials='Assets/materials/ares/pressure-doors-v3';write_materials(stage/materials)
    for path in sorted((stage/materials).iterdir()):record(path.relative_to(stage).as_posix())
    manifest=dict(revision='ares-pressure-doors-v3',stage=args.stage,files=files,source_sha256=sources,
        protected_sha256=protected,required_source_snippets={'Tools/ares_map.py':[inspect.getsource(A.configure)]},
        sections=details,materials=D.MATERIALS,trial_document=trial,new_triangles=sum(d['triangles'] for d in details),
        retained_hall_triangles=obj_triangles(ROOT/'Assets/models/maps/ares/pressure-doors-v2/hall_base.obj'),physics_bytes_exact=True,collision_envelopes_preserved=True,
        base_import='Assets/models/maps/ares/pressure-doors-v2/hall_base.obj')
    for group in (sources,protected):
        for path,digest in group.items():assert sha(ROOT/path)==digest,('Shared source changed',path)
    for path,item in files.items():assert (sha(ROOT/path) if (ROOT/path).exists() else None)==item['before'],path
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage,'preview':True})+'\n')
    (OUT/'asset-info-request.json').write_text(json.dumps({'calls':[{'name':'asset_info','arguments':{'path':v}} for v in D.MATERIALS.values()]+[{'name':'asset_info','arguments':{'path':DOCUMENT[7:]}}]}))
    (OUT/'compile-materials.json').write_text(json.dumps({'calls':[{'name':'asset_compile','arguments':{'path':v,'full':False}} for v in D.MATERIALS.values()]}))
    (OUT/'compile-trial.json').write_text(json.dumps({'path':trial[7:],'full':False}))
    (OUT/'compile-hall.json').write_text(json.dumps({'path':DOCUMENT[7:],'full':False}))
    print(json.dumps(dict(doors=3,new_triangles=manifest['new_triangles'],files=len(files),preview=True)),flush=True)


if __name__=='__main__':main()
