from pathlib import Path
import sys,json
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,veridant_map as V,veridant_fountain_water as B
OUT=ROOT/'output/veridant/fountain-water-v1';RESOURCE='models/maps/veridant/fountain-water-v1'
liner,water=K.Model(),K.Model();B.build_into(liner,water)
for name,m in [('liner',liner),('water',water)]:
    m.uv_source_name='veridant_dress';V.configure(m);K.write_model(OUT/'stage'/RESOURCE,RESOURCE,name,m)
    (OUT/(name+'-compile.json')).write_text(json.dumps({'path':RESOURCE+'/'+name+'.vmdl','full':True}))
    (OUT/(name+'-spawn.json')).write_text(json.dumps({'model':RESOURCE+'/'+name+'.vmdl','name':'Forecourt fountain '+name,'position':'0,0,0'}))
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/fountain-water');ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var stage=System.IO.Path.Combine(root,"output/veridant/fountain-water-v1/stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories)){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;'''
p=ex/'import.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}))
(OUT/'before.png').write_bytes(Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.06.13.56.05.png').read_bytes())
print(liner.triangle_count()+water.triangle_count())
