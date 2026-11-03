from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/railhead/clock-v1';OUT.mkdir(parents=True,exist_ok=True)
old=ROOT/'Sources/ReefHall/pump-v1'
(HERE/'native.py').write_text((old/'native.py').read_text().replace('output/reefhall/pump-v1','output/railhead/clock-v1').replace('reefhall-pump','railhead-clock'))
data=json.loads((ROOT/'Assets/scenes/maps/Railhead/railhead.scene').read_text())
print([n.get('Name') for n in data['GameObjects']])
# The run-time camera setup copies the actual player's effects, and the runner
# starts/stops offline editor play only when this task has to start it.
src=(old/'runtime_review.cs.txt').read_text().replace('output/reefhall/pump-v1/runtime-review','output/railhead/clock-v1/runtime-review').replace('scenes/maps/reefhall/reefhall.scene','scenes/maps/railhead/railhead.scene')
src=src.replace('models/maps/reefhall/reefhall_filter.vmdl','models/maps/railhead/railhead_dress_centre.vmdl').replace('models/maps/reefhall/pump-v1/filter_without_pump.vmdl','models/maps/railhead/clock-v1/dressing_without_clock.vmdl').replace('models/maps/reefhall/pump-v1/circulation_pump.vmdl','models/maps/railhead/clock-v1/station_clock.vmdl').replace('Reef Hall pump review','Railhead clock review')
start=src.index(' var views=new[]');end=src.index(' foreach(var variant in',start)
src=src[:start]+''' var views=new[]{new {Name="front",Eye=new Vector3(1050,-32,242),Target=new Vector3(1110,0,240),Fov=40f},new {Name="side",Eye=new Vector3(1060,-48,239),Target=new Vector3(1110,0,240),Fov=43f}};
'''+src[end:]
(HERE/'runtime_review.cs.txt').write_text(src)
# A baseline version inspects the existing clock before new resources are loaded.
baseline=src
start=baseline.index(' ModelRenderer architecture,');end=baseline.index(' var views=new[]',start)
baseline=baseline[:start]+baseline[end:]
baseline=baseline.replace('new[]{"before","after"}','new[]{"before"}')
start=baseline.index(' architecture.Model=');end=baseline.index(' foreach(var view in views)',start)
baseline=baseline[:start]+baseline[end:]
(HERE/'runtime_baseline.cs.txt').write_text(baseline)
for filename in ('runtime_review.cs.txt','runtime_baseline.cs.txt'):
    path=HERE/filename;s=path.read_text()
    s=s.replace('Game.ActiveScene?.Source?.ResourcePath!="scenes/menu.scene"','Game.ActiveScene?.Source?.ResourcePath!="scenes/maps/railhead/railhead.scene"')
    s=s.replace('Runtime check requires offline menu play, with editor lobby disabled','Runtime check requires offline Railhead play, with editor lobby disabled')
    s=s.replace(' Game.ActiveScene.Load(map);',' if(map==null)throw new InvalidOperationException("Railhead scene resource is missing");')
    start=s.index('} finally {')
    s=s[:start]+'''} finally {
 System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"restored.json"),System.Text.Json.JsonSerializer.Serialize(new{RuntimeOnly=true,SavedSceneUnchanged=true}));
}
'''
    path.write_text(s)
