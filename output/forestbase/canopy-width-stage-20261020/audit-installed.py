import sys,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools'))
import forestbase_map as M
old=json.loads((STAGE.parent/'canopy-width-before-20261020/Assets/scenes/maps/forestbase/forestbase.scene').read_text())
new=json.loads((ROOT/'Assets/scenes/maps/forestbase/forestbase.scene').read_text())
normalized=json.loads((STAGE/'native-prefab-baseline-normalized.json').read_text())
for i,node in enumerate(normalized['GameObjects']):
 assert node['__PrefabIdToInstanceId']==new['GameObjects'][33+i]['__PrefabIdToInstanceId']
 old['GameObjects'][33+i]['__PrefabIdToInstanceId']=node['__PrefabIdToInstanceId']
plan={r['id']:r for r in json.loads((STAGE/'width-plan.json').read_text())}
changed=[]
def walk(a,b):
 assert type(a) is type(b)
 if isinstance(a,dict):
  assert a.keys()==b.keys()
  if a.get('__guid') in plan:
   row=plan[a['__guid']]
   assert a['Name']==row['name'] and b['Name']==row['name']
   aa=np.array(list(map(float,a['Scale'].split(','))));bb=np.array(list(map(float,b['Scale'].split(','))))
   assert np.max(np.abs(bb-np.array(row['after'])))<.00001
   assert bb[2]==aa[2] and np.max(np.abs(bb[:2]/aa[:2]-1.18))<.000001
   a=dict(a);a['Scale']=b['Scale'];changed.append(a['Name'])
  for k in a:walk(a[k],b[k])
 elif isinstance(a,list):
  assert len(a)==len(b)
  for x,y in zip(a,b):walk(x,y)
 else:assert a==b,(a,b)
walk(old,new)
assert len(changed)==444
M.build(visual_chunks=[])
saved=next(n for n in new['GameObjects'] if n.get('Name')=='Forest Backdrop')['Children']
assert len(saved)==len(M.INSTANCES)==620
errors=[];scale_errors=[]
for node,(name,path,pos,yaw,scale) in zip(saved,M.INSTANCES):
 assert node['Name']==name
 model=node['Components'][0]['Model'];assert (model['Path'] if isinstance(model,dict) else model)==path
 errors.append(float(np.max(np.abs(np.array(list(map(float,node['Position'].split(','))))-M.K.to_world(pos)))))
 scale_errors.append(float(np.max(np.abs(np.array(list(map(float,node['Scale'].split(','))))-scale))))
print(json.dumps(dict(positionError=max(errors),scaleError=max(scale_errors),worstScale=saved[int(np.argmax(scale_errors))]["Name"])),flush=True)
# Same 0.001 scale tolerance as the pre-existing scenery audit; the largest error is unchanged Rock 104.
# The independent plan check above still verifies each actual width change to 0.00001.
assert max(errors)<.02 and max(scale_errors)<.001
report=dict(changedTrees=len(changed),allOtherSceneContentUnchangedAfterNativePrefabNormalization=True,regeneratedUnusedPrefabMappings=2,sceneryInstances=len(saved),maximumGeneratorPositionErrorInches=max(errors),maximumGeneratorScaleError=max(scale_errors),sceneSha256=hashlib.sha256((ROOT/'Assets/scenes/maps/forestbase/forestbase.scene').read_bytes()).hexdigest())
(STAGE/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
