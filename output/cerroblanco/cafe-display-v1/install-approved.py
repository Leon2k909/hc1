from pathlib import Path
import json,hashlib
R=Path('C:/sbox-projects/hc1/forked-shooter-main');O=R/'output/cerroblanco/cafe-display-v1';S=R/'Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj'
p=json.loads((O/'checks.json').read_text());assert hashlib.sha256(S.read_bytes()).hexdigest()==p['source_sha256']
B=O/'installed';B.mkdir(exist_ok=True);(B/'before.obj').write_bytes(S.read_bytes());(B/'before.vmdl').write_bytes(S.with_suffix('.vmdl').read_bytes())
(O/'install-approved.json').write_text(json.dumps({'code':'var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/cerroblanco/cafe-display-v1");var dest=System.IO.Path.Combine(root,"Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj");System.IO.File.WriteAllText(dest,System.IO.File.ReadAllText(System.IO.Path.Combine(o,"stage/models/maps/cerroblanco/cafe-display-v1/fine.obj")).Replace("mtllib fine.mtl","mtllib cerroblanco_fitout_fine.mtl"));Editor.AssetSystem.RegisterFile(dest);return new{Installed=true};'}))
(R/'Tools/cerroblanco_cafe_display.py').write_text((R/'Sources/CerroBlanco/cafe-display-v1/model.py').read_text()+'\ndef build_into(m):\n m.extend(build())\n')
f=R/'Tools/cerroblanco_fitout.py';s=f.read_text();a=s.index('    m.box( ( e0, 604, top )');b=s.index('    rng = np.random.default_rng( 5 )',a);s=s[:a]+'    from cerroblanco_cafe_display import build_into as display_case\n    display_case(m)\n'+s[b:];f.write_text(s)
