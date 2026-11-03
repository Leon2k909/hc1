from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
old=ROOT/'Sources/Railhead/clock-v1'
src=(old/'runtime_review.cs.txt').read_text(encoding='utf-8').replace('output/railhead/clock-v1','output/reefhall/server-rack-v1').replace('scenes/maps/railhead/railhead.scene','scenes/maps/reefhall/reefhall.scene').replace('Railhead','Reef Hall')
src=src.replace('models/maps/railhead/railhead_dress_centre.vmdl','models/maps/reefhall/reefhall_control.vmdl').replace('models/maps/railhead/clock-v1/dressing_without_clock.vmdl','models/maps/reefhall/server-rack-v1/control_without_racks.vmdl').replace('models/maps/railhead/clock-v1/station_clock.vmdl','models/maps/reefhall/server-rack-v1/server_racks.vmdl').replace('clock review','server rack review').replace('Candidate pump failed','Candidate racks failed')
start=src.index(' var views=new[]');end=src.index(' foreach(var variant in',start)
src=src[:start]+''' var serviceLights=new System.Collections.Generic.List<GameObject>();
 using(scene.Push())foreach(var e in new[]{2000f,2085f,2170f,2255f}) {
  var lamp=new GameObject(false,"Rack-mounted maintenance lamp");
  lamp.WorldPosition=new Vector3(844,-e,104.5f);
  var light=lamp.Components.Create<PointLight>();light.LightColor=new Color(.85f,.93f,1f)*4;light.Radius=180;light.Shadows=false;
  serviceLights.Add(lamp);
 }
 var views=new[]{new {Name="rack",Eye=new Vector3(610,-2130,70),Target=new Vector3(885,-2130,52),Fov=75f},new {Name="detail",Eye=new Vector3(799,-2030,52),Target=new Vector3(885,-2015,45),Fov=56f}};
'''+src[end:]
src=src.replace(' replacement.GameObject.Enabled=variant=="after";',' replacement.GameObject.Enabled=variant=="after";\n foreach(var lamp in serviceLights)lamp.Enabled=variant=="after";')
src=src.replace('PlayerCount=scene.GetAllComponents<Facepunch.PlayerPawn>().Count(),','PlayerCount=scene.GetAllComponents<Facepunch.PlayerPawn>().Count(),CandidateServiceLights=serviceLights.Count,')
(HERE/'runtime_review.cs.txt').write_text(src,encoding='utf-8')
capture=(old/'capture.py').read_text(encoding='utf-8').replace('scenes/maps/railhead/railhead.scene','scenes/maps/reefhall/reefhall.scene').replace("filename='runtime_baseline.cs.txt' if '--baseline' in sys.argv else 'runtime_review.cs.txt'","filename='runtime_review.cs.txt'")
(HERE/'capture.py').write_text(capture,encoding='utf-8')
verify=(old/'verify.py').read_text(encoding='utf-8').replace('railhead/clock-v1','reefhall/server-rack-v1').replace('dressing_without_clock','control_without_racks').replace('models/maps/railhead/railhead_dress_centre.vmdl','models/maps/reefhall/reefhall_control.vmdl').replace('== 124','== 286').replace('replaced_triangles=124','replaced_triangles=286').replace('scenes/maps/railhead/railhead.scene','scenes/maps/reefhall/reefhall.scene').replace("('front', 'side')","('rack', 'detail')").replace('RAILHEAD / STATION CLOCK','REEF HALL / SERVER RACKS')
verify=verify.replace('matching camera, lighting and exposure','matching camera/exposure · after includes rack service lamps')
verify=verify.replace("assert capture['PlayerCount'] > 0 and not capture['ErrorModels']","assert capture['PlayerCount'] > 0 and not capture['ErrorModels']\nassert capture['CandidateServiceLights'] == 4")
verify=verify.replace('actual_play_mode_checked=True, player_present=True, native_error_models=[],','actual_play_mode_checked=True, player_present=True, native_error_models=[], proposed_rack_service_lights=4,')
(HERE/'verify.py').write_text(verify,encoding='utf-8')
