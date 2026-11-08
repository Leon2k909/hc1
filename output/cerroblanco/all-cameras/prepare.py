from pathlib import Path
import sys,math,json,hashlib,collections
import numpy as np
R=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(R/'Tools'));sys.path.insert(0,str(R/'Sources/CerroBlanco/west-cctv-v1'))
from build import keys
import map_kit as K,cerroblanco_fitout as F,riverdale_camera as C,riverdale_parts as P
from cerroblanco_bollards_upgrade import split_obj,remap_faces
O=R/'output/cerroblanco/all-cameras';O.mkdir(exist_ok=True)
placements=[((2060,715,200),(1,1)),((-1030,-2150,190),(-1,-1)),((1400,-1000,200),(1,-1)),((-1126,1510,200),(-1,1))]
old=K.Model();new=K.Model()
for at,direction in placements:
 F.camera(old,at,direction)
 out=P.unit((*direction,0));anchor=np.array(at,dtype=float)
 class Face:
  def __init__(self):self.out=out;self.a=np.cross((0,0,1),out)
  def p(self,s,z,depth=0):return anchor+self.a*s+np.array((0,0,z))+out*depth
 end=anchor+out*10;target=end+P.unit(out*.85-np.array((0,0,.5)))*100;detail=K.Model();fine=K.Model();C.camera(detail,fine,Face(),0,0,target);new.extend(detail).extend(fine)
old.tile_overrides.update({k:64. for k in old.polygons});K.write_obj(O/'old.obj',old,'old');K.write_obj(O/'new.obj',new,'new')
S=R/'Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj';raw=S.read_bytes();(O/'before.obj').write_bytes(raw)
targets=collections.Counter(keys(O/'old.obj'));lines,vs,uvs,ns=split_obj(raw.decode());it=iter(keys(S));kept=[];removed=0
for l in lines:
 if l.startswith('f '):
  key=next(it)
  if targets[key]:targets[key]-=1;removed+=1;continue
 kept.append(l)
assert removed==232 and not any(targets.values())
fresh,nv,nt,nn=split_obj((O/'new.obj').read_text());merged=kept+[l for l in fresh if l.startswith('v ')]+nt+nn+remap_faces(fresh,len(vs),len(uvs),len(ns));(O/'after.obj').write_text('\n'.join(merged)+'\n')
a=collections.Counter(keys(S));b=collections.Counter(keys(O/'after.obj'));assert b==a-collections.Counter(keys(O/'old.obj'))+collections.Counter(keys(O/'new.obj'))
legacy=collections.Counter(keys(O/'old.obj'))
for path in ('courtyard-cctv-v1','west-cctv-v1'):legacy.update(keys(R/'output/cerroblanco'/path/'original.obj'))
assert not (legacy & b)
plan={'source_sha256':hashlib.sha256(raw).hexdigest(),'remaining_old_cameras_replaced':4,'total_new_cameras':6,'old_camera_triangles_remaining':0,'removed_triangles':removed,'added_triangles':new.triangle_count(),'all_unrelated_faces_preserved':True};(O/'plan.json').write_text(json.dumps(plan,indent=2));print(plan)
code='var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/cerroblanco/all-cameras");var p=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(o,"plan.json")));var dest=System.IO.Path.Combine(root,"Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj");if(Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(dest))).ToLowerInvariant()!=p["source_sha256"].GetValue<string>())throw new Exception("Source changed");System.IO.File.Copy(System.IO.Path.Combine(o,"after.obj"),dest,true);Editor.AssetSystem.RegisterFile(dest);return new{Replaced=4,TotalNew=6,OldRemaining=0};'
(O/'install.json').write_text(json.dumps({'code':code}))
module='''import numpy as np
import map_kit as K
import riverdale_camera as C
import riverdale_parts as P
def build_into(m,at,direction):
    out=P.unit((direction[0],direction[1],0));anchor=np.array(at,dtype=float)
    class Face:
        def __init__(self):self.out=out;self.a=np.cross((0,0,1),out)
        def p(self,s,z,depth=0):return anchor+self.a*s+np.array((0,0,z))+out*depth
    end=anchor+out*10;target=end+P.unit(out*.85-np.array((0,0,.5)))*100
    detail=K.Model();fine=K.Model();C.camera(detail,fine,Face(),0,0,target)
    m.extend(detail).extend(fine)
'''
(R/'Tools/cerroblanco_cctv.py').write_text(module)
f=R/'Tools/cerroblanco_fitout.py';s=f.read_text();a=s.index('def camera( m, at, out ):');b=s.index('\ndef roof_plant(',a);s=s[:a]+'''def camera( m, at, out ):
    """Approved CCTV model at every museum camera placement; no primitive fallback."""
    from cerroblanco_cctv import build_into
    build_into(m,at,out)

'''+s[b:];f.write_text(s)
