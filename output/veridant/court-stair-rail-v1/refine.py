from pathlib import Path
import sys,json
root=Path.cwd();sys.path.insert(0,str(root/'Tools'))
import map_kit as K,veridant_map as V,veridant_court_stair_rail as B
out=root/'output/veridant/court-stair-rail-v1';res='models/props/shared/veridant_court_stair_rail_v1'
m=K.Model();m.uv_source_name='veridant_buildings';B.build_into(m);V.configure(m);K.write_model(out/'stage'/res,res,'rail',m)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/court-stair-rail/refine.cs')
ex.write_text('''var root=Sandbox.Project.Current.GetRootPath();var rel="models/props/shared/veridant_court_stair_rail_v1";var src=System.IO.Path.Combine(root,"output/veridant/court-stair-rail-v1/stage",rel);foreach(var f in System.IO.Directory.GetFiles(src)){var dst=System.IO.Path.Combine(root,"Assets",rel,System.IO.Path.GetFileName(f));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;''')
(out/'refine.json').write_text(json.dumps({'path':str(ex)}))
