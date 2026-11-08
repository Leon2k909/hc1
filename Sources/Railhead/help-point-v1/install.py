from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/help-point-v1'
sys.path.insert(0,str(HERE));import native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='stage':
 sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,railhead_help_point as D
 m=json.loads((OUT/'manifest.json').read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 for src,dest in ((ROOT/'Assets'/m['active_base'],before/'original-west.obj'),(ROOT/'Assets/scenes/maps/Railhead/railhead.scene',before/'railhead.scene')):
  assert not dest.exists(),'Already staged; inspect installation';shutil.copyfile(src,dest)
 shutil.copyfile(ROOT/'Assets/models/props/railhead/help_point_v1/preview.obj',stage/'west_without_help_point.obj')
 (stage/'node.json').write_text(json.dumps(D.scene_object(K.SceneIds('b2be9919-67d8-4c95-af73-c78223aa9c50'))))
 (OUT/'install-plan.json').write_text(json.dumps(dict(active_base=m['active_base'],protected=m['protected'],files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}),indent=2))
 text=(ROOT/'Sources/Railhead/taxi-post-v1/install.cs.txt').read_text().replace('output/railhead/taxi-post-v1','output/railhead/help-point-v1').replace('models/maps/railhead/taxi-post-v1/taxi_post.vmdl','models/props/railhead/help_point_v1/help_point.vmdl').replace('East Taxi Rank Head Post','West Platform Help Point').replace('east_without_taxi.obj','west_without_help_point.obj').replace('OldFacesRemoved=124','OldFacesRemoved=360')
 (HERE/'install.cs.txt').write_text(text)
 text=(HERE/'capture.cs.txt').read_text().replace('output/railhead/help-point-v1/native','output/railhead/help-point-v1/installed').replace('"East Taxi Rank Head Post"','"East Taxi Rank Head Post","West Platform Help Point"').replace('cut=Model.Load("models/props/railhead/help_point_v1/preview.vmdl")','cut=old')
 start=text.index('  replacement=new GameObject');end=text.index('\n  if(old.IsError',start)
 text=text[:start]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/props/railhead/help_point_v1/help_point.vmdl");replacement.LodOverride=0;'+text[end:]
 text=text.replace('new[]{false,true}','new[]{true}').replace('PreviewOnly=true','Installed=true')
 (HERE/'capture_installed.cs.txt').write_text(text)
 print('Guarded installation staged')
elif sys.argv[1]=='install':print(native.script(HERE/'install.cs.txt'))
elif sys.argv[1]=='compile':print(native.call('asset_compile',dict(path='models/maps/railhead/railhead_dress_west.vmdl')))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
