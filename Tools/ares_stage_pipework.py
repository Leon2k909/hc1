"""Stage only Ares wall-pipe render geometry; retain the live hall's other work."""
import argparse
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import re
import shutil
from collections import Counter
import numpy as np
import ares_map as A
import ares_pipework as D
import map_kit as K
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ares/pipework-v1'
DOCUMENT='Assets/models/maps/ares/ares_hall.vmdl'


def preflight(source,wanted,polygons):
    positions={p for paint,face in wanted for p in face};paints={p for p,face in wanted}
    sparse={};count=0;paint=None;found=Counter()
    for line in source.open('rb'):
        if line.startswith(b'v '):
            count+=1;point=Patch.point(line[2:].decode())
            if point in positions:sparse[count]=point
        elif line.startswith(b'usemtl '):paint=line.split()[1]
        elif line.startswith(b'f ') and paint in paints:
            ids=[int(token.split(b'/')[0]) for token in line.split()[1:]]
            if all(i in sparse for i in ids):
                key=(paint,frozenset(sparse[i] for i in ids))
                if key in wanted:found[key]+=1
    Patch.coverage(found,wanted,polygons)
    assert sum(found.values())==2240
    print(json.dumps({'original_scope_verified':True,'matched_triangles':sum(found.values())}),flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stage',default='stage-v1');args=ap.parse_args()
    assert re.fullmatch(r'stage-[a-z0-9-]+',args.stage)
    stage=OUT/args.stage;stage.mkdir(parents=True,exist_ok=False)
    sources={p:Patch.sha(ROOT/p) for p in ('Tools/ares_pipework.py','Tools/ares_stage_pipework.py',
        'Tools/map_kit.py','Tools/riverdale_parts.py','Tools/boxyard_map.py','Sources/Ares/pipework-v1/legacy.py')}
    snippets={'Tools/ares_map.py':[inspect.getsource(A.pipe_run)]}
    raw=(ROOT/DOCUMENT).read_text();a,b=span(raw,'_class = "RenderMeshList"');render=raw[a:b]
    imports=re.findall(r'filename = "([^"]+\.obj)"',render)
    candidate=[p for p in imports if Path(p).stem in ('hall_base','ares_hall')]
    assert len(candidate)==1,candidate
    active='Assets/'+candidate[0]
    original=(ROOT/active).read_bytes()
    mtllib=next(line.split(maxsplit=1)[1].decode() for line in original.splitlines() if line.startswith(b'mtllib '))
    live_mtl=(Path(active).parent/mtllib).as_posix()
    protected_paths=['Assets/models/maps/ares/ares_hall.obj','Assets/models/maps/ares/ares_hall.mtl',
        'Assets/scenes/maps/Ares/ares.scene',live_mtl,
        'Assets/models/maps/ares/ares_hall_hulls_default.obj','Assets/models/maps/ares/ares_hall_hulls_metal.obj']
    protected_paths += ['Assets/'+p for p in imports if 'Assets/'+p!=active]
    protected={p:Patch.sha(ROOT/p) for p in dict.fromkeys(protected_paths)}
    # Save the starting document as evidence; it is not a publication target.
    proof=stage/'before'/DOCUMENT;proof.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/DOCUMENT,proof)
    spec=importlib.util.spec_from_file_location('ares_pipework_legacy',ROOT/'Sources/Ares/pipework-v1/legacy.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    old,new=K.Model(),K.Model();reports=[];placements=D.placements()
    for row in placements:
        kwargs={k:v for k,v in row.items() if k not in ('name','wall_n')}
        legacy.pipe_run(old,**kwargs)
    lookup,polygons=Patch.lookup_polygons(old);preflight(ROOT/active,lookup,polygons)
    for row in placements:
        kwargs={k:v for k,v in row.items() if k not in ('name','wall_n')}
        report=D.pipe_run(new,**kwargs,wall_n=row['wall_n']);reports.append({**row,**report})
        print(json.dumps({'run':row['name'],**report}),flush=True)
    assert not old.boxes and not old.hulls and not new.boxes and not new.hulls
    assert old.triangle_count()==2240,old.triangle_count()
    assert new.triangle_count()<350000,new.triangle_count()
    for key,poly_rows in new.polygons.items():
        for i,(pts,normal) in enumerate(poly_rows):
            assert np.isfinite(pts).all() and np.isfinite(normal).all()
            normals=new.polygon_normals.get((key,i))
            if normals is not None:assert np.isfinite(normals).all()
    A.configure(new);assert set(new.polygons)<=set(D.MATERIALS)
    for p,v in D.MATERIALS.items():assert new.material_overrides.get(p)==v
    private='Assets/models/maps/ares/pipework-v1'
    fragment=stage/'proof/pipework.obj';fragment.parent.mkdir(parents=True,exist_ok=True)
    K.write_obj(fragment,new,'ares_hall')
    extraction,found=Patch.replace_obj(ROOT/active,stage/active,stage/'proof/retained.obj',lookup,fragment)
    Patch.coverage(found,lookup,polygons);assert extraction['removed_triangles']==2240
    assert original==(ROOT/active).read_bytes()
    # The preview has identical model bytes, material aliases and collision.
    preview=f'{private}/hall_preview.obj'
    (stage/preview).parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(stage/active,stage/preview)
    preview_mtl=f'{private}/{mtllib}';shutil.copy2(ROOT/live_mtl,stage/preview_mtl)
    trial=f'{private}/trial_hall.vmdl'
    updated=raw.replace('filename = "'+active[7:]+'"','filename = "'+preview[7:]+'"',1)
    marker='_class = "PhysicsShapeList"'
    assert raw[raw.index(marker):]==updated[updated.index(marker):]
    (stage/trial).write_text(updated)
    files={}
    for relative in (active,preview,preview_mtl,trial):
        target=ROOT/relative;backup=stage/'before'/relative
        before=Patch.sha(target) if target.exists() else None
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
            assert Patch.sha(backup)==before
        files[relative]={'before':before,'after':Patch.sha(stage/relative),
            'source':(stage/relative).relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}
    for group in (sources,protected):
        for p,h in group.items():assert Patch.sha(ROOT/p)==h,p
    assert (ROOT/DOCUMENT).read_text()==raw,'The live hall document changed; restage from its current imports.'
    result={'revision':'ares-pipework-v1','stage':args.stage,'files':files,
        'source_sha256':sources,'required_source_snippets':snippets,'protected_sha256':protected,
        'active_base':active,'trial_document':trial,'preview_base':preview,'document':DOCUMENT,
        'document_sha256':Patch.sha(ROOT/DOCUMENT),'materials':D.MATERIALS,'runs':reports,
        'new_triangles':new.triangle_count(),'old_triangles':old.triangle_count(),
        'physics_bytes_exact':True,'existing_routes_radii_retained':True,**extraction}
    (stage/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage,'preview':True})+'\n')
    print(json.dumps({'runs':len(reports),'triangles':result['new_triangles'],
        'removed':result['old_triangles'],'live_target':active,'hall_document_is_not_modified':True}),flush=True)


if __name__=='__main__':main()
