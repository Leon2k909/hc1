from pathlib import Path
import sys,math,json,hashlib,collections
R=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(R/'Tools'));sys.path.insert(0,str(R/'Sources/CerroBlanco/gallery-vase-v1'))
from build import keys
import map_kit as K,cerroblanco_display_vase as V
from cerroblanco_bollards_upgrade import split_obj,remap_faces
O=R/'output/cerroblanco/all-vases';O.mkdir(exist_ok=True)
places=[(-900,1350,40),(1820,350,40),(-560,-1400,40),(-560,-1950,40)]+[(313+230*math.cos(math.radians(a)),1200+230*math.sin(math.radians(a)),44) for a in (135,315)]
old=K.Model();new=K.Model()
for e,n,z in places:
 old.cylinder((e,n),6,z,z+14,{'side':'cb_red','top':'cb_black','bottom':None},sides=12);V.build_into(new,e,n,z)
old.tile_overrides.update({'cb_red':64.,'cb_black':64.});K.write_obj(O/'old.obj',old,'old');K.write_obj(O/'new.obj',new,'new')
S=R/'Assets/models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj';raw=S.read_bytes();(O/'before.obj').write_bytes(raw)
targets=collections.Counter(keys(O/'old.obj'));lines,vs,uvs,ns=split_obj(raw.decode());it=iter(keys(S));kept=[];removed=0
for l in lines:
 if l.startswith('f '):
  key=next(it)
  if targets[key]:targets[key]-=1;removed+=1;continue
 kept.append(l)
assert removed==204 and not any(targets.values())
fresh,nv,nt,nn=split_obj((O/'new.obj').read_text());merged=kept+[l for l in fresh if l.startswith('v ')]+nt+nn+remap_faces(fresh,len(vs),len(uvs),len(ns))
(O/'after.obj').write_text('\n'.join(merged)+'\n')
assert collections.Counter(keys(O/'after.obj'))==collections.Counter(keys(S))-collections.Counter(keys(O/'old.obj'))+collections.Counter(keys(O/'new.obj'))
plan={'before_sha256':hashlib.sha256(raw).hexdigest(),'replaced':6,'placements':places,'removed_triangles':removed,'added_triangles':new.triangle_count()};(O/'plan.json').write_text(json.dumps(plan,indent=2))
code='var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/cerroblanco/all-vases");var p=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(o,"plan.json")));var dest=System.IO.Path.Combine(root,"Assets/models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj");if(Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(dest))).ToLowerInvariant()!=p["before_sha256"].GetValue<string>())throw new Exception("Source changed");System.IO.File.Copy(System.IO.Path.Combine(o,"after.obj"),dest,true);Editor.AssetSystem.RegisterFile(dest);return new{Replaced=6};'
(O/'install.json').write_text(json.dumps({'code':code}))
f=R/'Tools/cerroblanco_parts.py';s=f.read_text();a=s.index('    if thing == "vase":');b=s.index('    elif thing:',a);s=s[:a]+'    if thing == "vase":\n        from cerroblanco_display_vase import build_into\n        build_into(m,e,n,h)\n'+s[b:];f.write_text(s)
print(plan)
