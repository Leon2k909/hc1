"""Remove all courtyard drain geometry; retain the existing continuous paving and collision."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/veridant/courtyard-drains-v1/removed';OUT.mkdir(parents=True,exist_ok=True)
live=ROOT/'Assets/models/maps/veridant/veridant_ground.vmdl';text=live.read_text()
matches=[m for m in re.finditer(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S) if 'name = "courtyard_drain_covers_v1"' in m.group()]
assert len(matches)==1
m=matches[0];after=text[:m.start()]+text[m.end():]
after=re.sub(r'^\{ from = "vr_drain_[^\"]+"[^\n]*\n','',after,flags=re.M)
assert 'covers.obj' not in after and 'ground_without_drains.obj' in after
assert after.split('PhysicsShapeList',1)[1]==text.split('PhysicsShapeList',1)[1]
(OUT/'before.vmdl').write_bytes(live.read_bytes());(OUT/'ground_no_drains.vmdl').write_text(after)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/drain-removal-20261106');ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/courtyard-drains-v1/removed");var live=System.IO.Path.Combine(root,"Assets/models/maps/veridant/veridant_ground.vmdl");if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"before.vmdl")))throw new Exception("Ground model changed since preparation");var tmp=live+".no-drains";System.IO.File.Copy(System.IO.Path.Combine(o,"ground_no_drains.vmdl"),tmp,true);System.IO.File.Move(tmp,live,true);Editor.AssetSystem.RegisterFile(live);return new{DrainsRemoved=true,PavingAndCollisionPreserved=true};'''
p=ex/'remove-drains.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}))
