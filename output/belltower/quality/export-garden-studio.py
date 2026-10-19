"""Small actual-geometry exports for offline UV and construction review."""
from pathlib import Path
import argparse
import json
import platform
import runpy
import sys
platform._wmi=None
root=Path.cwd()
sys.path.insert(0,str(root/'Tools'))
import numpy as np
import belltower_map as B
import belltower_gardens as G
import building_textures as BT
from map_kit import Model,write_obj

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--revision',choices=('garden-v1','garden-v2','garden-v3'),default='garden-v3')
options=parser.parse_args()
out=root/'output/belltower/quality'/f'{options.revision}-studio'
out.mkdir(parents=True,exist_ok=True)
old=runpy.run_path(str(root/'output/belltower/quality/garden-v1-before/source/belltower_map.py'))
models={}
for name,build in [('shed-before',old['shed']),('shed-after',B.shed)]:
    model=Model()
    build(model,-1440,-1380,-1090,-1030,-48,'+e',np.random.default_rng(2024),True)
    models[name]=model
models['shed-door']=models['shed-after']
model=Model()
B.shed(model,-1840,-1720,-1440,-1340,-48,'+n',np.random.default_rng(2024))
models['large-shed']=model
model=Model()
G.compost_bin(model,-25,25,-25,25,0)
models['compost']=model
model=Model()
G.woodpile(model,-50,50,-15,15,0)
models['firewood']=model
model=Model()
G.wheelbarrow(model,B.Place((0,0,0)))
models['wheelbarrow']=model
records=[]
for name,model in models.items():
    B.Detail.configure(model)
    write_obj(out/(name+'.obj'),model,'belltower_west')
    records.append({'name':name,'triangles':model.triangle_count(),
                    'materials':{paint:model.material_overrides.get(paint,BT.material_path(paint)) for paint in model.polygons}})
(out/'models.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps({'exports':len(records),'directory':str(out)}))
