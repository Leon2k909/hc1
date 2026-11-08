from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/help-point-v1'
base=ROOT/'Sources/Railhead/taxi-post-v1'
(HERE/'native.py').write_text((base/'native.py').read_text().replace('taxi-post-v1','help-point-v1').replace('railhead-taxi-post','railhead-help-point'))
sys.path.insert(0,str(HERE));import native
text=(base/'import.cs.txt').read_text().replace('output/railhead/taxi-post-v1','output/railhead/help-point-v1').replace('Assets/models/maps/railhead/taxi-post-v1/','Assets/models/props/railhead/help_point_v1/').replace('Assets/materials/railhead/taxi-post-v1/','Assets/materials/railhead/help_point_v1/')
# This manifest uses paths relative to Assets, whereas the earlier taxi importer used project-relative paths.
text=text.replace('var files=manifest["files"].AsObject();','var files=new System.Text.Json.Nodes.JsonObject();foreach(var pair in manifest["files"].AsObject())files.Add("Assets/"+pair.Key,pair.Value.DeepClone());')
(HERE/'import.cs.txt').write_text(text)
print(native.script(HERE/'import.cs.txt'))
for name in ('help_point','preview'):print(native.call('asset_compile',dict(path=f'models/props/railhead/help_point_v1/{name}.vmdl')))
text=(base/'capture_current.cs.txt').read_text().replace('output/railhead/taxi-post-v1/current-native','output/railhead/help-point-v1/native').replace('models/maps/railhead/railhead_dress_east.vmdl','models/maps/railhead/railhead_dress_west.vmdl').replace('models/maps/railhead/taxi-post-v1/east_without_taxi.vmdl','models/props/railhead/help_point_v1/preview.vmdl').replace('models/maps/railhead/taxi-post-v1/taxi_post.vmdl','models/props/railhead/help_point_v1/help_point.vmdl').replace('"Station Indirect Light"','"Station Indirect Light","East Taxi Rank Head Post"')
start=text.index(' var views=');end=text.index('\n foreach(var after',start)
text=text[:start]+''' var views=new[]{("whole",new Vector3(420,1010,68),new Vector3(378,1154,32),32f),("detail",new Vector3(395,1090,52),new Vector3(378,1154,43),35f)};'''+text[end:]
text=text.replace('view.Item1=="detail"?1200:900','view.Item1=="detail"?1000:900').replace('view.Item1=="detail"?900:1200','1200').replace('ReusedExistingCandidate=true','ExistingMaterialsReused=true')
start=text.index(' var trace=');end=text.index('var info=',start);text=text[:start]+' '+text[end:]
text=text.replace('PlayerFloorHit=trace.Hit,PlayerFloorZ=trace.EndPosition.z,','')
(HERE/'capture.cs.txt').write_text(text)
print(native.script(HERE/'capture.cs.txt'))
