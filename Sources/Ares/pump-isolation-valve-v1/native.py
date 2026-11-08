from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/ares/pump-isolation-valve-v1'
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
m=json.loads((OUT/'manifest.json').read_text());text=(ROOT/'Sources/Ares/control-console-native-v1/import.cs.txt').read_text().replace('control-console-native-v1','pump-isolation-valve-v1').replace('control_console_native_v1','pump_isolation_valve_v1')
(HERE/'import.cs.txt').write_text(text)
if '--capture-only' not in sys.argv:
 print(native.script(HERE/'import.cs.txt'));print(native.call('asset_compile',dict(path='models/props/ares/pump_isolation_valve_v1/preview.vmdl')))
text=(ROOT/'Sources/Ares/control-console-native-v1/capture.cs.txt').read_text().replace('control-console-native-v1','pump-isolation-valve-v1').replace('control_console_native_v1','pump_isolation_valve_v1').replace('models/props/ares/pump_isolation_valve_v1/console.vmdl',m['reused_approved_compiled_valve']).replace('"models/maps/ares/ares_dressing.vmdl"','"models/maps/ares/ares_reactor.vmdl"').replace('Console review','Pump valve review')
vec=lambda v:'new Vector3('+','.join(str(float(x))+'f' for x in v)+')'
text=text.replace('new Vector3(-440,-230,0)',vec(m['world_position']));text=text.replace('replacement.LodOverride=0;','replacement.LodOverride=0;replacement.WorldRotation=Rotation.LookAt('+vec(m['world_forward'])+','+vec(m['world_up'])+');')
text=text.replace('"Ares bounced lighting"','"Ares bounced lighting","Core Process Console","Lower Hall Bulkhead Lamp","West Control Room Display","West Stair Landing Rail","West Control Room Operator Console","ARES transport cases"')
c=m['world_wheel_center'];player=[c[0]+72,c[1]-72,64];detail=[c[0]+49.5,c[1],99];target=[m['world_valve_center'][0]+8.4853,m['world_valve_center'][1]-8.4853,92]
text=text.replace('var views=new[]{("player",new Vector3(-540,-290,64),new Vector3(-440,-230,38),50f),("detail",new Vector3(-494,-255,57),new Vector3(-438,-230,40),55f)};', 'var views=new[]{("player",'+vec(player)+','+vec(c)+',48f),("detail",'+vec(detail)+','+vec(target)+',50f)};')
key=[c[0]+56.57,c[1]-56.57,140]
text=text.replace('scene.Deserialize(data);room=','scene.Deserialize(data);var reviewLight=new GameObject(true,"Identical temporary inspection light");reviewLight.WorldPosition='+vec(key)+';var light=reviewLight.AddComponent<PointLight>();light.Radius=240;light.LightColor=new Color(3.5f,3.4f,3.2f);light.Shadows=true;room=')
text=text.replace('PreviewOnly=true,','PreviewOnly=true,IdenticalTemporaryInspectionLight=true,')
text=text.replace('scene.EditorTick(.016f,.016f);','scene.EditorTick(elapsed+=.016f,.016f);').replace('var scene=Scene.CreateEditorScene();','var elapsed=0f;var scene=Scene.CreateEditorScene();').replace('frame<12','frame<45')
(HERE/'capture.cs.txt').write_text(text);print(native.script(HERE/'capture.cs.txt'))
