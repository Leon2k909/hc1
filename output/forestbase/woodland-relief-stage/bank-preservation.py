import sys,json,collections
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
import map_kit as K
root=Path.cwd();out=root/'output/forestbase/woodland-relief-stage'
def faces(path,paint):
 vs=[];ts=[];ns=[];rows=[];p=None
 for line in path.read_text().splitlines():
  f=line.split()
  if not f:continue
  if f[0]=='v':vs.append(tuple(map(float,f[1:])))
  elif f[0]=='vt':ts.append(tuple(map(float,f[1:])))
  elif f[0]=='vn':ns.append(tuple(map(float,f[1:])))
  elif f[0]=='usemtl':p=f[1]
  elif f[0]=='f' and p==paint:
   refs=[tuple(int(x)-1 for x in v.split('/')) for v in f[1:]]
   rows.append(tuple((vs[v],ts[t],ns[n]) for v,t,n in refs))
 return collections.Counter(rows)
old=faces(root/'output/forestbase/woodland-relief-before/Assets/models/maps/forestbase/vista.obj','mud')
new=faces(out/'models/maps/forestbase/vista.obj','mud');soil=faces(out/'models/maps/forestbase/vista.obj','forest_soil')
assert not new-old,'A bank or other retained mud face changed'
removed=old-new
def horizontal(rows):
 result=collections.Counter()
 for row,count in rows.items():result[tuple((v[0],v[2]) for v,uv,n in row)]+=count
 return result
assert horizontal(removed)==horizontal(soil),'Soil replacement changed its footprint'
shift=K.uv_offset('vista');errors=[]
for row in soil:
 for v,uv,n in row:errors.extend((abs(uv[0]-(-v[0]/92+shift[0])),abs(uv[1]-(v[2]/92+shift[1]))))
assert max(errors)<1e-5,'Discontinuous soil UV projection'
r=dict(allRetainedMudFacesPositionsUvsNormalsExact=True,replacedFloorFootprintExact=True,continuousWorldUvMaximumError=max(errors),retainedFaces=sum(new.values()),replacedFloorFaces=sum(removed.values()))
(out/'bank-preservation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
