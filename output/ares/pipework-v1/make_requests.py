from pathlib import Path
import json
import sys
root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root/'Tools'))
import ares_pipework as D
import map_kit as K
out=root/'output/ares/pipework-v1'
requests=[]
for row in D.placements():
    a,b=row['a'],row['b'];e=(a[0]+b[0])/2;n=a[1];z=a[2]
    sign=1 if n>row['wall_n'] else -1
    start=K.to_world((e,n+sign*(row['r']+50),z))
    end=K.to_world((e,row['wall_n']-sign*3,z))
    fmt=lambda p:','.join(f'{x:.5f}' for x in p)
    requests.append({'name':'scene_trace','arguments':{'from':fmt(start),'to':fmt(end)}})
(out/'trace-request.json').write_text(json.dumps({'calls':requests}))
(out/'compile-preview.json').write_text(json.dumps({'path':'models/maps/ares/pipework-v1/trial_hall.vmdl','full':False}))
(out/'compile-live.json').write_text(json.dumps({'path':'models/maps/ares/ares_hall.vmdl','full':False}))
(out/'info-request.json').write_text(json.dumps({'calls':[
    {'name':'asset_info','arguments':{'path':p}} for p in (
        'models/maps/ares/pipework-v1/trial_hall.vmdl','models/maps/ares/ares_hall.vmdl')]}))
print('Prepared 16 comparison rays and native resource requests')
