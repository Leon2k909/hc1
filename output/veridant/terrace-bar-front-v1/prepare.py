from pathlib import Path
import sys,json
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,veridant_map as V,veridant_terrace_bar_front as B
OUT=ROOT/'output/veridant/terrace-bar-front-v1';RESOURCE='models/maps/veridant/terrace-bar-front-v1'
m=K.Model();m.uv_source_name='veridant_buildings';B.build_into(m);V.configure(m);K.write_model(OUT/'stage'/RESOURCE,RESOURCE,'front',m)
original=K.Model();original.uv_source_name='veridant_buildings'
V.P.bar_counter(original,(-100,-14),(100,14),0,front='-n');V.configure(original)
old='models/props/shared/terrace_bar_original_v1';K.write_model(OUT/'stage'/old,old,'bar_original',original)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/terrace-bar-front');ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var stage=System.IO.Path.Combine(root,"output/veridant/terrace-bar-front-v1/stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories)){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;'''
p=ex/'import.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}));(OUT/'compile.json').write_text(json.dumps({'path':RESOURCE+'/front.vmdl','full':True}));(OUT/'original-compile.json').write_text(json.dumps({'path':old+'/bar_original.vmdl','full':True}));(OUT/'spawn.json').write_text(json.dumps({'model':RESOURCE+'/front.vmdl','name':'Terrace bar timber front','position':'0,0,0'}))
(OUT/'before.png').write_bytes(Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.06.13.39.39.png').read_bytes())
print(m.triangle_count())
