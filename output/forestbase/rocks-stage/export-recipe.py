import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
import forestbase_rocks as R
import map_kit as K
out=K.ROOT/'output/forestbase/rocks-stage'
R.write(out)
shader=out/R.SHADER;shader.parent.mkdir(parents=True,exist_ok=True);shader.write_bytes((K.ASSETS/R.SHADER).read_bytes())
scene=json.loads((K.ASSETS/'scenes/maps/ForestBase/forestbase.scene').read_text())
changed=[];remapped=[]
def visit(nodes):
 for node in nodes:
  name=node.get('Name','')
  if name.startswith('Rock '):
   renderer=next((c for c in node.get('Components',[]) if c.get('__type')=='Sandbox.ModelRenderer'),None)
   if renderer and renderer.get('Model')=='models/maps/forestbase/boulder/cliff.vmdl':
    renderer['Model']=R.MODEL;remapped.append(name)
    seed=int(name.split()[1])
    if R.rim(seed):
     scale=list(map(float,node['Scale'].split(',')));old=scale[2];scale[2]=min(old,math.sqrt(scale[0]*scale[1]))
     if scale[2]<old-.001:node['Scale']=K.vec(scale);changed.append(dict(name=name,before=old,after=scale[2]))
  visit(node.get('Children',[]))
visit(scene['GameObjects'])
K.write_text(out/'forestbase.scene',json.dumps(scene,indent=2))
K.write_text(out/'scene-changes.json',json.dumps(dict(materialRemaps=remapped,loweredRocks=changed),indent=2))
print(json.dumps(dict(materialRemaps=len(remapped),loweredRocks=len(changed),changes=changed)))
