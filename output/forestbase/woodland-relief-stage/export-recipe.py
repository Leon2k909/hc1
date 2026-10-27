import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
import forestbase_map as M
import forestbase_cascade as C
import forestbase_floor as F
out=M.K.ROOT/'output/forestbase/woodland-relief-stage'
(out/'materials/forestbase').mkdir(parents=True,exist_ok=True)
original=C.build
C.build=lambda m:original(m,material_output=out/'materials/forestbase')
models=M.build(visual_chunks=['vista'])
count=M.K.write_model(out/M.RES,M.RES,'vista',models['vista'])
F.soil_material(out/F.SOIL_MATERIAL)
scene=json.loads(M.SCENE.read_text());moves=[]
def walk(nodes):
 for node in nodes:
  if node.get('Name','').startswith(('Fir ','Young fir ','Forest middle ','Far fir ','Forest understory ')):
   p=node['Position'].split(',');n,w,z=map(float,p);e=-w
   delta=F.height(e,n)-F.height(e,n,False)
   if abs(delta)>1e-6:
    p[2]=M.K.vec((0,0,z+delta)).split(',')[2];node['Position']=','.join(p);moves.append(dict(name=node['Name'],rise=delta))
  walk(node.get('Children',[]))
walk(scene['GameObjects'])
M.K.write_text(out/'forestbase.scene',json.dumps(scene,indent=2)+'\n')
M.K.write_text(out/'root-shifts.json',json.dumps(moves,indent=2)+'\n')
print(json.dumps(dict(triangles=count,boxes=len(models['vista'].boxes),hulls=len(models['vista'].hulls),movedRoots=len(moves),maxRootRise=max(x['rise'] for x in moves))))
