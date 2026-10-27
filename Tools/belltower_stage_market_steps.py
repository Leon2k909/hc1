"""Replace only the installed market-cross steps; retain every other civic prop."""
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import belltower_market_steps as M
import belltower_stone_wear as W
import belltower_stage_stone_wear as S

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/market-steps-v2'
DOC='Assets/models/maps/belltower/belltower_centre.vmdl'
EDGE='Assets/models/maps/belltower/edge-realism-v1/centre.obj'
CANON='Assets/models/maps/belltower/belltower_centre.obj'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def old_steps(path):
    vertices={};paint=None;wanted={};faces=[]
    for line in path.open('rb'):
        if line.startswith(b'v '):vertices[len(vertices)+1]=S.point(line[2:].decode())
        elif line.startswith(b'usemtl '):paint=line.split()[1]
        elif line.startswith(b'f ') and paint==b'fountain_limestone':
            pts=[vertices[int(t.split(b'/')[0])] for t in line.split()[1:]]
            if all(abs(p[0])<=100100 and -100<=p[1]<=36100 and abs(p[2]-1275000)<=100100 for p in pts):
                key=(paint,frozenset(pts));assert key not in wanted
                wanted[key]=len(faces);faces.append((paint,pts))
    assert len(faces)>1000,'Expected the complete currently installed stone treads.'
    return wanted,faces


def main():
    stage=OUT/'stage-v1';stage.mkdir(parents=True,exist_ok=False)
    document=(ROOT/DOC).read_bytes();raw=document.decode()
    assert 'models/maps/belltower/edge-realism-v1/centre.obj' in raw
    assert M.STONE not in raw,'Already installed.'
    model=K.Model();report=M.build(model,(0.,1275.),'default')
    original=K.Model()
    for r,z0,z1,count in M.TIERS:original.cylinder((0,1275),r,z0,z1,{},sides=8,surface='default',turn=np.pi/8)
    assert len(model.hulls)==len(original.hulls)==3 and not model.boxes
    assert all(np.array_equal(a[0],b[0]) and a[1]==b[1] for a,b in zip(model.hulls,original.hulls))
    fragment=stage/'proof/steps.obj';fragment.parent.mkdir(parents=True)
    K.write_obj(fragment,model,'belltower_centre')
    wanted,old=old_steps(ROOT/EDGE);files={};proofs={}
    def record(relative):
        target=ROOT/relative;path=stage/relative;before=sha(target) if target.exists() else None
        backup=stage/'before'/relative
        if before:backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,backup);assert sha(backup)==before
        files[relative]={'before':before,'after':sha(path),'source':path.relative_to(ROOT).as_posix(),
                         'backup':backup.relative_to(ROOT).as_posix() if before else None}
    for relative in (EDGE,CANON):
        result,found=S.patch(ROOT/relative,stage/relative,wanted,fragment)
        S.coverage(found,wanted,old);assert result['removed_triangles']==len(old)
        proofs[relative]=result;record(relative)
        mtl=relative[:-4]+'.mtl';data=(ROOT/mtl).read_bytes()
        for material in M.MATERIALS:
            if ('newmtl '+material+'\n').encode() not in data.replace(b'\r\n',b'\n'):
                data+=f'\nnewmtl {material}\nKd 1 1 1\nd 1\n'.encode()
        path=stage/mtl;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);record(mtl)
    alias=f'\n{{ from = "{M.STONE}.vmat" to = "{M.MATERIALS[M.STONE]}" }},'
    at=raw.index('[',raw.index('remaps ='))+1;updated=raw[:at]+alias+raw[at:]
    marker='_class = "PhysicsShapeList"'
    assert raw[raw.index(marker):]==updated[updated.index(marker):]
    (stage/DOC).write_bytes(updated.encode());record(DOC)
    material='Assets/'+M.MATERIALS[M.STONE];path=stage/material;path.parent.mkdir(parents=True)
    text=(ROOT/'Assets/materials/belltower/well-v1/well_cut_stone.vmat').read_text()
    text=text.replace('// Tools/belltower_well.py; unchanged source texture pixels.','// Worn market steps; original CC0 stone texture pixels retained.')
    text=text.replace('[1.04 1.01 .93]','[1.12 1.10 1.04]').replace('g_flPlanterNormal "0.42"','g_flPlanterNormal "0.20"').replace('g_flPlanterRoughness "0.72"','g_flPlanterRoughness "0.82"')
    path.write_text(text);record(material)
    imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',raw)
    protected=['Assets/'+p for p in imports if 'Assets/'+p!=EDGE]
    protected+=['Assets/scenes/maps/Belltower/belltower.scene','Assets/materials/belltower/well-v1/well_cut_stone.vmat',
        'Assets/materials/belltower/well-v1/well_mortar.vmat']
    protected+=[p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/materials/belltower/scans').glob('medieval_blocks_03*')]
    sources=['Tools/belltower_market_steps.py','Tools/belltower_stage_market_steps.py','Tools/belltower_stone_wear.py',
        'Tools/belltower_stone_chips.py','Tools/map_kit.py','Tools/belltower_planters.py']
    before_faces=sum(line.startswith(b'f ') for line in (ROOT/EDGE).open('rb'))
    after_faces=sum(line.startswith(b'f ') for line in (stage/EDGE).open('rb'))
    assert after_faces==before_faces-len(old)+model.triangle_count() and after_faces<65000
    manifest={'revision':'belltower-market-steps-v2','files':files,'geometry_preservation':proofs,
        'protected_sha256':{p:sha(ROOT/p) for p in dict.fromkeys(protected)},'source_sha256':{p:sha(ROOT/p) for p in sources},
        'required_source_snippets':{'Tools/belltower_map.py':[inspect.getsource(S.B.market_cross)]},
        'geometry':report,'removed_step_triangles':len(old),'new_step_triangles':model.triangle_count(),
        'bounded_import_triangles_before':before_faces,'bounded_import_triangles_after':after_faces,
        'physics_bytes_exact':True,'original_collision_hulls_exact':True,'column_and_capital_preserved':True}
    for p,item in files.items():assert (sha(ROOT/p) if (ROOT/p).exists() else None)==item['before'],p
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'compile.json').write_text(json.dumps({'path':DOC[7:],'full':False}))
    (OUT/'compile-material.json').write_text(json.dumps({'path':M.MATERIALS[M.STONE],'full':False}))
    (OUT/'info.json').write_text(json.dumps({'path':DOC[7:]}))
    print(json.dumps({'files':len(files),'blocks':report['blocks'],'old_triangles':len(old),
        'new_triangles':model.triangle_count(),'unrelated_geometry_and_collision_preserved':True}))


if __name__=='__main__':main()
