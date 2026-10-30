"""Prepare matched source-mesh comparisons; CPU render only, two worker threads."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/asset-improvement-20261030/console'
ASSET=ROOT/'Assets/models/props/collider/console-trial-v1'
eye=np.array((4.7,-5.8,4.25));target=np.array((0.,1.35,1.37))
forward=(target-eye)/np.linalg.norm(target-eye);right=np.cross(forward,(0,0,1));right/=np.linalg.norm(right);up=np.cross(right,forward)
limits=[];bounds={}
for name in ('before','after'):
    points=[]
    source=ASSET/(name+'.obj')
    if name=='before' and not source.exists():source=ROOT/'output/collider-console-accepted-20261030/retired-before-resources/before.obj'
    for line in source.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);points.append(np.array((-a,n,z))*.0254)
    points=np.array(points);rel=points-eye;depth=rel@forward;assert depth.min()>0
    x=rel@right/depth;y=rel@up/depth
    limits.extend((18*.88/abs(x).max(),13.5*.88/abs(y).max()))
    bounds[name]={'metreMin':points.min(axis=0).tolist(),'metreMax':points.max(axis=0).tolist()}
lens=float(np.floor(min(75.,*limits)));assert lens>=30
s=(ROOT/'Sources/Collider/equipment-case-trial-v1/render.py').read_text()
s=s.replace("OUT=ROOT/'output/asset-improvement-20261029/equipment-case'","OUT=ROOT/'output/asset-improvement-20261030/console'")
s=s.replace("RESOURCE='models/props/collider/equipment-case-trial-v1'","RESOURCE='models/props/collider/console-trial-v1'")
s=s.replace('output/collider-case-accepted-20261029/retired-before-resources','output/collider-console-accepted-20261030/retired-before-resources')
s=s.replace('scene.cycles.samples=48','scene.cycles.samples=32;scene.cycles.device="CPU"')
s=s.replace('scene.render.threads=4','scene.render.threads=2')
s=s.replace("data.lens=54. if view=='main' else 67.",f'data.lens={lens}')
s=s.replace("views=[('main',(3.5,-4.6,3.3),(0,0,.85)),('detail',(2.25,-3.5,1.85),(.35,-.55,.95))]",
    "views=[('main',"+repr(tuple(eye.tolist()))+','+repr(tuple(target.tolist()))+")]")
s=s.replace("'exposure':0.,'images':[]}","'exposure':0.,'renderDevice':'CPU','threads':2,'idlePriority':True,'images':[]}")
# Larger prop than the earlier equipment case; identical illumination for each variant.
s=s.replace("Vector((0,0,.85))","Vector((0,1.25,1.4))")
s=s.replace("('Key',(-3.2,-3.7,5.5),950,4.0","('Key',(-3.2,-3.7,6.0),1250,4.0")
s=s.replace("('Fill',(4.,-1.0,3.0),620,3.4","('Fill',(4.,-1.0,3.8),850,3.4")
s=s.replace("('Rim',(-.5,3.5,4.8),1150,3.0","('Rim',(-.5,5.5,5.8),1300,3.0")
s=s.replace('for view,eye,target in views:',
    """def source_hash(name):
    path=ASSETS/RESOURCE/(name+'.obj')
    if name=='before' and not path.exists():path=ROOT/'output/collider-console-accepted-20261030/retired-before-resources/before.obj'
    return hashlib.sha256(path.read_bytes()).hexdigest()
report['modelSourceSHA256']={n:source_hash(n) for n in ('before','after')}
for view,eye,target in views:""")
s=s.replace("    for variant,objects in (('before',before),('after',after)):\n",'''    for variant,objects in (('before',before),('after',after)):
        if variant=='before' and '--after-only' in sys.argv:
            previous=json.loads((OUT/'render-report.json').read_text())
            assert all(previous[k]==report[k] for k in ('renderer','samples','viewTransform','exposure','renderDevice','threads'))
            cached=next(i for i in previous['images'] if i['variant']==variant and i['view']==view)
            assert cached['eyeMetres']==list(eye) and cached['targetMetres']==list(target) and cached['lens']==data.lens
            assert cached['width']==scene.render.resolution_x and cached['height']==scene.render.resolution_y
            assert hashlib.sha256((OUT/cached['file']).read_bytes()).hexdigest()==cached['sha256']
            first=json.loads((OUT/'revisions/first-pass/evidence/manifest.json').read_text())
            assert first['models']['before']['meshSHA256']==report['modelSourceSHA256']['before']
            report['images'].append(cached)
            continue
''')
(Path(__file__).parent/'render.py').write_text(s)
(OUT/'framing.json').write_text(json.dumps({'eyeMetres':eye.tolist(),'targetMetres':target.tolist(),
    'lens':lens,'bothMeshesFitWithMargin':True,'bounds':bounds},indent=2)+'\n')
print('Prepared two CPU renders, common '+str(lens)+' mm camera.')
