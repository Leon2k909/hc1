from pathlib import Path
import sys,json
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,veridant_map as V,veridant_colonnade_planter as B
m=K.Model();m.uv_source_name='veridant_buildings';B.build_into(m);V.configure(m)
res='models/props/shared/colonnade_planter_v1';o=ROOT/'output/veridant/colonnade-planter-reuse-v1';stage=o/'model-update';K.write_model(stage/res,res,'planter',m)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/planter-refine');ex.mkdir(parents=True,exist_ok=True)
code='''var root=Sandbox.Project.Current.GetRootPath();var stage=System.IO.Path.Combine(root,"output/veridant/colonnade-planter-reuse-v1/model-update");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories)){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;'''
p=ex/'import.cs';p.write_text(code);(o/'refine-import.json').write_text(json.dumps({'path':str(p)}))
