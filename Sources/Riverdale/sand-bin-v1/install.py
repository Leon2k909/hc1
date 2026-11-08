from pathlib import Path
import sys,json,hashlib,shutil,re
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/riverdale/sand-bin-v1'
sys.path.insert(0,str(HERE));import current_native as native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='stage':
 sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,riverdale_sand_bin as D
 m=json.loads((OUT/'manifest.json').read_text());guard=json.loads((OUT/'current-native/guard.json').read_text())
 for p,h in guard.items():assert sha(ROOT/p)==h,p
 for p,h in m['files'].items():assert sha(ROOT/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 for src,dest in ((ROOT/m['source'],before/'original-yard.obj'),(ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene',before/'riverdale.scene')):
  assert not dest.exists(),'Already staged; inspect installation';shutil.copyfile(src,dest)
 old=(ROOT/m['source']).read_text();new=(ROOT/'Assets/models/maps/riverdale/sand-bin-v1/yard_without_bin.obj').read_text()
 new=re.sub(r'(?m)^mtllib .+$',re.search(r'(?m)^mtllib .+$',old).group(),new)
 (stage/'yard_without_bin.obj').write_text(new)
 (stage/'node.json').write_text(json.dumps(D.scene_object(K.SceneIds('e1a2b420-c718-4ac0-986a-41d4ea7a56de'))))
 (OUT/'install-plan.json').write_text(json.dumps(dict(active_base=m['source'].replace('\\','/').removeprefix('Assets/'),protected=guard,files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}),indent=2))
 text=(ROOT/'Sources/Railhead/taxi-post-v1/install.cs.txt').read_text().replace('output/railhead/taxi-post-v1','output/riverdale/sand-bin-v1').replace('models/maps/railhead/taxi-post-v1/taxi_post.vmdl','models/maps/riverdale/sand-bin-v1/sand_bin.vmdl').replace('East Taxi Rank Head Post','Court Sand Bin').replace('east_without_taxi.obj','yard_without_bin.obj').replace('OldFacesRemoved=124','OldFacesRemoved=38').replace('"railhead"','"riverdale"').replace('scenes/maps/railhead/railhead.scene','scenes/maps/riverdale/riverdale.scene').replace('Assets/scenes/maps/Railhead/railhead.scene','Assets/scenes/maps/Riverdale/riverdale.scene')
 (HERE/'install.cs.txt').write_text(text)
 text=(HERE/'capture_current.cs.txt').read_text().replace('output/riverdale/sand-bin-v1/current-native','output/riverdale/sand-bin-v1/installed').replace('"Yard Prop Solids"','"Yard Prop Solids","Court Sand Bin"').replace('cut=Model.Load("models/maps/riverdale/sand-bin-v1/yard_without_bin.vmdl")','cut=old')
 start=text.index('  replacement=new GameObject');end=text.index('\n  if(old.IsError',start)
 text=text[:start]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/maps/riverdale/sand-bin-v1/sand_bin.vmdl");replacement.LodOverride=0;'+text[end:]
 text=text.replace('new[]{false,true}','new[]{true}').replace('PreviewOnly=true','Installed=true')
 (HERE/'capture_installed.cs.txt').write_text(text);print('Guarded installation staged')
elif sys.argv[1]=='install':print(native.script(HERE/'install.cs.txt'))
elif sys.argv[1]=='compile':print(native.call('asset_compile',dict(path='models/maps/riverdale/riverdale_yard_props.vmdl')))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
