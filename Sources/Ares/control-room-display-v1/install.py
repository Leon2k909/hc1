from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/ares/control-room-display-v1'
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='stage':
 sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,ares_control_room_display as D
 m=json.loads((OUT/'manifest.json').read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 shutil.copyfile(ROOT/'Assets'/m['active_base'],before/'original-hall.obj');shutil.copyfile(ROOT/'Assets/scenes/maps/Ares/ares.scene',before/'ares.scene')
 shutil.copyfile(OUT/'stage/Assets/models/props/ares/control_room_display_v1/preview.obj',stage/'hall_without_display.obj')
 (stage/'node.json').write_text(json.dumps(D.scene_object(K.SceneIds('3efea5ac-9403-4371-9a19-9547a94ca369'))))
 (OUT/'install-plan.json').write_text(json.dumps(dict(active_base=m['active_base'],protected=m['protected'],files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}),indent=2))
 text=(ROOT/'Sources/Ares/control-console-native-v1/install.cs.txt').read_text().replace('control-console-native-v1','control-room-display-v1').replace('control_console_native_v1','control_room_display_v1').replace('console.vmdl','display.vmdl').replace('Core Process Console','West Control Room Display').replace('dressing_without_console.obj','hall_without_display.obj').replace('OldFacesRemoved=40','OldFacesRemoved=2').replace('model.IsError||model.MeshInfo.LodCount!=3','model.IsError')
 (HERE/'install.cs.txt').write_text(text)
 text=(HERE/'capture.cs.txt').read_text().replace('output/ares/control-room-display-v1/native','output/ares/control-room-display-v1/installed').replace('"ARES transport cases"','"ARES transport cases","West Control Room Display"')
 text=text.replace('cut=Model.Load("models/props/ares/control_room_display_v1/preview.vmdl")','cut=old')
 start=text.index('  replacement=new GameObject');end=text.index('\n  if(old.IsError',start)
 text=text[:start]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/props/ares/control_room_display_v1/display.vmdl");replacement.LodOverride=0;'+text[end:]
 text=text.replace('new[]{false,true}','new[]{true}').replace('PreviewOnly=true','Installed=true')
 (HERE/'capture_installed.cs.txt').write_text(text)
 print('Guarded installation staged')
elif sys.argv[1]=='install':
 print(native.script(HERE/'install.cs.txt'));print(native.call('asset_compile',dict(path='models/maps/ares/ares_hall.vmdl')))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
