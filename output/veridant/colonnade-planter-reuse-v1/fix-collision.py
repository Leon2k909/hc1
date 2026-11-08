from pathlib import Path
import re,json
root=Path('C:/sbox-projects/hc1/forked-shooter-main');o=root/'output/veridant/colonnade-planter-reuse-v1';p=root/'Assets/models/maps/veridant/veridant_buildings.vmdl';text=p.read_text();(o/'pre-clearance.vmdl').write_text(text)
nodes=list(re.finditer(r'\{\s*_class = "PhysicsShapeBox".*?\n\s*\},',text,re.S));selected=[]
for node in nodes:
    pos=tuple(map(float,re.search(r'origin = \[([^]]+)\]',node.group())[1].replace(',',' ').split()))
    if pos in [(4,236,11),(36,236,11),(4,214,11),(36,214,11)]:selected.append(node)
assert len(selected)==4,len(selected)
for index,node in reversed(list(enumerate(selected))):
    repl=''
    if index==0:
        repl=re.sub(r'origin = \[[^]]+\]','origin = [ 12.5, 233, 12 ]',node.group())
        repl=re.sub(r'angles = \[[^]]+\]','angles = [ 0, 0, 0 ]',repl)
        repl=re.sub(r'dimensions = \[[^]]+\]','dimensions = [ 47, 42, 24 ]',repl)
        repl=re.sub(r'surface_prop = "[^"]+"','surface_prop = "default"',repl)
    text=text[:node.start()]+repl+text[node.end():]
(o/'clearance.vmdl').write_text(text)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/planter-clearance');ex.mkdir(parents=True,exist_ok=True)
code='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/colonnade-planter-reuse-v1");var live=System.IO.Path.Combine(root,"Assets/models/maps/veridant/veridant_buildings.vmdl");if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"pre-clearance.vmdl")))throw new Exception("Parent changed");System.IO.File.Copy(System.IO.Path.Combine(o,"clearance.vmdl"),live,true);Editor.AssetSystem.RegisterFile(live);return true;'''
f=ex/'fix.cs';f.write_text(code);(o/'collision-import.json').write_text(json.dumps({'path':str(f)}))
