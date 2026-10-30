"""Matched close-up of both base meshes under the same actual saved H-column."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/asset-improvement-20261030/column-base'
ASSET=ROOT/'Assets/models/props/collider/column-base-trial-v1'
eye=np.array((3.6,-4.6,3.0));target=np.array((0.,0.,.38))
forward=(target-eye)/np.linalg.norm(target-eye);right=np.cross(forward,(0,0,1));right/=np.linalg.norm(right);up=np.cross(right,forward)
limits=[];bounds={}
for name in ('before','after'):
    points=[]
    for line in (ASSET/(name+'.obj')).read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);points.append(np.array((-a,n,z))*.0254)
    points=np.array(points);rel=points-eye;depth=rel@forward;assert depth.min()>0
    x=rel@right/depth;y=rel@up/depth;limits.extend((18*.84/abs(x).max(),13.5*.84/abs(y).max()))
    bounds[name]={'metreMin':points.min(axis=0).tolist(),'metreMax':points.max(axis=0).tolist()}
lens=float(np.floor(min(75.,*limits)));assert lens>=30
s=(ROOT/'Sources/Collider/equipment-case-trial-v1/render.py').read_text()
s=s.replace("OUT=ROOT/'output/asset-improvement-20261029/equipment-case'","OUT=ROOT/'output/asset-improvement-20261030/column-base'")
s=s.replace("RESOURCE='models/props/collider/equipment-case-trial-v1'","RESOURCE='models/props/collider/column-base-trial-v1'")
s=s.replace("    doc=(directory/(name+'.vmdl')).read_text()\n"+r'''    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc))''',r'''    if name=='context':
        directory=OUT/'context';remaps=json.loads((directory/'materials.json').read_text())
    else:
        doc=(directory/(name+'.vmdl')).read_text()
        remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc))''')
assert "directory=OUT/'context'" in s
s=s.replace("before=model('before');after=model('after')","before=model('before');after=model('after');context=model('context')")
s=s.replace('scene.cycles.samples=48','scene.cycles.samples=32;scene.cycles.device="CPU"')
s=s.replace('scene.render.threads=4','scene.render.threads=2')
s=s.replace('primitive_plane_add(size=200,','primitive_plane_add(size=2000,')
s=s.replace("views=[('main',(3.5,-4.6,3.3),(0,0,.85)),('detail',(2.25,-3.5,1.85),(.35,-.55,.95))]",
    "views=[('main',"+repr(tuple(eye.tolist()))+','+repr(tuple(target.tolist()))+")]")
s=s.replace("data.lens=54. if view=='main' else 67.",f'data.lens={lens}')
s=s.replace('    material_cache[path]=mat', '''    metal_path=keys.get('TextureMetalness','')
    if metal_path and not metal_path.startswith('['):
        img=R.image(metal_path,data=True)
        if img is not None:
            tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=img
            for node in mat.node_tree.nodes:
                if node.type=='BSDF_PRINCIPLED':mat.node_tree.links.new(tex.outputs['Color'],node.inputs['Metallic'])
    material_cache[path]=mat''')
s=s.replace("'exposure':0.,'images':[]}","'exposure':0.,'renderDevice':'CPU','threads':2,'idlePriority':True,'sameActualColumnContext':True,'images':[]}")
s=s.replace('for view,eye,target in views:',
    "report['modelSourceSHA256']={n:hashlib.sha256((ASSETS/RESOURCE/(n+'.obj')).read_bytes()).hexdigest() for n in ('before','after')}\nreport['contextMeshSHA256']=hashlib.sha256((OUT/'context/context.obj').read_bytes()).hexdigest()\nfor view,eye,target in views:")
(Path(__file__).parent/'render.py').write_text(s)
wrapper=(ROOT/'Sources/Collider/console-trial-v1/render_low_impact.py').read_text().replace('output/asset-improvement-20261030/console','output/asset-improvement-20261030/column-base')
(Path(__file__).parent/'render_low_impact.py').write_text(wrapper)
(OUT/'framing.json').write_text(json.dumps({'eyeMetres':eye.tolist(),'targetMetres':target.tolist(),'lens':lens,
    'bothBaseMeshesFitWithMargin':True,'bounds':bounds,'actualColumnContextExtendsAboveCloseup':True},indent=2)+'\n')
print('Prepared matched base close-ups with unchanged actual H-column, '+str(lens)+' mm.')
