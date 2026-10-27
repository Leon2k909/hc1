import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
import forestbase_map as M
out=M.K.ROOT/'output/forestbase/cargo-stage'
models=M.build(visual_chunks=['yard','logistics'])
layout=json.loads((M.K.ROOT/'output/forestbase/layout.json').read_text())
for name in ('yard','logistics'):
 m=models[name];count=M.K.write_model(out/M.RES,M.RES,name,m);layout['stats'][name]=dict(triangles=count,boxes=len(m.boxes),hulls=len(m.hulls))
layout['dm']=M.DM
M.K.write_text(out/'layout.json',json.dumps(layout,indent=2))
scene=json.loads(M.SCENE.read_text());changed=[]
def walk(ns):
 for n in ns:
  if n.get('Name') in ('DM 5','DM 12'):
   i=int(n['Name'].split()[1])-1;pose=M.spawn(n['Name'],f'spawn/dm/{i}',M.DM[i],'Unassigned','deathmatch');n['Position']=pose['Position'];n['Rotation']=pose['Rotation'];changed.append(n['Name'])
  walk(n.get('Children',[]))
walk(scene['GameObjects']);assert len(changed)==2
M.K.write_text(out/'forestbase.scene',json.dumps(scene,indent=2))
print(json.dumps({n:layout['stats'][n] for n in ('yard','logistics')}))
