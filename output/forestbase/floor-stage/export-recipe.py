import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
import forestbase_map as M
import forestbase_floor as F
out=M.K.ROOT/'output/forestbase/floor-stage'
out.mkdir(parents=True,exist_ok=True)
(out/'cascade-materials').mkdir(parents=True,exist_ok=True)
import forestbase_cascade as C
original_cascade=C.build
C.build=lambda m:original_cascade(m,material_output=out/'cascade-materials')
models=M.build(visual_chunks=['vista'])
stats=F.write_models(out/M.RES/'floor')
F.material(out/'forest_grass.vmat')
vista=models['vista']
count=M.K.write_model(out/M.RES,M.RES,'vista',vista)
scene=json.loads(M.SCENE.read_text())
backdrop=next(n for n in scene['GameObjects'] if n['Name']=='Forest Backdrop')
oldnames={n['Name'] for n in backdrop['Children']}
added=[]
for i,(name,path,pos,yaw,scale) in enumerate(M.INSTANCES):
 if not name.startswith('Forest floor grass '):continue
 assert name not in oldnames
 node=M.K.game_object(M.IDS,name,f'forest/{i}',M.K.to_world(pos),M.K.yaw_rotation(yaw),scale=M.K.vec(scale),components=[M.component('Sandbox.ModelRenderer',f'forest/{i}/render',Model=path,RenderType='On',Tint='1,1,1,1')])
 backdrop['Children'].append(node);added.append(node['Name'])
M.K.write_text(out/'forestbase.scene',json.dumps(scene,indent=2))
layout=json.loads((M.K.ROOT/'output/forestbase/layout.json').read_text())
layout['stats']['vista']=dict(triangles=count,boxes=len(vista.boxes),hulls=len(vista.hulls))
layout['sceneryInstances']=len(M.INSTANCES);layout['forestFloor']=stats
M.K.write_text(out/'layout.json',json.dumps(layout,indent=2))
print(json.dumps(dict(vista=layout['stats']['vista'],grass=stats,objectsAdded=added)))
