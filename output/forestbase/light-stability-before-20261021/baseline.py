import sys,json
from pathlib import Path
root=Path("C:/Users/mimi-/Documents/S&box Projects/hc1")
sys.path.insert(0,str(root/'Tools'))
import forestbase_map as F
import map_kit as K
out=Path("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/light-stability-before-20261021")/'generated'
out.mkdir(exist_ok=True)
models=F.build(visual_chunks=['ground','barracks','command'])
for name in ('ground','barracks','command'):
    K.write_obj(out/(name+'.obj'),models[name],name)
    assert (out/(name+'.obj')).read_bytes()==(root/'Assets/models/maps/forestbase'/(name+'.obj')).read_bytes(),name+' baseline differs'
print('All three generated models match the installed baseline.')
