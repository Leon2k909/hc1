from pathlib import Path
import json
OUT=Path('C:/sbox-projects/hc1/forked-shooter-main/output/veridant/gallery-frames-v1')
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/gallery-wall-art');ex.mkdir(parents=True,exist_ok=True)
for name,source,expected in [('before','before/parent.vmdl','stage/models/maps/veridant/veridant_buildings.vmdl'),('after','stage/models/maps/veridant/veridant_buildings.vmdl','before/parent.vmdl')]:
    code='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/gallery-frames-v1");var live=System.IO.Path.Combine(root,"Assets/models/maps/veridant/veridant_buildings.vmdl");if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"EXPECTED")))throw new Exception("Parent changed");System.IO.File.Copy(System.IO.Path.Combine(o,"SOURCE"),live,true);Editor.AssetSystem.RegisterFile(live);return true;'''.replace('EXPECTED',expected).replace('SOURCE',source)
    p=ex/(name+'.cs');p.write_text(code);(OUT/(name+'-swap.json')).write_text(json.dumps({'path':str(p)}))
(OUT/'camera.json').write_text(json.dumps({'position':'-400,465,226','angles':'12,180,0'}))
