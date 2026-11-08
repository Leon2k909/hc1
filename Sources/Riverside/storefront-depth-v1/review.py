from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/riverside/storefront-depth-v1';base=ROOT/'Sources/Railhead/help-point-v1'
(HERE/'native.py').write_text((base/'native.py').read_text().replace('railhead/help-point-v1','riverside/storefront-depth-v1').replace('railhead-help-point','riverside-shopfront-review'))
sys.path.insert(0,str(HERE));import native
text=(base/'import.cs.txt').read_text().replace('output/railhead/help-point-v1','output/riverside/storefront-depth-v1').replace('Assets/models/props/railhead/help_point_v1/','Assets/models/props/riverside/storefront_depth_v1/').replace('Assets/materials/railhead/help_point_v1/','Assets/materials/riverside/storefront_depth_v1/')
(HERE/'import.cs.txt').write_text(text);print(native.script(HERE/'import.cs.txt'))
for name in ('windows','preview'):print(native.call('asset_compile',dict(path=f'models/props/riverside/storefront_depth_v1/{name}.vmdl')))
text=(base/'capture.cs.txt').read_text().replace('output/railhead/help-point-v1/native','output/riverside/storefront-depth-v1/native').replace('Assets/scenes/maps/Railhead/railhead.scene','Assets/scenes/maps/Riverside/riverside.scene')
start=text.index('var names=');end=text.index('\nvar roots=',start)
text=text[:start]+'var names=new[]{"Moon","Sky","Fog","Look","Riverside","Lights","Reflection Probes","Volumetric Fog","Porch Lights","Store Ceiling Lights","Interior Drinks Fridges","Store Timber Steps","Shed Downlights","West Yard Fences","Office Entry Doors","Office Rules Signs","T2 Sliding Window Frame","Trailer Entry Doors","Roof Air Conditioners","Streetlight Heads","Pole Insulators","Roof TV Aerials","Trailer Hitches","Passive Roof Vents","Water Tower Tanks"}.ToHashSet(StringComparer.OrdinalIgnoreCase);'+text[end:]
text=text.replace('models/maps/railhead/railhead_dress_west.vmdl','models/maps/riverside/riverside_store.vmdl').replace('models/props/railhead/help_point_v1/preview.vmdl','models/props/riverside/storefront_depth_v1/preview.vmdl').replace('models/props/railhead/help_point_v1/help_point.vmdl','models/props/riverside/storefront_depth_v1/windows.vmdl').replace('old=room.Model;','old=room.Model;room.LodOverride=0;')
start=text.index(' var views=');end=text.index('\n foreach(var after',start)
text=text[:start]+''' var views=new[]{("context",new Vector3(350,-50,100),new Vector3(600,-220,95),65f),("detail",new Vector3(565,-370,85),new Vector3(642,-320,82),58f)};'''+text[end:]
text=text.replace('new Bitmap(view.Item1=="detail"?1000:900,1200)','new Bitmap(1600,1100)')
(HERE/'capture.cs.txt').write_text(text);print(native.script(HERE/'capture.cs.txt'))
