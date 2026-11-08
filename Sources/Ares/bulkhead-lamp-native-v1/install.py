from pathlib import Path
import json,sys,subprocess,os,hashlib
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/ares/bulkhead-lamp-native-v1'
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='lods':
 text=(ROOT/'Sources/Ares/control-console-native-v1/build_lods.py').read_text().replace('control-console-native-v1','bulkhead-lamp-native-v1').replace('control_console_native_v1','bulkhead_lamp_native_v1').replace('console','lamp').replace('Console','Lamp').replace('CONSOLE','LAMP').replace('((1,.23),(2,.075))','((1,.20),(2,.045))')
 (HERE/'build_lods.py').write_text(text)
 env=dict(os.environ)
 for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):env[k]='1'
 with (OUT/'lod-build.log').open('w') as log:
  p=subprocess.Popen(['C:/Program Files/Blender Foundation/Blender 5.1/blender.exe','-b','--factory-startup','--threads','4','--python-exit-code','1','--python',str(HERE/'build_lods.py')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.IDLE_PRIORITY_CLASS)
  try:
   code=p.wait(timeout=180);assert code==0,(OUT/'lod-build.log').read_text()
  finally:
   if p.poll() is None:p.terminate();p.wait(timeout=15)
 print((OUT/'lods.json').read_text())
 m=json.loads((OUT/'manifest.json').read_text());stage=OUT/'stage/Assets';m['files']={p.relative_to(stage).as_posix():sha(p) for p in stage.rglob('*') if p.is_file()};(OUT/'manifest.json').write_text(json.dumps(m,indent=2))
 print(native.script(HERE/'import.cs.txt'))
 print(native.call('asset_compile',dict(path='models/props/ares/bulkhead_lamp_native_v1/lamp.vmdl')))
elif sys.argv[1]=='stage':
 import shutil
 sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,ares_bulkhead_lamp as L
 m=json.loads((OUT/'manifest.json').read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 base=ROOT/'Assets'/m['active_base'];shutil.copyfile(base,before/'original-dressing.obj');shutil.copyfile(ROOT/'Assets/scenes/maps/Ares/ares.scene',before/'ares.scene')
 shutil.copyfile(OUT/'stage/Assets/models/props/ares/bulkhead_lamp_native_v1/preview.obj',stage/'dressing_without_lamp.obj')
 (stage/'node.json').write_text(json.dumps(L.scene_object(K.SceneIds('5b97f85a-1ceb-4fe2-96b2-49eb7e582cb9'))))
 plan=dict(active_base=m['active_base'],protected=m['protected'],files={p.name:sha(p) for p in stage.iterdir() if p.is_file()})
 (OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
 text=(ROOT/'Sources/Ares/control-console-native-v1/install.cs.txt').read_text().replace('control-console-native-v1','bulkhead-lamp-native-v1').replace('control_console_native_v1','bulkhead_lamp_native_v1').replace('console.vmdl','lamp.vmdl').replace('Core Process Console','Lower Hall Bulkhead Lamp').replace('dressing_without_console.obj','dressing_without_lamp.obj').replace('OldFacesRemoved=40','OldFacesRemoved=24')
 (HERE/'install.cs.txt').write_text(text)
 text=(ROOT/'Sources/Ares/control-console-native-v1/capture_installed.cs.txt').read_text().replace('control-console-native-v1','bulkhead-lamp-native-v1').replace('control_console_native_v1','bulkhead_lamp_native_v1').replace('console.vmdl','lamp.vmdl').replace('"Core Process Console"','"Core Process Console","Lower Hall Bulkhead Lamp"')
 text=text.replace('var views=new[]{("player",new Vector3(-540,-290,64),new Vector3(-440,-230,38),50f),("detail",new Vector3(-494,-255,57),new Vector3(-438,-230,40),55f)};', 'var views=new[]{("context",new Vector3(-330,1010,90),new Vector3(-300,1098,119),50f),("detail",new Vector3(-312,1070,119),new Vector3(-300,1098,120),40f)};')
 (HERE/'capture_installed.cs.txt').write_text(text)
 print('Install staged with guards and originals archived outside Assets')
elif sys.argv[1]=='install':
 print(native.script(HERE/'install.cs.txt'))
 print(native.call('asset_compile',dict(path='models/maps/ares/ares_dressing.vmdl')))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
