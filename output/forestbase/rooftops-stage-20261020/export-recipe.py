import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
import forestbase_map as M
out=Path("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/rooftops-stage-20261020")
models=M.build(visual_chunks=['barracks','command'])
layout=json.loads((M.K.ROOT/'output/forestbase/layout.json').read_text())
for name in ('barracks','command'):
 m=models[name];count=M.K.write_model(out/M.RES,M.RES,name,m);layout['stats'][name]=dict(triangles=count,boxes=len(m.boxes),hulls=len(m.hulls))
M.K.write_text(out/'layout.json',json.dumps(layout,indent=2))
print(json.dumps({n:layout['stats'][n] for n in ('barracks','command')}))
