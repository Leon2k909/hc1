from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/riverside/storefront-depth-v1'
sys.path.insert(0,str(HERE));import native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='stage':
 sys.path.insert(0,str(ROOT/'Tools'));import riverside_storefront_depth as D
 m=json.loads((OUT/'manifest.json').read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 for src,dest in ((ROOT/'Assets'/m['active_base'],before/'original-store.obj'),(ROOT/'Assets/scenes/maps/Riverside/riverside.scene',before/'riverside.scene')):
  if dest.exists():assert sha(src)==sha(dest),'Staged backup differs; inspect installation'
  else:shutil.copyfile(src,dest)
 shutil.copyfile(ROOT/'Assets/models/props/riverside/storefront_depth_v1/preview.obj',stage/'store_without_flat_windows.obj')
 (stage/'node.json').write_text(json.dumps(D.scene_object()))
 snapshot=native.script(HERE/'snapshot_install.cs.txt');print(snapshot);assert snapshot.get('Clean'),snapshot
 (OUT/'install-plan.json').write_text(json.dumps(dict(active_base=m['active_base'],protected=m['protected'],files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}),indent=2))
 text=(HERE/'capture.cs.txt').read_text().replace('output/riverside/storefront-depth-v1/native','output/riverside/storefront-depth-v1/installed').replace('"Water Tower Tanks"','"Water Tower Tanks","Lucky Stop Glazed Windows"').replace('cut=Model.Load("models/props/riverside/storefront_depth_v1/preview.vmdl")','cut=old')
 a=text.index('  replacement=new GameObject');b=text.index('\n  if(old.IsError',a);text=text[:a]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/props/riverside/storefront_depth_v1/windows.vmdl");replacement.LodOverride=0;'+text[b:]
 text=text.replace('new[]{false,true}','new[]{true}').replace('PreviewOnly=true','Installed=true');(HERE/'capture_installed.cs.txt').write_text(text,encoding='utf-8');print('Guarded live-scene installation staged')
elif sys.argv[1]=='install':print(native.script(HERE/'install.cs.txt'))
elif sys.argv[1]=='compile':print(native.call('asset_compile',dict(path='models/maps/riverside/riverside_store.vmdl')))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
