"""Stage the final geometry and lighting without replacing the saved native scene."""
import json
import orion_map as O

models=O.build()
for name in ("orion_west","orion_east","orion_yard","orion_detail","orion_backdrop"):
    m=models[name]
    print(name,O.K.write_model(O.STAGE/O.RESOURCE,O.RESOURCE,name,m),flush=True)
lights=[dict(name=n,position=O.K.vec((p[1],-p[0],p[2])),color=c,radius=r,shadows=s) for n,p,c,r,s in O.LIGHTS]
(O.ROOT/"output/orion/final-lights.json").write_text(json.dumps(lights,indent=2))
# Native vista models use the same terrain function as the backdrop source.
import numpy as np
rng=np.random.default_rng(124)
trees=[]
for i in range(320):
    a=rng.uniform(0,np.pi);r=rng.uniform(3200,13500);e,n=np.cos(a)*r,np.sin(a)*r
    fade=np.clip((r-2400)/4500,0,1)
    broad=1100+450*np.sin(e/2100+n/3300)+350*np.sin(n/1900-e/4200)+180*np.sin(e/700)*np.cos(n/900)
    ridge=abs(np.sin(e/2900+n/4400))*850
    h=-220+fade*(broad+ridge)+np.clip((r-9000)/16000,0,1)*1200
    trees.append(dict(position=O.K.vec((n,-e,h-18)),height=float(rng.uniform(140,330)),yaw=float(rng.uniform(0,360)),variant=i%2))
(O.ROOT/"output/orion/forest.json").write_text(json.dumps(trees,indent=2))
print("Staged",len(lights),"lights and",len(trees),"vista trees")
