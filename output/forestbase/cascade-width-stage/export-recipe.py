import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
import forestbase_map as M
import forestbase_cascade as C
out=M.K.ROOT/'output/forestbase/cascade-width-stage'
mat=out/'materials/forestbase';mat.mkdir(parents=True,exist_ok=True)
original=C.build
C.build=lambda m:original(m,material_output=mat)
models=M.build(visual_chunks=['vista'])
m=models['vista'];count=M.K.write_model(out/M.RES,M.RES,'vista',m)
layout=json.loads((M.K.ROOT/'output/forestbase/layout.json').read_text())
layout['stats']['vista']=dict(triangles=count,boxes=len(m.boxes),hulls=len(m.hulls))
M.K.write_text(out/'layout.json',json.dumps(layout,indent=2))
print(json.dumps(layout['stats']['vista']))
