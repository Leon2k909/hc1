from pathlib import Path
import sys,json
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K, veridant_map as V, veridant_parts as P
OUT=ROOT/'output/veridant/lantern-posts-v1/original-retained'
RESOURCE='models/props/shared/terrace_lantern_original_v1'
m=K.Model();m.uv_source_name='veridant_buildings'
P.lantern_post(m,'Reusable original lantern',(0,0,0),96,light=False)
V.configure(m);K.write_model(OUT/'stage'/RESOURCE,RESOURCE,'lantern_original',m)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/lantern-original');ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var stage=System.IO.Path.Combine(root,"output/veridant/lantern-posts-v1/original-retained/stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories)){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;'''
p=ex/'import.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}));(OUT/'compile.json').write_text(json.dumps({'path':RESOURCE+'/lantern_original.vmdl','full':True}))
print(m.triangle_count())
