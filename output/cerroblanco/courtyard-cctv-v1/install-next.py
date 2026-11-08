from pathlib import Path
import json,hashlib
R=Path('C:/sbox-projects/hc1/forked-shooter-main');O=R/'output/cerroblanco/courtyard-cctv-v1';S=R/'Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj'
p=json.loads((O/'checks.json').read_text());assert hashlib.sha256(S.read_bytes()).hexdigest()==p['source_sha256'];b=O/'installed';b.mkdir(exist_ok=True);(b/'before.obj').write_bytes(S.read_bytes());(b/'before.vmdl').write_bytes(S.with_suffix('.vmdl').read_bytes())
code='var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/cerroblanco/courtyard-cctv-v1");var dest=System.IO.Path.Combine(root,"Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj");System.IO.File.WriteAllText(dest,System.IO.File.ReadAllText(System.IO.Path.Combine(o,"stage/models/maps/cerroblanco/courtyard-cctv-v1/fine.obj")).Replace("mtllib fine.mtl","mtllib cerroblanco_fitout_fine.mtl"));var model=System.IO.Path.ChangeExtension(dest,".vmdl");System.IO.File.WriteAllText(model,System.IO.File.ReadAllText(System.IO.Path.Combine(o,"stage/models/maps/cerroblanco/courtyard-cctv-v1/fine.vmdl")).Replace("models/maps/cerroblanco/courtyard-cctv-v1/fine.obj","models/maps/cerroblanco/cerroblanco_fitout_fine.obj"));Editor.AssetSystem.RegisterFile(dest);Editor.AssetSystem.RegisterFile(model);return new{Installed=true};'
(O/'install.json').write_text(json.dumps({'code':code}))
(R/'Tools/cerroblanco_courtyard_cctv.py').write_text((R/'Sources/CerroBlanco/courtyard-cctv-v1/model.py').read_text())
f=R/'Tools/cerroblanco_fitout.py';s=f.read_text();marker='    """ A security camera on a wall bracket, looking out and down. """';assert marker in s;s=s.replace(marker,marker+'\n    if tuple(at)==(480,-1000,200):\n        from cerroblanco_courtyard_cctv import build\n        m.extend(build());return');f.write_text(s)
d=R/'Sources/CerroBlanco/west-cctv-v1';d.mkdir(exist_ok=True);out=R/'output/cerroblanco/west-cctv-v1';out.mkdir(exist_ok=True)
s=(R/'Sources/CerroBlanco/courtyard-cctv-v1/model.py').read_text().replace('(480.,-1000.,200.)','(-1126.,-160.,200.)').replace('out=P.unit((1,-1,0))','out=P.unit((-1,-1,0))');(d/'model.py').write_text(s)
s=(R/'Sources/CerroBlanco/courtyard-cctv-v1/build.py').read_text().replace('courtyard-cctv-v1','west-cctv-v1').replace('courtyard_cctv_v1','west_cctv_v1').replace('(480,-1000,200),(1,-1)','(-1126,-160,200),(-1,-1)')
# Camera material remaps are already installed; retain them without duplicates.
a=s.index('    import riverdale_camera as C');b=s.index("    (dest/'fine.vmdl')",a);s=s[:a]+s[b:];(d/'build.py').write_text(s)
for n in ['import.json','compile.json','show.json','restore.json']:(out/n).write_text((R/'output/cerroblanco/courtyard-cctv-v1'/n).read_text().replace('courtyard-cctv-v1','west-cctv-v1'))
(out/'capture.py').write_text((R/'output/cerroblanco/courtyard-cctv-v1/capture.py').read_text().replace('-1050,-530,180','-205,1180,180').replace("'angles':'-14,45,0'","'angles':'-14,-50,0'"))
