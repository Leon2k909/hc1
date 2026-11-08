from pathlib import Path
import json,re,hashlib
root=Path(__file__).resolve().parents[3]; out=root/'output/veridant/sign-v2'
live=root/'Assets/models/maps/veridant/veridant_dress.vmdl'
text=live.read_text()
nodes=list(re.finditer(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S))
matches=[m for m in nodes if 'name = "reception_sign_v2"' in m.group()]
assert len(matches)==1
m=matches[0]; reverted=text[:m.start()]+text[m.end():]
assert reverted.count('models/maps/veridant/sign-v2/dress-without-sign.obj')==1
reverted=reverted.replace('models/maps/veridant/sign-v2/dress-without-sign.obj','models/maps/veridant/chair-v2/dress-base.obj')
(out/'pre-revert.vmdl').write_bytes(live.read_bytes())
(out/'reverted.vmdl').write_text(reverted)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/db605f643da247b3a5b2f1f27ae53518')
ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/sign-v2");var path=System.IO.Path.Combine(root,"Assets/models/maps/veridant/veridant_dress.vmdl");
if(System.IO.File.ReadAllText(path)!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"pre-revert.vmdl"))) throw new Exception("Parent changed since revert preparation");
var temp=path+".revert";System.IO.File.Copy(System.IO.Path.Combine(o,"reverted.vmdl"),temp,true);System.IO.File.Move(temp,path,true);Editor.AssetSystem.RegisterFile(path);return new { Reverted=true };
'''
p=ex/'sign-revert.cs';p.write_text(script);(out/'revert.json').write_text(json.dumps({'path':str(p)}))
