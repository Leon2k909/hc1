from pathlib import Path
import sys,json
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,veridant_map as V,veridant_fountain_coping as B
OUT=ROOT/'output/veridant/fountain-rim-v1';RESOURCE='models/maps/veridant/fountain-rim-v1';dest=OUT/'stage'/RESOURCE
m=K.Model();m.uv_source_name='veridant_buildings';B.build_into(m);V.configure(m);K.write_model(dest,RESOURCE,'coping',m)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/fountain-rim');ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var stage=System.IO.Path.Combine(root,"output/veridant/fountain-rim-v1/stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories)){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;'''
p=ex/'import.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}));(OUT/'compile.json').write_text(json.dumps({'path':RESOURCE+'/coping.vmdl','full':True}));(OUT/'spawn.json').write_text(json.dumps({'model':RESOURCE+'/coping.vmdl','name':'Forecourt fountain coping','position':'0,0,0'}))
(OUT/'before.png').write_bytes(Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.06.13.10.44.png').read_bytes())
print(m.triangle_count())
