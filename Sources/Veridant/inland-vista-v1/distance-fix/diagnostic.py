import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RUN=ROOT/'output/veridant/inland-vista-v1/distance-fix'
config=json.loads((RUN/'captures/config.json').read_text())
config['views']=[view for view in config['views'] if view['name']=='user-elevated']
config['folder']='output/veridant/inland-vista-v1/distance-fix/diagnostic-lawn'
config['terrain_material']='materials/veridant/vr_lawn.vmat'
config['stream_frames']=20
(RUN/'diagnostic').mkdir(exist_ok=True)
(RUN/'diagnostic/config.json').write_text(json.dumps(config))
(HERE/'diagnostic.cs.txt').write_text((HERE/'capture.cs.txt').read_text().replace('distance-fix/captures','distance-fix/diagnostic'),encoding='utf-8')
