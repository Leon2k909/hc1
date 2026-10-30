"""Actual saved Collider chair versus an ergonomic operator-chair proposal."""
from pathlib import Path
from collections import Counter
import hashlib
import argparse
import json
import re
import shutil
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_map as M
import collider_operators as O
OUT=ROOT/'output/asset-improvement-20261029/chair'
RESOURCE='models/props/collider/chair-trial-v1';MAT='materials/collider/chair-trial-v1'
DEST=ROOT/'Assets'/RESOURCE;MD=ROOT/'Assets'/MAT
ORIGIN=np.array((1723.,-55.,256.))
ROTATION=np.array(((0.,1.,0.),(-1.,0.,0.),(0.,0.,1.)))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def key(p,points):return p,tuple(sorted(tuple(round(float(v),3) for v in pt) for pt in points))


def baseline():
    raw=K.Model();M.control_desk(raw,1,-55.,256.)
    expected=Counter()
    for paint,polys in raw.polygons.items():
        for ps,n in polys:
            a=np.array(ps)
            if np.all(a[:,0]>=1699.9) and np.all(a[:,0]<=1746.1) and np.all(a[:,1]>=-77.1) and np.all(a[:,1]<=-32.9) and np.all(a[:,2]<=309.1):
                for i in range(1,len(ps)-1):expected[key(paint,[ps[0],ps[i],ps[i+1]])]+=1
    assert sum(expected.values())>50
    remaining=expected.copy();before=K.Model();vs=[];uv=[];ns=[];paint=''
    source=ROOT/'Assets/models/maps/collider/collider_structure.obj'
    for line in source.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);ns.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f ') and paint in ('co_case','co_trim'):
            ids=[[int(v)-1 for v in token.split('/')] for token in line.split()[1:]]
            points=[vs[v] for v,t,n in ids];signature=key(paint,points)
            if remaining[signature]:
                remaining[signature]-=1
                before.polygon(paint,[ROTATION@(p-ORIGIN) for p in points],uv=[uv[t] for v,t,n in ids],normals=[ROTATION@ns[n] for v,t,n in ids])
    assert not +remaining,('Baseline not installed',sum((+remaining).values()),sum(expected.values()))
    before.box((-22.,-23.,0),(22.,23.,52.),None,'metal')
    M.configure(before)
    return before,{'source':source.relative_to(ROOT).as_posix(),'sourceSHA256':sha(source),
        'planChairOrigin':ORIGIN.tolist(),'exactMatchedTriangles':sum(expected.values()),'copiedSavedGeometryUVsNormals':True}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refine',action='store_true');args=parser.parse_args()
    if DEST.exists():
        assert args.refine,'Candidate already exists; use --refine for this owned proposal'
        old=json.loads((OUT/'manifest.json').read_text())
        for p,h in old['protectedSourceSHA256'].items():assert sha(ROOT/p)==h,p
        for name,d in old['models'].items():assert sha(DEST/(name+'.obj'))==d['meshSHA256']
    before,provenance=baseline()
    OUT.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True);MD.mkdir(parents=True,exist_ok=True)
    paths=[ROOT/'Assets/models/maps/collider'/f'collider_{n}{ext}' for n in ('structure','detail') for ext in ('.obj','.mtl','.vmdl')]
    paths.append(ROOT/'Assets/scenes/maps/Collider/collider.scene')
    guards={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    # Reuse the project's uninstalled ergonomic furniture draft in a private scope.
    O.MATERIAL_DIR=MAT
    after=O.transform(O.chair(1),(0,0,0),np.diag((-1.,-1.,1.)))
    # Use a physical face projection on cushion shoulders as well as broad faces.
    # The older XY-only seat UVs collapse at the vertical edge and pinch the weave.
    for index,(points,normal) in enumerate(after.polygons['op_fabric']):
        drop=int(np.argmax(np.abs(normal)));axes=[i for i in range(3) if i!=drop]
        after.polygon_uvs[('op_fabric',index)]=[(p[axes[0]]/6.,p[axes[1]]/6.) for p in points]
    after.box((-22.,-23.,0),(22.,23.,52.),None,'metal')
    for paint in after.polygons:
        after.material_overrides[paint]=f'{MAT}/{paint}.vmat';after.tile_overrides[paint]=O.TILES[paint]
    stage=OUT/'material-stage';O.materials(stage)
    dependencies=set()
    for paint in after.polygons:
        p=stage/(paint+'.vmat');shutil.copyfile(p,MD/p.name)
        for texture in re.findall(r'Texture\w+\s+"([^"]+)"',p.read_text()):
            if texture.startswith(MAT+'/'):dependencies.add(Path(texture).name)
    for name in dependencies:shutil.copyfile(stage/name,MD/name)
    models={}
    for name,model in (('before',before),('after',after)):
        K.write_obj(DEST/(name+'.obj'),model,name);K.write_vmdl(DEST/(name+'.vmdl'),RESOURCE,name,model)
        models[name]={'triangles':model.triangle_count(),'meshSHA256':sha(DEST/(name+'.obj'))}
    for p,h in guards.items():assert sha(ROOT/p)==h,p
    result={'status':'candidate-only-not-installed','editorUsed':False,'engineCompilation':'pending',
        'baseline':provenance,'models':models,'protectedSourceSHA256':guards,'authoredCollisionUnchanged':True,
        'originalCollisionBoxInches':[44,46,52],'existingOperatorDraftReused':True,
        'newDetails':['compressed upholstered cushions and edge welt','separate back shell and spine','height and tilt controls','five-spoke cast base','swivel forks and twin caster wheels','physical fabric UV projection on cushion shoulders'],
        'materialFiles':sorted(p.name for p in MD.iterdir())}
    for p in (OUT/'manifest.json',Path(__file__).parent/'candidate.json'):p.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('protectedSourceSHA256','materialFiles')}))


if __name__=='__main__':main()
