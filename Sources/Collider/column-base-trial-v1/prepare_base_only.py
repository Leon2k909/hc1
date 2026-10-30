"""Clarify the exact proposed component by hiding the unchanged column in both views."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
import hashlib,json,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
PARENT=ROOT/'output/asset-improvement-20261030/column-base';OUT=PARENT/'base-only-review'
ASSET=ROOT/'Assets/models/props/collider/column-base-trial-v1'
review=json.loads((HERE/'review.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert review['installedInMap'] is False
for path,h in review['proposalSourceSHA256'].items():assert sha(ROOT/path)==h,path
for path,h in review['protectedSourceSHA256'].items():assert sha(ROOT/path)==h,path
eye=np.array((3.9,-4.6,3.4));target=np.array((0.,0.,.33))
forward=(target-eye)/np.linalg.norm(target-eye);right=np.cross(forward,(0,0,1));right/=np.linalg.norm(right);up=np.cross(right,forward)
limits=[];bounds={}
for name in ('before','after'):
    pts=[]
    for line in (ASSET/(name+'.obj')).read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);pts.append((-a*.0254,n*.0254,z*.0254))
    pts=np.array(pts);relative=pts-eye;depth=relative@forward;assert depth.min()>0
    x=relative@right/depth;y=relative@up/depth
    limits.extend((18*.85/abs(x).max(),13.5*.85/abs(y).max()))
    bounds[name]={'metreMin':pts.min(axis=0).tolist(),'metreMax':pts.max(axis=0).tolist()}
lens=float(np.floor(min(75.,*limits)));assert lens>=30
OUT.mkdir(parents=True,exist_ok=True)
s=(HERE/'render.py').read_text()
s=s.replace("OUT=ROOT/'output/asset-improvement-20261030/column-base'","OUT=ROOT/'output/asset-improvement-20261030/column-base/base-only-review'")
assert "context=model('context')" in s
s=s.replace("context=model('context')","context=[]")
s=s.replace("'sameActualColumnContext':True","'sameActualColumnContext':False,'columnHiddenForClarity':True,'contextTrianglesShown':0")
s=s.replace("(OUT/'context/context.obj')","(OUT.parent/'context/context.obj')")
s,n=re.subn(r'^views=.*$',"views=[('base-only',"+repr(tuple(eye.tolist()))+','+repr(tuple(target.tolist()))+")]",s,flags=re.M);assert n==1
s,n=re.subn(r'^    data.lens=[\d.]+$',f'    data.lens={lens}',s,flags=re.M);assert n==1
(HERE/'render_base_only.py').write_text(s)
wrapper=(HERE/'render_low_impact.py').read_text()
wrapper=wrapper.replace('output/asset-improvement-20261030/column-base','output/asset-improvement-20261030/column-base/base-only-review')
wrapper=wrapper.replace("parent/'render.py'","parent/'render_base_only.py'")
assert "'render_base_only.py'" in wrapper
(HERE/'render_base_only_low_impact.py').write_text(wrapper)
(OUT/'framing.json').write_text(json.dumps({'eyeMetres':eye.tolist(),'targetMetres':target.tolist(),'lens':lens,
    'bothBaseMeshesFitWithMargin':True,'columnHiddenInBothVariants':True,'bounds':bounds},indent=2)+'\n')
print('Prepared matched component-only views; all original/proposal sources untouched; '+str(lens)+' mm.')
