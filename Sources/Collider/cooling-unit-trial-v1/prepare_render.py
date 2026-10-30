"""One common portrait camera; actual map-ground height, CPU-only matched comparison."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/asset-improvement-20261030/cooling-unit'
ASSET=ROOT/'Assets/models/props/collider/cooling-unit-trial-v1'
eye=np.array((7.,-10.,6.9));target=np.array((0.,1.0,2.6))
forward=(target-eye)/np.linalg.norm(target-eye);right=np.cross(forward,(0,0,1));right/=np.linalg.norm(right);up=np.cross(right,forward)
limits=[];bounds={}
for name in ('before','after'):
    points=[]
    for line in (ASSET/(name+'.obj')).read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);points.append(np.array((-a,n,z))*.0254)
    points=np.array(points);relative=points-eye;depth=relative@forward;assert depth.min()>0
    x=relative@right/depth;y=relative@up/depth
    limits.extend((18*.87/abs(x).max(),24*.87/abs(y).max()))
    bounds[name]={'metreMin':points.min(axis=0).tolist(),'metreMax':points.max(axis=0).tolist()}
lens=float(np.floor(min(85.,*limits)));assert lens>=35
s=(ROOT/'Sources/Collider/equipment-case-trial-v1/render.py').read_text()
s=s.replace("OUT=ROOT/'output/asset-improvement-20261029/equipment-case'","OUT=ROOT/'output/asset-improvement-20261030/cooling-unit'")
s=s.replace("RESOURCE='models/props/collider/equipment-case-trial-v1'","RESOURCE='models/props/collider/cooling-unit-trial-v1'")
s=s.replace('scene.cycles.samples=48','scene.cycles.samples=32;scene.cycles.device="CPU"')
s=s.replace('scene.render.threads=4','scene.render.threads=2')
s=s.replace('resolution_x=1400;scene.render.resolution_y=1050','resolution_x=1050;scene.render.resolution_y=1400')
s=s.replace('data.lens=54.;data.clip_end=1000','data.lens=54.;data.clip_end=1000;data.sensor_fit="HORIZONTAL"')
s=s.replace("data.lens=54. if view=='main' else 67.",f'data.lens={lens}')
s=s.replace("views=[('main',(3.5,-4.6,3.3),(0,0,.85)),('detail',(2.25,-3.5,1.85),(.35,-.55,.95))]",
    "views=[('main',"+repr(tuple(eye.tolist()))+','+repr(tuple(target.tolist()))+")]")
s=s.replace("location=(0,0,-.005)","location=(0,0,-.513)")
s=s.replace("Vector((0,0,.85))","Vector((0,1.0,2.6))")
s=s.replace("('Key',(-3.2,-3.7,5.5),950,4.0","('Key',(-4.,-6.,9.5),2400,4.5")
s=s.replace("('Fill',(4.,-1.0,3.0),620,3.4","('Fill',(6.,-1.,6.5),1600,4.0")
s=s.replace("('Rim',(-.5,3.5,4.8),1150,3.0","('Rim',(-3.,6.,8.5),2400,4.0")
s=s.replace("'exposure':0.,'images':[]}","'exposure':0.,'renderDevice':'CPU','threads':2,'idlePriority':True,'groundPlanZ':0.,'images':[]}")
s=s.replace('for view,eye,target in views:',
    "report['modelSourceSHA256']={n:hashlib.sha256((ASSETS/RESOURCE/(n+'.obj')).read_bytes()).hexdigest() for n in ('before','after')}\nfor view,eye,target in views:")
s=s.replace("    for variant,objects in (('before',before),('after',after)):\n",'''    for variant,objects in (('before',before),('after',after)):
        if variant=='before' and '--after-only' in sys.argv:
            old=json.loads((OUT/'render-report.json').read_text())
            for k in ('renderer','samples','viewTransform','exposure','renderDevice','threads','groundPlanZ'):assert old[k]==report[k]
            assert old['modelSourceSHA256']['before']==report['modelSourceSHA256']['before']
            cached=next(r for r in old['images'] if r['variant']=='before' and r['view']==view)
            assert cached['eyeMetres']==list(eye) and cached['targetMetres']==list(target) and cached['lens']==data.lens
            assert cached['width']==scene.render.resolution_x and cached['height']==scene.render.resolution_y
            assert hashlib.sha256((OUT/cached['file']).read_bytes()).hexdigest()==cached['sha256']
            report['images'].append(cached)
            continue
''')
(Path(__file__).parent/'render.py').write_text(s)
wrapper=(ROOT/'Sources/Collider/console-trial-v1/render_low_impact.py').read_text()
wrapper=wrapper.replace('output/asset-improvement-20261030/console','output/asset-improvement-20261030/cooling-unit')
(Path(__file__).parent/'render_low_impact.py').write_text(wrapper)
(OUT/'framing.json').write_text(json.dumps({'eyeMetres':eye.tolist(),'targetMetres':target.tolist(),'lens':lens,
    'bothMeshesFitWithMargin':True,'groundPlanePlanZ':0,'groundPlaneLocalMetres':-.513,
    'bounds':bounds,'portraitResolution':[1050,1400]},indent=2)+'\n')
print('Prepared common '+str(lens)+' mm camera and CPU-only portrait comparison.')
