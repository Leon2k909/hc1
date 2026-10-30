"""Add pipe-specific PBR finishes to a compiled and inspected geometry stage."""
import argparse
import inspect
import json
from pathlib import Path
import re
import shutil
import ares_map as A
import ares_pipework as D
import ares_pipework_materials as M
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ares/pipework-v1'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--from-stage',required=True)
    ap.add_argument('--stage',required=True);args=ap.parse_args()
    assert all(re.fullmatch(r'stage-[a-z0-9-]+',s) for s in (args.from_stage,args.stage))
    cached=OUT/args.from_stage;cache=json.loads((cached/'manifest.json').read_text())
    stage=OUT/args.stage;stage.mkdir(parents=True,exist_ok=False)
    active=cache['active_base'];item=cache['files'][active]
    assert Patch.sha(ROOT/active)==item['before'],'Live base changed; rebuild geometry from its current source.'
    assert Patch.sha(ROOT/item['source'])==item['after']
    assert Patch.sha(ROOT/'Sources/Ares/pipework-v1/geometry-before-materials.py')==cache['source_sha256']['Tools/ares_pipework.py']
    retained=(cached/'proof/retained.obj').read_bytes();combined=(ROOT/item['source']).read_bytes()
    assert Patch.sha(cached/'proof/retained.obj')==cache['retained_bytes_sha256']
    assert combined.startswith(retained)
    suffix=combined[len(retained):];retagged=[]
    for line in suffix.splitlines(keepends=True):
        if line.startswith(b'usemtl '):
            paint=line.split()[1].decode();assert paint in D.PAINTS
            line=b'usemtl '+D.PAINTS[paint].encode()+b'\n'
        retagged.append(line)
    new_suffix=b''.join(retagged)
    assert [s for s in suffix.splitlines() if not s.startswith(b'usemtl ') ]==[
            s for s in new_suffix.splitlines() if not s.startswith(b'usemtl ')]
    (stage/active).parent.mkdir(parents=True,exist_ok=True)
    (stage/active).write_bytes(retained+new_suffix)
    (stage/'proof').mkdir();(stage/'proof/retained.obj').write_bytes(retained)
    document=cache['document'];raw=(ROOT/document).read_text()
    a,b=span(raw,'_class = "RenderMeshList"')
    imports=re.findall(r'filename = "([^"]+\.obj)"',raw[a:b])
    assert active[7:] in imports
    mtllib=next(line.split(maxsplit=1)[1].decode() for line in retained.splitlines() if line.startswith(b'mtllib '))
    live_mtl=(Path(active).parent/mtllib).as_posix()
    mtl=(ROOT/live_mtl).read_text()
    for paint in D.MATERIALS:
        assert f'newmtl {paint}\n' not in mtl
        mtl+=f'newmtl {paint}\nKd 1 1 1\nd 1\n'
    (stage/live_mtl).write_text(mtl)
    private='Assets/models/maps/ares/pipework-v1'
    preview=f'{private}/hall_preview.obj';preview_mtl=f'{private}/{mtllib}';trial=f'{private}/trial_hall.vmdl'
    (stage/preview).parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(stage/active,stage/preview);(stage/preview_mtl).write_text(mtl)
    updated=raw.replace('filename = "'+active[7:]+'"','filename = "'+preview[7:]+'"',1)
    remaps=''.join(f'\n{{ from = "{p}.vmat" to = "{v}" }},' for p,v in D.MATERIALS.items())
    index=updated.index('[',updated.index('remaps ='))+1
    updated=updated[:index]+remaps+'\n'+updated[index:]
    marker='_class = "PhysicsShapeList"'
    assert raw[raw.index(marker):]==updated[updated.index(marker):]
    (stage/trial).write_text(updated)
    (stage/'before'/document).parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/document,stage/'before'/document)
    material='Assets/materials/ares/pipework-v1';M.write_materials(stage/material)
    files={}
    relatives=[active,live_mtl,preview,preview_mtl,trial]+[p.relative_to(stage).as_posix() for p in sorted((stage/material).iterdir())]
    for relative in relatives:
        target=ROOT/relative;backup=stage/'before'/relative
        before=Patch.sha(target) if target.exists() else None
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
            assert Patch.sha(backup)==before
        files[relative]={'before':before,'after':Patch.sha(stage/relative),
            'source':(stage/relative).relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}
    protected_paths=['Assets/models/maps/ares/ares_hall.obj','Assets/models/maps/ares/ares_hall.mtl',
        'Assets/scenes/maps/Ares/ares.scene','Assets/models/maps/ares/ares_hall_hulls_default.obj',
        'Assets/models/maps/ares/ares_hall_hulls_metal.obj']+['Assets/'+p for p in imports if 'Assets/'+p!=active]
    protected={p:Patch.sha(ROOT/p) for p in dict.fromkeys(protected_paths)}
    source_paths=['Tools/ares_pipework.py','Tools/ares_pipework_materials.py','Tools/ares_finish_pipework.py',
        'Tools/map_kit.py','Tools/riverdale_parts.py','Tools/boxyard_map.py',
        'Sources/Ares/pipework-v1/legacy.py','Sources/Ares/pipework-v1/geometry-before-materials.py']
    result={**cache,'stage':args.stage,'geometry_reused_from':args.from_stage,'files':files,
        'source_sha256':{p:Patch.sha(ROOT/p) for p in source_paths},
        'required_source_snippets':{'Tools/ares_map.py':[inspect.getsource(A.pipe_run),inspect.getsource(A.configure)]},
        'protected_sha256':protected,'active_mtl':live_mtl,'materials':D.MATERIALS,
        'document_sha256':Patch.sha(ROOT/document),'materials_only_geometry_retag':True}
    assert (ROOT/document).read_text()==raw
    for relative,data in files.items():assert (Patch.sha(ROOT/relative) if (ROOT/relative).exists() else None)==data['before']
    (stage/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage,'preview':True})+'\n')
    (OUT/'compile-preview-materials.json').write_text(json.dumps({'calls':[
        {'name':'asset_compile','arguments':{'path':p,'full':False}} for p in D.MATERIALS.values()]+[
        {'name':'asset_compile','arguments':{'path':trial[7:],'full':False}}]}))
    (OUT/'info-materials.json').write_text(json.dumps({'calls':[
        {'name':'asset_info','arguments':{'path':p}} for p in D.MATERIALS.values()]+[
        {'name':'asset_info','arguments':{'path':trial[7:]}},
        {'name':'asset_info','arguments':{'path':document[7:]}}]}))
    print(json.dumps({'stage':args.stage,'private_materials':len(D.MATERIALS),'files':len(files),
        'geometry_identical_to_preview':True,'new_triangles':result['new_triangles']}))

if __name__=='__main__':main()
