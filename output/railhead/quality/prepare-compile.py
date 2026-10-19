from pathlib import Path
import json
import sys
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'Tools'))
import railhead_map as R
folder=Path(__file__).resolve().parent
files=json.loads((folder/'import.json').read_text())['files']
calls=[{'name':'asset_compile','arguments':{'path':f['path']}} for f in files if f['path'].endswith(('.vmat','.vmdl'))]
(folder/'compile.json').write_text(json.dumps({'calls':calls}),encoding='utf-8')
lights=[{'name':name,'position':R.K.vec(R.K.to_world(position)),'radius':radius} for name,position,colour,radius,shadows in R.lights() if name.startswith('Hall Kiosk ')]
(folder/'hall-lights.json').write_text(json.dumps(lights),encoding='utf-8')
print(len(calls),'asset compiles;',len(lights),'hall lights')
