from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
text=(ROOT/'Sources/Ares/control-console-native-v1/import.cs.txt').read_text().replace('control-console-native-v1','main-airlock-sign-v1').replace('control_console_native_v1','main_airlock_sign_v1');(HERE/'import.cs.txt').write_text(text)
if '--capture-only' not in sys.argv:
 print(native.script(HERE/'import.cs.txt'))
 for p in ('materials/ares/main_airlock_sign_v1/face.vmat','models/props/ares/main_airlock_sign_v1/sign.vmdl','models/props/ares/main_airlock_sign_v1/preview.vmdl'):print(native.call('asset_compile',dict(path=p)))
text=(ROOT/'Sources/Ares/control-console-native-v1/capture.cs.txt').read_text().replace('control-console-native-v1','main-airlock-sign-v1').replace('control_console_native_v1','main_airlock_sign_v1').replace('console.vmdl','sign.vmdl').replace('"models/maps/ares/ares_dressing.vmdl"','"models/maps/ares/ares_hall.vmdl"').replace('new Vector3(-440,-230,0)','Vector3.Zero').replace('Console review','Main airlock sign review')
text=text.replace('"Ares bounced lighting"','"Ares bounced lighting","Core Process Console","Lower Hall Bulkhead Lamp","West Control Room Display","West Stair Landing Rail","West Control Room Operator Console","Northeast Pump Isolation Valve","ARES transport cases"')
text=text.replace('var views=new[]{("player",new Vector3(-540,-290,64),new Vector3(-440,-230,38),50f),("detail",new Vector3(-494,-255,57),new Vector3(-438,-230,40),55f)};', 'var views=new[]{("player",new Vector3(-1010,-75,64),new Vector3(-1398.5f,0,210),55f),("detail",new Vector3(-1220,-75,240),new Vector3(-1398.5f,0,250),43f)};')
text=text.replace('new Bitmap(1200,1000)','new Bitmap(view.Item1=="detail"?1600:1200,view.Item1=="detail"?650:1000)')
text=text.replace('scene.EditorTick(.016f,.016f);','scene.EditorTick(elapsed+=.016f,.016f);').replace('var scene=Scene.CreateEditorScene();','var elapsed=0f;var scene=Scene.CreateEditorScene();').replace('frame<12','frame<90')
(HERE/'capture.cs.txt').write_text(text);print(native.script(HERE/'capture.cs.txt'))
