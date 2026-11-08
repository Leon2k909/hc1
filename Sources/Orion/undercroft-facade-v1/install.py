from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/orion/undercroft-facade-v1'
sys.path.insert(0,str(HERE));import native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='stage':
 sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,orion_undercroft_facade as D
 m=json.loads((OUT/'manifest.json').read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 for src,dest in ((ROOT/'Assets/models/maps/orion/orion_launch_deck.obj',before/'original-launch-deck.obj'),(ROOT/'Assets/scenes/maps/Orion/orion.scene',before/'orion.scene')):
  assert not dest.exists(),'Already staged; inspect installation';shutil.copyfile(src,dest)
 shutil.copyfile(ROOT/'Assets/models/props/orion/undercroft_facade_v1/preview.obj',stage/'deck_without_facade.obj')
 (stage/'node.json').write_text(json.dumps(D.scene_object(K.SceneIds('cd0fd89c-6ca4-4cf3-aa26-145601afc2e5'))))
 (OUT/'install-plan.json').write_text(json.dumps(dict(active_base='models/maps/orion/orion_launch_deck.obj',protected=m['protected'],files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}),indent=2))
 text=(ROOT/'Sources/Railhead/taxi-post-v1/install.cs.txt').read_text().replace('output/railhead/taxi-post-v1','output/orion/undercroft-facade-v1').replace('models/maps/railhead/taxi-post-v1/taxi_post.vmdl','models/props/orion/undercroft_facade_v1/facade.vmdl').replace('East Taxi Rank Head Post','Orion Undercroft Façade').replace('east_without_taxi.obj','deck_without_facade.obj').replace('OldFacesRemoved=124','OldFacesRemoved=50').replace('AddedRenderers=1','AddedRenderers=1,AddedInteriorLights=2').replace('"railhead"','"orion"').replace('scenes/maps/railhead/railhead.scene','scenes/maps/orion/orion.scene').replace('Assets/scenes/maps/Railhead/railhead.scene','Assets/scenes/maps/Orion/orion.scene')
 (HERE/'install.cs.txt').write_text(text,encoding='utf-8')
 text=(HERE/'capture.cs.txt').read_text().replace('output/orion/undercroft-facade-v1/native','output/orion/undercroft-facade-v1/installed').replace('"Orion Launch Vehicle"','"Orion Launch Vehicle","Orion Undercroft Façade"').replace('cut=Model.Load("models/props/orion/undercroft_facade_v1/preview.vmdl")','cut=old')
 a=text.index('  // Identical light sources');b=text.index('room=scene.GetAllComponents',a);text=text[:a]+'  '+text[b:]
 a=text.index('  replacement=new GameObject');b=text.index('\n  if(old.IsError',a)
 text=text[:a]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/props/orion/undercroft_facade_v1/facade.vmdl");replacement.LodOverride=0;'+text[b:]
 text=text.replace('new[]{false,true}','new[]{true}').replace('PreviewOnly=true','Installed=true')
 (HERE/'capture_installed.cs.txt').write_text(text,encoding='utf-8');print('Guarded installation staged')
elif sys.argv[1]=='install':print(native.script(HERE/'install.cs.txt'))
elif sys.argv[1]=='compile':print(native.call('asset_compile',dict(path='models/maps/orion/orion_launch_deck.vmdl')))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
