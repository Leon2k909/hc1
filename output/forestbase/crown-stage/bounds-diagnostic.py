import sys,json,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
from forestbase_crown_audit import read
root=Path.cwd();base=root/'Assets/models/maps/forestbase/fir';stage=root/'output/forestbase/crown-stage/models/maps/forestbase/fir';rows=[]
for variant in 'abc':
 near=read(base/f'fir_{variant}_lod0.obj',strict=False)
 for level in ('lod1','distant','horizon'):
  old=read(root/'output/forestbase/crown-before/Assets/models/maps/forestbase/fir'/f'fir_{variant}_{level}.obj',strict=False);new=read(stage/f'fir_{variant}_{level}.obj')
  excess=np.maximum(near['mins']-new['mins'],new['maxs']-near['maxs'])
  if excess.max()>.002:rows.append(dict(variant=variant,level=level,nearMin=near['mins'].tolist(),nearMax=near['maxs'].tolist(),oldMin=old['mins'].tolist(),oldMax=old['maxs'].tolist(),newMin=new['mins'].tolist(),newMax=new['maxs'].tolist(),maximumExcess=float(excess.max())))
print(json.dumps(rows))
