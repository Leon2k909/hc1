from pathlib import Path
import sys,json,hashlib,shutil,re
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/pa-speaker-v2'
sys.path.insert(0,str(HERE));import current_native as native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='stage':
 sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,railhead_pa_speaker as D
 m=json.loads((OUT/'manifest.json').read_text());guard=json.loads((OUT/'current-native/guard.json').read_text())
 for p,h in guard.items():assert sha(ROOT/p)==h,p
 for p,h in m['files'].items():assert sha(ROOT/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 for src,dest in ((ROOT/m['source'],before/'original-centre.obj'),(ROOT/'Assets/scenes/maps/Railhead/railhead.scene',before/'railhead.scene')):
  assert not dest.exists(),'Already staged; inspect installation';shutil.copyfile(src,dest)
 old=(ROOT/m['source']).read_text();new=(ROOT/'Assets/models/maps/railhead/pa-speaker-v2/centre_without_speaker.obj').read_text()
 new=re.sub(r'(?m)^mtllib .+$',re.search(r'(?m)^mtllib .+$',old).group(),new)
 (stage/'centre_without_speaker.obj').write_text(new)
 (stage/'node.json').write_text(json.dumps(D.scene_object(K.SceneIds('ec4c5b49-72b4-48e5-969f-bb9248a73ed1'))))
 (OUT/'install-plan.json').write_text(json.dumps(dict(active_base=m['source'].replace('\\','/').removeprefix('Assets/'),protected=guard,files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}),indent=2))
 text=(ROOT/'Sources/Railhead/taxi-post-v1/install.cs.txt').read_text().replace('output/railhead/taxi-post-v1','output/railhead/pa-speaker-v2').replace('models/maps/railhead/taxi-post-v1/taxi_post.vmdl','models/maps/railhead/pa-speaker-v2/pa_speaker.vmdl').replace('East Taxi Rank Head Post','Central Platform PA Speaker').replace('east_without_taxi.obj','centre_without_speaker.obj').replace('OldFacesRemoved=124','OldFacesRemoved=36')
 (HERE/'install.cs.txt').write_text(text)
 text=(HERE/'capture_current.cs.txt').read_text().replace('output/railhead/pa-speaker-v2/current-native','output/railhead/pa-speaker-v2/installed').replace('"West Platform Help Point"','"West Platform Help Point","Central Platform PA Speaker"').replace('cut=Model.Load("models/maps/railhead/pa-speaker-v2/centre_without_speaker.vmdl")','cut=old')
 start=text.index('  replacement=new GameObject');end=text.index('\n  if(old.IsError',start)
 text=text[:start]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/maps/railhead/pa-speaker-v2/pa_speaker.vmdl");replacement.LodOverride=0;'+text[end:]
 text=text.replace('new[]{false,true}','new[]{true}').replace('PreviewOnly=true','Installed=true')
 (HERE/'capture_installed.cs.txt').write_text(text)
 print('Guarded installation staged')
elif sys.argv[1]=='install':print(native.script(HERE/'install.cs.txt'))
elif sys.argv[1]=='compile':print(native.call('asset_compile',dict(path='models/maps/railhead/railhead_dress_centre.vmdl')))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
