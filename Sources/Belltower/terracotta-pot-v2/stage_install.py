"""Stage accepted pots, removing only old clay faces and their render imports."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys,tempfile,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_map as B
import belltower_detail as D
import belltower_pots as Pots
import belltower_remove_doorway_posts as Patch
from belltower_move_square_lamps import geometry,sha

OUT=Path(tempfile.gettempdir())/'belltower-terracotta-pot-v2'
STAGE=OUT/'install-stage'
Patch.STAGE=STAGE

def centres(path):
    points=set()
    for line in path.open('rb'):
        if line.startswith(b'v '):
            q=tuple(map(float,line.split()[1:]))
            if abs(q[1])<.001:points.add(q)
    out=[]
    while points:
        pending=[points.pop()];group=[]
        while pending:
            q=pending.pop();group.append(q)
            near={p for p in points if sum((a-b)**2 for a,b in zip(p,q))<225}
            points-=near;pending.extend(near)
        assert len(group)==14
        y,z,x=np.mean(group,axis=0)
        out.append((-round(float(y),3),round(float(x),3),0.))
    return sorted(out)

def remove_import(text,reference):
    marker=text.index('filename = "'+reference+'"')
    start=text.rfind('\n\t\t\t\t\t{',0,marker)+1
    end=text.index('\n\t\t\t\t\t},',marker)+len('\n\t\t\t\t\t},')
    node=text[start:end]
    assert node.count('_class = "RenderMeshFile"')==1 and node.count('filename = ')==1
    return text[:start]+text[end:]

def main():
    STAGE.mkdir(parents=True,exist_ok=False)
    positions=[];files={};protected={}
    for side in ('west','east'):
        clay=ROOT/f'Assets/models/maps/belltower/compiler-safe/{side}/{side}_011_clay_pot.obj'
        cs=centres(clay);assert len(cs)==6
        positions.extend((side,c) for c in cs)
        m=K.Model()
        for c in cs:D.lathe(m,(-c[0],c[1]) if side=='east' else c[:2],0.,[(7.,0.),(9.,15.),(10.2,15.5),(10.2,18.),(9.2,18.),(9.,16.5)],'clay_pot',sides=14)
        if side=='east':m=m.mirrored()
        wanted=geometry(m)
        path=ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        row,found=Patch.render(path,wanted)
        assert wanted==found and row['removed_triangles']==840,(side,sum(found.values()))
        files[path.relative_to(ROOT).as_posix()]=row
        vmdl=path.with_suffix('.vmdl');text=vmdl.read_text();reference=clay.relative_to(ROOT/'Assets').as_posix()
        result=remove_import(text,reference)
        assert reference not in result
        files[vmdl.relative_to(ROOT).as_posix()]=Patch.record(vmdl,result.encode(),{'removed_clay_imports':1,'other_modeldoc_bytes_exact':True})
        for ref in re.findall(r'filename\s*=\s*"([^"]+)"',text):
            p=ROOT/'Assets'/ref
            if p.is_file():protected[p.relative_to(ROOT).as_posix()]=sha(p)
    group=Pots.group(B.ids,positions)
    assert len(group['Children'])==12
    (STAGE/'pots.json').write_text(json.dumps(group,indent=2))
    for p in ['Assets/materials/buildings/clay_pot.vmat','Tools/belltower_map.py','Tools/belltower_pots.py']:
        protected[p]=sha(ROOT/p)
    report={'revision':'belltower-pot-v2-install','files':files,'protected':protected,'scene_before':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),'positions_plan':positions,'group_sha256':sha(STAGE/'pots.json'),'pots':12,'old_triangles_removed':1680}
    (STAGE/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'targets':len(files),'pots':12,'old_triangles_removed':1680,'all_other_geometry_and_physics_preserved':True}))

if __name__=='__main__':main()
