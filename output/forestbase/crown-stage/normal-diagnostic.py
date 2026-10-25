import sys,json,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
from forestbase_crown_obj import read_faces
rows=[]
for variant in 'abc':
 p=Path('output/forestbase/crown-stage/models/maps/forestbase/fir')/f'fir_{variant}_lod1.obj'
 for paint,faces in read_faces(p).items():
  normals=np.array([tuple(map(float,n.split())) for row in faces for v,t,n in row]);v=np.array([[tuple(map(float,v.split())) for v,t,n in row] for row in faces]);area=np.linalg.norm(np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=1)
  rows.append(dict(variant=variant,paint=paint,badNormals=int((np.abs(np.linalg.norm(normals,axis=1)-1)>.005).sum()),minimumNormal=float(np.linalg.norm(normals,axis=1).min()),zeroArea=int((area<=1e-12).sum()),minimumDoubleArea=float(area.min())))
print(json.dumps(rows))
