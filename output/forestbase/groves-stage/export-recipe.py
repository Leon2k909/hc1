import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
import forestbase_forest as F
import map_kit as K
scene=json.loads((K.ROOT/'output/forestbase/groves-before/Assets/scenes/maps/ForestBase/forestbase.scene').read_text())
backdrop=next(n for n in scene['GameObjects'] if n.get('Name')=='Forest Backdrop')
items=[]
for n in backdrop['Children']:
 r=next(c for c in n['Components'] if c['__type']=='Sandbox.ModelRenderer');p=list(map(float,n['Position'].split(',')));q=list(map(float,n['Rotation'].split(',')));items.append((n['Name'],r['Model'],(-p[1],p[0],p[2]),math.degrees(2*math.atan2(q[2],q[3])),tuple(map(float,n['Scale'].split(',')))))
changed=[]
for n,item in zip(backdrop['Children'],F.regroup(items)):
 p=K.vec(K.to_world(item[2]))
 if n['Position']!=p:changed.append(n['Name']);n['Position']=p
out=K.ROOT/'output/forestbase/groves-stage'
K.write_text(out/'forestbase.scene',json.dumps(scene,indent=2))
K.write_text(out/'changed-names.json',json.dumps(changed,indent=2))
print(json.dumps(dict(moved=len(changed),names=changed)))
