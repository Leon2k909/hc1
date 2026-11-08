from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/ares/west-operator-console-v1'
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='stage':
 sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,ares_west_operator_console as D
 m=json.loads((OUT/'manifest.json').read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 for src,dest in ((ROOT/'Assets'/m['active_base'],before/'original-hall.obj'),(ROOT/'Assets/scenes/maps/Ares/ares.scene',before/'ares.scene')):
  assert not dest.exists(),'Already staged; inspect current installation';shutil.copyfile(src,dest)
 shutil.copyfile(OUT/'stage/Assets/models/props/ares/west_operator_console_v1/preview.obj',stage/'hall_without_console.obj')
 (stage/'node.json').write_text(json.dumps(D.scene_object(K.SceneIds('b03a691a-6728-42bf-8e1c-ff749c62aa61'))))
 (OUT/'install-plan.json').write_text(json.dumps(dict(active_base=m['active_base'],protected=m['protected'],files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}),indent=2))
 text=(ROOT/'Sources/Ares/control-console-native-v1/install.cs.txt').read_text().replace('control-console-native-v1','west-operator-console-v1').replace('control_console_native_v1','west_operator_console_v1').replace('console.vmdl','after.vmdl').replace('Core Process Console','West Control Room Operator Console').replace('dressing_without_console.obj','hall_without_console.obj')
 (HERE/'install.cs.txt').write_text(text)
 text=(HERE/'capture.cs.txt').read_text().replace('output/ares/west-operator-console-v1/native','output/ares/west-operator-console-v1/installed').replace('"ARES transport cases"','"ARES transport cases","West Control Room Operator Console"')
 text=text.replace('cut=Model.Load("models/props/ares/west_operator_console_v1/preview.vmdl")','cut=old')
 start=text.index('  replacement=new GameObject');end=text.index('\n  if(old.IsError',start)
 text=text[:start]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/props/ares/west_operator_console_v1/after.vmdl");replacement.LodOverride=0;'+text[end:]
 text=text.replace('new[]{false,true}','new[]{true}').replace('PreviewOnly=true','Installed=true')
 (HERE/'capture_installed.cs.txt').write_text(text)
 print('Guarded installation staged')
elif sys.argv[1]=='install':print(native.script(HERE/'install.cs.txt'))
elif sys.argv[1]=='compile':print(native.call('asset_compile',dict(path='models/maps/ares/ares_hall.vmdl')))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
