from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/taxi-post-v1'
sys.path.insert(0,str(HERE));import native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='stage':
 sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,railhead_taxi_post as D
 m=json.loads((OUT/'manifest.json').read_text());guard=json.loads((OUT/'current-native/guard.json').read_text())
 for p,h in guard.items():assert sha(ROOT/p)==h,p
 for p,h in m['files'].items():assert sha(ROOT/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 for src,dest in ((ROOT/m['source'],before/'original-east.obj'),(ROOT/'Assets/scenes/maps/Railhead/railhead.scene',before/'railhead.scene')):
  assert not dest.exists(),'Already staged; inspect installation';shutil.copyfile(src,dest)
 # Keep the public source mtllib line; only remove the reviewed face lines.
 old=(ROOT/m['source']).read_text();new=(ROOT/'Assets/models/maps/railhead/taxi-post-v1/east_without_taxi.obj').read_text()
 import re
 new=re.sub(r'(?m)^mtllib .+$',re.search(r'(?m)^mtllib .+$',old).group(),new)
 (stage/'east_without_taxi.obj').write_text(new)
 (stage/'node.json').write_text(json.dumps(D.scene_object(K.SceneIds('29a58fab-920b-4cd8-a62c-2f917fb7b114'))))
 (OUT/'install-plan.json').write_text(json.dumps(dict(active_base=m['source'].replace('Assets/','',1),protected=guard,files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}),indent=2))
 text=(ROOT/'Sources/Ares/control-console-native-v1/install.cs.txt').read_text().replace('output/ares/control-console-native-v1','output/railhead/taxi-post-v1').replace('models/props/ares/control_console_native_v1/console.vmdl','models/maps/railhead/taxi-post-v1/taxi_post.vmdl').replace('||model.MeshInfo.LodCount!=3','').replace('Core Process Console','East Taxi Rank Head Post').replace('dressing_without_console.obj','east_without_taxi.obj').replace('OldFacesRemoved=40','OldFacesRemoved=124').replace('"ares"','"railhead"').replace('scenes/maps/ares/ares.scene','scenes/maps/railhead/railhead.scene').replace('Assets/scenes/maps/Ares/ares.scene','Assets/scenes/maps/Railhead/railhead.scene')
 (HERE/'install.cs.txt').write_text(text)
 text=(HERE/'capture_current.cs.txt').read_text().replace('output/railhead/taxi-post-v1/current-native','output/railhead/taxi-post-v1/installed').replace('"Station Indirect Light"','"Station Indirect Light","East Taxi Rank Head Post"').replace('cut=Model.Load("models/maps/railhead/taxi-post-v1/east_without_taxi.vmdl")','cut=old')
 start=text.index('  replacement=new GameObject');end=text.index('\n  if(old.IsError',start)
 text=text[:start]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/maps/railhead/taxi-post-v1/taxi_post.vmdl");replacement.LodOverride=0;'+text[end:]
 text=text.replace('new[]{false,true}','new[]{true}').replace('PreviewOnly=true','Installed=true')
 (HERE/'capture_installed.cs.txt').write_text(text)
 print('Guarded installation staged')
elif sys.argv[1]=='install':print(native.script(HERE/'install.cs.txt'))
elif sys.argv[1]=='compile':print(native.call('asset_compile',dict(path='models/maps/railhead/railhead_dress_east.vmdl')))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
