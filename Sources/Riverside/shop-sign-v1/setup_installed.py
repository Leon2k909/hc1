from pathlib import Path
p=Path(__file__).parent;root=Path('C:/sbox-projects/hc1/forked-shooter-main')
s=(root/'Sources/Riverside/shelving-v1/runtime-installed.cs.txt').read_text(encoding='utf-8').replace('shelving-review','shop-sign-review').replace('shelving-v1','shop-sign-v1').replace('745,-218,85','310,-320,85').replace('765,-140,47','514,-220,200').replace('FieldOfView=60','FieldOfView=55')
s=s.replace('var original=store.Model;','''var original=store.Model;
var light=scene.GetAllComponents<PointLight>().Single(l=>l.GameObject.Name.StartsWith("store sign") && (l.WorldPosition-new Vector3(454,-220,210)).Length<.25f);
if(MathF.Abs(light.Intensity-.2f)>.0001f)throw new Exception("Saved light was not toned down");''')
(p/'runtime-installed.cs.txt').write_text(s,encoding='utf-8')
s=(root/'Sources/Riverside/shelving-v1/capture_installed.py').read_text(encoding='utf-8')
s=s.replace("call('open_scene',dict(path=status['ActiveScenePath']))","call('open_scene',dict(path='scenes/maps/sewage/sewage.scene'))")
s=s.replace("final[k]==status[k]", "final[k]==dict(status,ActiveScenePath='scenes/maps/sewage/sewage.scene')[k]")
(p/'capture_installed.py').write_text(s,encoding='utf-8')
