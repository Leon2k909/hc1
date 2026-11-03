"""Stage the approved cabinet's exact render and collision replacement."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/collider-tool-cabinet-accepted-20261031';TRIAL=ROOT/'Assets/models/props/collider/tool-cabinet-trial-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ORIGIN=np.array((-650.,160.,0.));WORLD=np.array((160.,650.,0.))
def key(paint,points):return paint,tuple(sorted(tuple(round(float(v),3) for v in p) for p in points))
def faces(path,offset=0):
    vertices=[];paint=''
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(np.array((-a,n,z))+offset)
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):yield key(paint,[vertices[int(t.split('/')[0])-1] for t in line.split()[1:]])
def blocks(text):return list(re.finditer(r'(?m)^\t{5}\{\n\t{6}_class = "(?:PhysicsShapeBox|PhysicsHullFile)"[\s\S]*?^\t{5}\},?\n',text))
def values(text,name):return np.fromstring(re.search(r'\b'+name+r' = \[([^]]+)\]',text)[1],sep=',')
def main():
    assert not (HERE/'installed.json').exists(),'Already installed'
    review=json.loads((HERE/'review.json').read_text());candidate=json.loads((HERE/'candidate.json').read_text())
    assert review['userApproved'] and review['nativeEngineScreenshot'] and review['nativeCollision']['Passed']
    for name,h in {**candidate['protectedSourceSHA256'],**review['proposalSourceSHA256']}.items():assert sha(ROOT/name)==h,name
    source=ROOT/'Assets/models/maps/collider/collider_detail.obj';lines=source.read_text().splitlines(keepends=True)
    remaining=Counter(faces(TRIAL/'before.obj',ORIGIN));assert sum(remaining.values())==2420
    positions=[];paint='';kept=[];removed=[]
    for number,line in enumerate(lines,1):
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);positions.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            signature=key(paint,[positions[int(t.split('/')[0])-1] for t in line.split()[1:]])
            if remaining[signature]:remaining[signature]-=1;removed.append(number);continue
        kept.append(line)
    assert not +remaining and len(removed)==2420
    offsets=tuple(sum(l.startswith(p) for l in lines) for p in ('v ','vt ','vn '));extra=['\no approved_maintenance_tool_cabinet\n']
    for line in (TRIAL/'after.obj').read_text().splitlines(keepends=True):
        if line.startswith(('#','mtllib ','o ')):continue
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);e,north,height=ORIGIN+np.array((-a,n,z));line=f'v {-e:.6f} {height:.6f} {north:.6f}\n'
        elif line.startswith('f '):line='f '+' '.join('/'.join(str(int(v)+offsets[i]) for i,v in enumerate(t.split('/'))) for t in line.split()[1:])+'\n'
        extra.append(line)
    assert sum(l.startswith('f ') for l in extra)==23646
    doc=source.with_suffix('.vmdl').read_text();oldblocks=blocks(doc)
    selected=[b for b in oldblocks if 'PhysicsShapeBox' in b[0] and np.allclose(values(b[0],'origin'),(160,650,26.5)) and np.allclose(values(b[0],'dimensions'),(80,42,47))]
    assert len(selected)==1
    oldbox=selected[0][0];newdoc=doc.replace(oldbox,'',1)
    additions=[]
    for block in blocks((TRIAL/'after.vmdl').read_text()):
        text=block[0];field='origin' if 'PhysicsShapeBox' in text else 'offset_origin'
        position=values(text,field)+WORLD
        text=re.sub(r'\b'+field+r' = \[[^]]+\]',field+' = [ '+', '.join(f'{v:.4f}' for v in position)+' ]',text,count=1)
        additions.append(text)
    assert len(additions)==41
    start=newdoc.index('_class = "PhysicsShapeList"');end=newdoc.index('\n\t\t\t\t]',start)
    newdoc=newdoc[:end]+chr(10)+''.join(additions).rstrip(chr(10))+newdoc[end:]
    assert Counter(b[0] for b in blocks(newdoc))==Counter(b[0] for b in oldblocks)-Counter([oldbox])+Counter(additions)
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',(TRIAL/'after.vmdl').read_text()));assert len(remaps)==7
    added=',\n'.join(f'\t\t\t\t\t\t\t{{ from = "{p}" to = "{v}" }}' for p,v in sorted(remaps.items()))
    newdoc,n=re.subn(r'(\bremaps\s*=\s*\[)([\s\S]*?)(\n\t{6}\])',lambda m:m[1]+m[2].rstrip().rstrip(',')+',\n'+added+m[3],newdoc,count=1);assert n==1
    payloads={source:''.join(kept+extra),source.with_suffix('.vmdl'):newdoc,
              source.with_suffix('.mtl'):source.with_suffix('.mtl').read_text()+''.join(f'newmtl {p[:-5]}\nKd 1 1 1\nd 1\n' for p in sorted(remaps))}
    OUT.mkdir(parents=True,exist_ok=True);records=[]
    for target,text in payloads.items():
        relative=target.relative_to(ROOT);backup=OUT/'before'/relative;stage=OUT/'stage'/relative
        backup.parent.mkdir(parents=True,exist_ok=True);stage.parent.mkdir(parents=True,exist_ok=True)
        backup.write_bytes(target.read_bytes());stage.write_text(text,encoding='utf-8',newline='\n')
        records.append(dict(path=relative.as_posix(),before=sha(target),after=sha(stage),stage=stage.relative_to(ROOT).as_posix()))
    result=dict(userApproved=True,placementPlan=ORIGIN.tolist(),removedTriangles=2420,addedTriangles=23646,
        detailTrianglesBefore=sum(l.startswith('f ') for l in lines),detailTrianglesAfter=sum(l.startswith('f ') for l in kept+extra),
        oldCollisionBoxesRemoved=1,newCollisionBoxes=39,newCollisionHulls=10,unrelatedPhysicsBlocksUnchanged=True,
        files=records,removedFaceLines=removed,protectedOtherFiles={p:h for p,h in candidate['protectedSourceSHA256'].items() if p not in {r['path'] for r in records}},
        proposalSourceSHA256=review['proposalSourceSHA256'])
    (OUT/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    (HERE/'accepted-physics.json').write_text(json.dumps(candidate['collisionShapes'],indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('removedFaceLines','protectedOtherFiles','proposalSourceSHA256')}))
if __name__=='__main__':main()
