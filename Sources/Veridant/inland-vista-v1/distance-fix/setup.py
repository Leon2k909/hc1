"""Prepare isolated native import/capture scripts for this scoped revision."""
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = ROOT / 'output/veridant/inland-vista-v1/distance-fix'
OLD = HERE.parent / 'proportion-fix'
stage = 'stage-v26'
script = re.sub(r'"stage-v\d+"','"'+stage+'"',(HERE/'import.cs.txt').read_text(encoding='utf-8'))
(HERE / 'import.cs.txt').write_text(script, encoding='utf-8')
(HERE / 'capture.cs.txt').write_text((OLD / 'capture.cs.txt').read_text(encoding='utf-8').replace('proportion-fix','distance-fix'), encoding='utf-8')
config = json.loads((ROOT / 'output/veridant/inland-vista-v1/proportion-fix/captures/config.json').read_text())
config['folder'] = 'output/veridant/inland-vista-v1/distance-fix/after-v26'
raw = json.loads((RUN / 'camera-before/get_editor_camera.json').read_text())
camera = json.loads(next(block['text'] for block in raw['content'] if block['type']=='text'))
x,y,z = map(float,camera['Position'].split(','))
pitch,yaw,_ = map(float,camera['Angles'].split(','))
pitch,yaw = math.radians(pitch),math.radians(yaw)
dx,dy,dz = math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),-math.sin(pitch)
view = {'name':'user-latest', 'eye':[-y,x,z],
        'target':[-y-dy*10000,x+dx*10000,z+dz*10000],
        'fov':camera['FieldOfView'], 'width':1536,'height':646}
config['views'].insert(0,view)
(RUN / 'captures').mkdir(parents=True,exist_ok=True)
(RUN / 'captures/config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
for paint in ('vr_inland_vista','vr_inland_vista_b','vr_inland_vista_c','vr_inland_scrub','vr_inland_brush'):
    (RUN / (paint+'.json')).write_text(json.dumps({'path':'materials/veridant/'+paint+'.vmat','full':True}))
(RUN / 'model.json').write_text(json.dumps({'path':'models/maps/veridant/veridant_backdrop.vmdl','full':True}))
print(json.dumps({'stage':stage,'views':len(config['views']),'latest':view},indent=2))
(HERE/'compile-distance.cs.txt').write_text((HERE/'compile-shaders.cs.txt').read_text().replace(', "hc1_veridant_scrub_v3"',''),encoding='utf-8')
