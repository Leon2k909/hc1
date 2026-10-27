"""Re-export only shoreline groups; retain the already rebuilt distant Vista."""
import sys,json,math,runpy
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import forestbase_shore as S
import forestbase_cascade as C
STAGE=Path(__file__).resolve().parent
m=K.Model();m.uv_source_name='vista';instances=[]
S.build(m,instances)
partial=STAGE/'shore-only.obj'
K.write_obj(partial,m,'vista')
def parse(path):
    lines=path.read_text().splitlines();indices={t:[] for t in ('v','vt','vn')};groups={};group=None
    for line_index,line in enumerate(lines):
        tag=line.split(' ',1)[0]
        if tag in indices:indices[tag].append(line_index)
        elif tag=='usemtl':group=line.split()[1];groups[group]=[]
        elif tag=='f':groups[group].append([tuple(map(int,item.split('/'))) for item in line.split()[1:]])
    return lines,indices,groups
full_path=STAGE/'models/maps/forestbase/vista.obj'
full,fi,fg=parse(full_path);part,pi,pg=parse(partial)
changed={}
for group in ('shore_bank','shore_rock'):
    assert len(fg[group])==len(pg[group])
    maps=[{} for _ in range(3)]
    for old_face,new_face in zip(fg[group],pg[group]):
        assert len(old_face)==len(new_face)
        for old,new in zip(old_face,new_face):
            for axis in range(3):
                prior=maps[axis].setdefault(old[axis],new[axis]);assert prior==new[axis]
    for axis,tag in enumerate(('v','vt','vn')):
        for a,b in maps[axis].items():full[fi[tag][a-1]]=part[pi[tag][b-1]]
    changed[group]={tag:len(maps[i]) for i,tag in enumerate(('v','vt','vn'))}
K.write_text(full_path,'\n'.join(full)+'\n')
grass=[dict(name=name,model=path,world=K.to_world(pos).tolist(),scale=scale,yaw=yaw)
       for name,path,pos,yaw,scale in instances if name.startswith('Shore grass ')]
(STAGE/'shore-grass.json').write_text(json.dumps(grass,indent=2)+'\n')
all_instances=json.loads((STAGE/'scenery-instances.json').read_text())
by_name={r['name']:r for r in grass}
all_instances=[by_name.get(r['name'],r) for r in all_instances]
(STAGE/'scenery-instances.json').write_text(json.dumps(all_instances,indent=2)+'\n')
triangles=np.array([np.array(points)[list(ids)] for points,normal in m.polygons['shore_bank'] for ids in ((0,1,2),(0,2,3))])
water=C.basin_outline();samples=[]
for a,b in zip(water,water[1:]+water[:1]):samples.extend((a,(a+b)/2))
clearances=[]
for point in samples:
    q=point[:2];mask=np.all(triangles[:,:,:2].min(axis=1)-1e-7<=q,axis=1)&np.all(triangles[:,:,:2].max(axis=1)+1e-7>=q,axis=1)
    hits=[]
    for tri in triangles[mask]:
        v,w=tri[1,:2]-tri[0,:2],tri[2,:2]-tri[0,:2]
        uv=np.linalg.solve(np.stack((v,w),axis=1),q-tri[0,:2])
        if min(uv)>=-1e-6 and sum(uv)<=1.000001:hits.append(float(tri[0,2]+uv[0]*(tri[1,2]-tri[0,2])+uv[1]*(tri[2,2]-tri[0,2])))
    assert hits,('Uncovered pool edge',point)
    clearances.append(max(hits)-point[2])
assert min(clearances)>1,('Water edge floats above bank',min(clearances))
old_cascade=runpy.run_path(str(STAGE.parent/'impact-mist-before-20261020/Tools/forestbase_cascade.py'))
assert np.array_equal(np.array(old_cascade['basin_outline']()),np.array(water)), 'Pool contour changed'
assert len(grass)==24
report=dict(changedGroups=changed,poolEdgeSamples=len(samples),minimumBankOverlapInches=min(clearances),maximumBankOverlapInches=max(clearances),poolContourUnchanged=True,grass=24)
(STAGE/'shore-contact-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
