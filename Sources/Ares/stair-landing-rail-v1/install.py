from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/ares/stair-landing-rail-v1'
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='stage':
 sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,ares_stair_landing_rail as D
 m=json.loads((OUT/'manifest.json').read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 for source,dest in ((ROOT/'Assets'/m['active_base'],before/'original-hall.obj'),(ROOT/'Assets/scenes/maps/Ares/ares.scene',before/'ares.scene')):
  assert not dest.exists(),'Install already staged; inspect instead of overwriting snapshots'
  shutil.copyfile(source,dest)
 shutil.copyfile(OUT/'stage/Assets/models/props/ares/stair_landing_rail_v1/preview.obj',stage/'hall_without_rail.obj')
 (stage/'node.json').write_text(json.dumps(D.scene_object(K.SceneIds('1f4bf3ed-aa92-42d0-896d-5b74678b1b75'))))
 (OUT/'install-plan.json').write_text(json.dumps(dict(active_base=m['active_base'],protected=m['protected'],files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}),indent=2))
 text=(ROOT/'Sources/Ares/control-console-native-v1/install.cs.txt').read_text().replace('control-console-native-v1','stair-landing-rail-v1').replace('control_console_native_v1','stair_landing_rail_v1').replace('console.vmdl','rail.vmdl').replace('Core Process Console','West Stair Landing Rail').replace('dressing_without_console.obj','hall_without_rail.obj').replace('OldFacesRemoved=40','OldFacesRemoved=84').replace('model.IsError||model.MeshInfo.LodCount!=3','model.IsError')
 (HERE/'install.cs.txt').write_text(text)
 text=(HERE/'capture.cs.txt').read_text().replace('output/ares/stair-landing-rail-v1/native','output/ares/stair-landing-rail-v1/installed').replace('"ARES transport cases"','"ARES transport cases","West Stair Landing Rail"')
 text=text.replace('cut=Model.Load("models/props/ares/stair_landing_rail_v1/preview.vmdl")','cut=old')
 start=text.index('  replacement=new GameObject');end=text.index('\n  if(old.IsError',start)
 text=text[:start]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/props/ares/stair_landing_rail_v1/rail.vmdl");replacement.LodOverride=0;'+text[end:]
 text=text.replace('new[]{false,true}','new[]{true}').replace('PreviewOnly=true','Installed=true')
 text=text.replace('new Vector3(-540,-290,64),new Vector3(-540,-290,-20)','new Vector3(-119,800,272),new Vector3(-119,800,190)')
 (HERE/'capture_installed.cs.txt').write_text(text)
 print('Guarded installation staged; originals archived outside Assets')
elif sys.argv[1]=='install':
 print(native.script(HERE/'install.cs.txt'));print(native.call('asset_compile',dict(path='models/maps/ares/ares_hall.vmdl')))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
elif sys.argv[1]=='offline':
 import subprocess
 # Offline mutation is allowed only after the native CLI confirms no editor is running.
 state=subprocess.run([str(native.CLI),'--list'],cwd=ROOT,capture_output=True,text=True,check=True)
 assert json.loads(state.stdout)==[],'Editor running; use native install instead'
 plan=json.loads((OUT/'install-plan.json').read_text())
 for p,h in plan['protected'].items():assert sha(ROOT/p)==h,p
 for p,h in plan['files'].items():assert sha(OUT/'install-stage'/p)==h,p
 scene_path=ROOT/'Assets/scenes/maps/Ares/ares.scene';scene=json.loads(scene_path.read_text())
 assert not any(n.get('Name')=='West Stair Landing Rail' for n in scene['GameObjects'])
 node=json.loads((OUT/'install-stage/node.json').read_text());scene['GameObjects'].append(node)
 target=ROOT/'Assets'/plan['active_base'];shutil.copyfile(OUT/'install-stage/hall_without_rail.obj',target)
 scene_path.write_text(json.dumps(scene,indent=2)+'\n',encoding='utf-8')
 report=dict(Installed=True,Offline=True,OldFacesRemoved=84,AddedRenderers=1,AddedColliders=0,NativeCandidatePreviouslyCompiled=True,PublicHallRecompile='pending next editor open')
 (OUT/'installed.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
elif sys.argv[1]=='retire-offline':
 import subprocess
 state=subprocess.run([str(native.CLI),'--list'],cwd=ROOT,capture_output=True,text=True,check=True);assert json.loads(state.stdout)==[],'Use native asset tools while editor is open'
 scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text());assert any(n.get('Name')=='West Stair Landing Rail' for n in scene['GameObjects'])
 folder=ROOT/'Assets/models/props/ares/stair_landing_rail_v1';archive=OUT/'retired-preview';archive.mkdir(exist_ok=True)
 for name in ('preview.obj','preview.obj.meta','preview.vmdl','preview.vmdl.meta','preview.vmdl_c','hall_base.mtl'):
  source=folder/name;target=archive/name
  if source.exists():
   assert not target.exists(),target
   shutil.move(str(source),str(target))
 print('Retired private whole-map preview resources outside Assets')
