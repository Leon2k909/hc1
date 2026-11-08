from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/city-light-v1';base=ROOT/'Sources/Railhead/help-point-v1'
(HERE/'native.py').write_text((base/'native.py').read_text().replace('help-point-v1','city-light-v1').replace('railhead-help-point','railhead-lightbox'))
sys.path.insert(0,str(HERE));import native
text=(base/'import.cs.txt').read_text().replace('help-point-v1','city-light-v1').replace('help_point_v1','city_light_v1')
(HERE/'import.cs.txt').write_text(text);print(native.script(HERE/'import.cs.txt'))
for name in ('lightbox','preview','preview_glass'):print(native.call('asset_compile',dict(path=f'models/props/railhead/city_light_v1/{name}.vmdl')))
m=json.loads((OUT/'manifest.json').read_text())
opaque=next(p for p in m['parts'] if p['part']=='opaque');glass=next(p for p in m['parts'] if p['part']=='glass')
text=(base/'capture.cs.txt').read_text().replace('output/railhead/help-point-v1/native','output/railhead/city-light-v1/native').replace('models/maps/railhead/railhead_dress_west.vmdl',opaque['public_model']).replace('models/props/railhead/help_point_v1/preview.vmdl','models/props/railhead/city_light_v1/preview.vmdl').replace('models/props/railhead/help_point_v1/help_point.vmdl','models/props/railhead/city_light_v1/lightbox.vmdl').replace('"East Taxi Rank Head Post"','"East Taxi Rank Head Post","West Platform Help Point","Central Platform PA Speaker"')
text=text.replace('Model old,cut;','Model old,cut,oldGlass,cutGlass;ModelRenderer glazing;').replace('  replacement=new GameObject','  glazing=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="'+glass['public_model']+'");oldGlass=glazing.Model;cutGlass=Model.Load("models/props/railhead/city_light_v1/preview_glass.vmdl");\n  replacement=new GameObject').replace('room.Model=after?cut:old;','room.Model=after?cut:old;glazing.Model=after?cutGlass:oldGlass;')
start=text.index(' var views=');end=text.index('\n foreach(var after',start)
text=text[:start]+''' var views=new[]{("whole",new Vector3(1120,-630,78),new Vector3(1297,-545,69),32f),("detail",new Vector3(1190,-592,83),new Vector3(1297,-545,72),32f)};'''+text[end:]
(HERE/'capture.cs.txt').write_text(text);print(native.script(HERE/'capture.cs.txt'))
