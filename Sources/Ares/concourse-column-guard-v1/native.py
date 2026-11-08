from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
text=(ROOT/'Sources/Ares/control-console-native-v1/import.cs.txt').read_text().replace('control-console-native-v1','concourse-column-guard-v1').replace('control_console_native_v1','concourse_column_guard_v1')
text=text.replace('ExistingCandidateReused=true','ExistingMaterialsReused=true')
(HERE/'import.cs.txt').write_text(text)
if '--capture-only' not in sys.argv:
 print(native.script(HERE/'import.cs.txt'))
 for p in ('models/props/ares/concourse_column_guard_v1/guard.vmdl','models/props/ares/concourse_column_guard_v1/preview.vmdl'):print(native.call('asset_compile',dict(path=p)))
text=(ROOT/'Sources/Ares/control-console-native-v1/capture.cs.txt').read_text().replace('control-console-native-v1','concourse-column-guard-v1').replace('control_console_native_v1','concourse_column_guard_v1').replace('console.vmdl','guard.vmdl').replace('"models/maps/ares/ares_dressing.vmdl"','"models/maps/ares/ares_hall.vmdl"').replace('new Vector3(-440,-230,0)','Vector3.Zero').replace('Console review','Column guard review')
text=text.replace('"Ares bounced lighting"','"Ares bounced lighting","Core Process Console","Lower Hall Bulkhead Lamp","West Control Room Display","West Stair Landing Rail","West Control Room Operator Console","ARES transport cases"')
text=text.replace('tone.ExposureCompensation=0','tone.ExposureCompensation=2.2f')
text=text.replace('camera.ZNear=.5f','camera.EnablePostProcessing=true;camera.ZNear=.5f')
text=text.replace('var scene=Scene.CreateEditorScene();','var elapsed=0f;var look=data["GameObjects"].AsArray().Single(n=>n["Name"]?.GetValue<string>()=="Look");var savedTone=look["Components"].AsArray().Single(n=>n["__type"]?.GetValue<string>()=="Sandbox.Tonemapping");savedTone["AutoExposureEnabled"]=true;savedTone["MinimumExposure"]=2.2f;savedTone["MaximumExposure"]=2.2f;var scene=Scene.CreateEditorScene();')
text=text.replace('camera=new GameObject(true,"Review camera").AddComponent<CameraComponent>();','var holder=new GameObject(false,"Review camera");camera=holder.AddComponent<CameraComponent>();camera.IsMainCamera=false;')
text=text.replace('scene.EditorTick(.016f,.016f);','scene.EditorTick(elapsed+=.016f,.016f);')
text=text.replace('scene.EditorTick(elapsed+=.016f,.016f);preRender?.Invoke(scene,null);preCamera?.Invoke(scene,null);\n }','holder.Enabled=true;scene.EditorTick(elapsed+=.016f,.016f);preRender?.Invoke(scene,null);preCamera?.Invoke(scene,null);\n }')
text=text.replace('frame<12','frame<90')
text=text.replace('scene.Deserialize(data);room=', 'scene.Deserialize(data);var inspection=new GameObject(true,"Identical review inspection light");inspection.WorldPosition=new Vector3(-1125,595,75);var key=inspection.AddComponent<PointLight>();key.Radius=240;key.LightColor=new Color(4,3.8f,3.4f);key.Shadows=true;room=')
text=text.replace('PreviewOnly=true,','PreviewOnly=true,IdenticalTemporaryInspectionLight=true,')
text=text.replace('ReusedExistingCandidate=true','PurposeBuiltGuard=true')
text=text.replace('var views=new[]{("player",new Vector3(-540,-290,64),new Vector3(-440,-230,38),50f),("detail",new Vector3(-494,-255,57),new Vector3(-438,-230,40),55f)};', 'var views=new[]{("player",new Vector3(-1146,590,64),new Vector3(-1076,650,18),45f),("detail",new Vector3(-1121,610,36),new Vector3(-1076,650,16),50f)};')
(HERE/'capture.cs.txt').write_text(text);print(native.script(HERE/'capture.cs.txt'))
