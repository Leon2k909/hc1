import sys,json,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
from forestbase_floor_audit import geometry
v,f=geometry(Path('output/forestbase/woodland-relief-stage/models/maps/forestbase/vista.obj'),'forest_soil');t=v[f];n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);s=np.degrees(np.arctan2(np.linalg.norm(n[:,:2],axis=1),n[:,2]));ids=np.argsort(s)[-6:]
print(json.dumps(dict(maxSlope=float(s.max()),minimumZNormal=float(n[:,2].min()),percentiles=np.percentile(s,[50,90,95,99]).tolist(),steepest=[dict(slope=float(s[i]),center=t[i].mean(axis=0).tolist()) for i in ids])))
