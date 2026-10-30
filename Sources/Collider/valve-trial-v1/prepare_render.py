"""Fit one shared camera around both real valve meshes, with room at every edge."""
from pathlib import Path
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261029/valve'
ASSET=ROOT/'Assets/models/props/collider/valve-trial-v1'
eye=np.array((1.35,-1.85,1.15));target=np.array((0.,-.22,.33))
forward=(target-eye)/np.linalg.norm(target-eye);right=np.cross(forward,(0,0,1));right/=np.linalg.norm(right);up=np.cross(right,forward)
limits=[];bounds={}
for name in ('before','after'):
    points=[]
    path=ASSET/(name+'.obj')
    if name=='before' and not path.exists():path=ROOT/'output/collider-valve-accepted-20261029/retired-before-resources/before.obj'
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);points.append(np.array((-a,n,z))*.0254)
    points=np.array(points);relative=points-eye;depth=relative@forward;assert depth.min()>0
    x=relative@right/depth;y=relative@up/depth
    limits.extend((18.*.86/abs(x).max(),13.5*.86/abs(y).max()))
    bounds[name]={'metreMin':points.min(axis=0).tolist(),'metreMax':points.max(axis=0).tolist()}
lens=float(np.floor(min(70.,*limits)))
assert 30<=lens<=70,lens
s=(ROOT/'Sources/Collider/equipment-case-trial-v1/render.py').read_text()
s=s.replace("OUT=ROOT/'output/asset-improvement-20261029/equipment-case'","OUT=ROOT/'output/asset-improvement-20261029/valve'")
s=s.replace("RESOURCE='models/props/collider/equipment-case-trial-v1'","RESOURCE='models/props/collider/valve-trial-v1'")
s=s.replace('output/collider-case-accepted-20261029/retired-before-resources','output/collider-valve-accepted-20261029/retired-before-resources')
s=s.replace('scene.cycles.samples=48','scene.cycles.samples=32')
s=s.replace('    material_cache[path]=mat',"""    metal_path=keys.get('TextureMetalness','')
    if metal_path and not metal_path.startswith('['):
        img=R.image(metal_path,data=True)
        if img is not None:
            texture=mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=img
            for node in mat.node_tree.nodes:
                if node.type=='BSDF_PRINCIPLED':mat.node_tree.links.new(texture.outputs['Color'],node.inputs['Metallic'])
    material_cache[path]=mat""")
s=s.replace('for view,eye,target in views:',"report['metalnessTexturesSupported']=True\nfor view,eye,target in views:")
s=s.replace("views=[('main',(3.5,-4.6,3.3),(0,0,.85)),('detail',(2.25,-3.5,1.85),(.35,-.55,.95))]",
    "views=[('main',"+repr(tuple(eye.tolist()))+','+repr(tuple(target.tolist()))+")]")
s=s.replace("data.lens=54. if view=='main' else 67.",f"data.lens={lens}")
s=s.replace("    for variant,objects in (('before',before),('after',after)):\n",
    """    for variant,objects in (('before',before),('after',after)):
        if variant=='before' and '--after-only' in sys.argv:
            previous=json.loads((OUT/'render-report.json').read_text())
            assert all(previous[k]==report[k] for k in ('renderer','samples','viewTransform','exposure'))
            cached=next(i for i in previous['images'] if i['variant']==variant and i['view']==view)
            assert cached['eyeMetres']==list(eye) and cached['targetMetres']==list(target) and cached['lens']==data.lens
            assert cached['width']==scene.render.resolution_x and cached['height']==scene.render.resolution_y
            assert hashlib.sha256((OUT/cached['file']).read_bytes()).hexdigest()==cached['sha256']
            report['images'].append(cached)
            continue
""")
(Path(__file__).parent/'render.py').write_text(s)
(OUT/'framing.json').write_text(json.dumps({'eyeMetres':eye.tolist(),'targetMetres':target.tolist(),'lens':lens,'bothMeshesFitWithMargin':True,'bounds':bounds},indent=2)+'\n')
print('Prepared matched full-valve renders at '+str(lens)+' mm.')
