from pathlib import Path
import json,hashlib,subprocess
R=Path('C:/sbox-projects/hc1/forked-shooter-main');O=R/'output/cerroblanco/cafe-grinder-v1';S=R/'Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj'
p=json.loads((O/'checks.json').read_text());assert hashlib.sha256(S.read_bytes()).hexdigest()==p['source_sha256']
B=O/'installed';B.mkdir(exist_ok=True);(B/'before.obj').write_bytes(S.read_bytes())
code='var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/cerroblanco/cafe-grinder-v1");var dest=System.IO.Path.Combine(root,"Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj");System.IO.File.WriteAllText(dest,System.IO.File.ReadAllText(System.IO.Path.Combine(o,"stage/models/maps/cerroblanco/cafe-grinder-v1/fine.obj")).Replace("mtllib fine.mtl","mtllib cerroblanco_fitout_fine.mtl"));var model=System.IO.Path.ChangeExtension(dest,".vmdl");var text=System.IO.File.ReadAllText(model);var marker="{ from = \\"soil.vmat\\" to = \\"materials/buildings/soil.vmat\\" }";return dest;'
# Native editor imports both approved sources, including the new bean remap.
v=S.with_suffix('.vmdl');(B/'before.vmdl').write_bytes(v.read_bytes())
stage=O/'stage/models/maps/cerroblanco/cafe-grinder-v1'
newmodel=(stage/'fine.vmdl').read_text().replace('models/maps/cerroblanco/cafe-grinder-v1/fine.obj','models/maps/cerroblanco/cerroblanco_fitout_fine.obj')
(B/'approved.vmdl').write_text(newmodel)
code='var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/cerroblanco/cafe-grinder-v1");var dest=System.IO.Path.Combine(root,"Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj");System.IO.File.WriteAllText(dest,System.IO.File.ReadAllText(System.IO.Path.Combine(o,"stage/models/maps/cerroblanco/cafe-grinder-v1/fine.obj")).Replace("mtllib fine.mtl","mtllib cerroblanco_fitout_fine.mtl"));var model=System.IO.Path.ChangeExtension(dest,".vmdl");System.IO.File.Copy(System.IO.Path.Combine(o,"installed/approved.vmdl"),model,true);Editor.AssetSystem.RegisterFile(dest);Editor.AssetSystem.RegisterFile(model);return new{Installed=true};'
(O/'install-approved.json').write_text(json.dumps({'code':code}))
# Generator replaces just the legacy grinder drawing.
t=(R/'Sources/CerroBlanco/cafe-grinder-v1/build.py').read_text();body=t[t.index('def build():'):t.index('\ndef keys(')]
(R/'Tools/cerroblanco_cafe_grinder.py').write_text('import math\nimport numpy as np\nimport map_kit as K\nimport riverdale_parts as P\nPROP="models/props/cerroblanco/cafe_grinder_v1"\nX=(1,0,0);Y=(0,1,0);Z=(0,0,1);AX=(X,Y,Z)\n'+body+'\ndef build_into(m):\n local=build()\n for mat,rows in local.polygons.items():\n  for i,(pts,n) in enumerate(rows):rows[i]=([p+np.array((600,616,42)) for p in pts],n)\n m.extend(local)\n')
f=R/'Tools/cerroblanco_fitout.py';s=f.read_text();a=s.index('    lathe( m, P.BLACK, ( 600.0');b=s.index('    e0, e1 = 628.0',a);s=s[:a]+'    from cerroblanco_cafe_grinder import build_into\n    build_into(m)\n'+s[b:];f.write_text(s)
