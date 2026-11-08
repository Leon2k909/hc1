from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/city-light-v1'
sys.path.insert(0,str(HERE));import native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='stage':
 sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,railhead_city_light as D
 m=json.loads((OUT/'manifest.json').read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 dest=before/'railhead.scene';assert not dest.exists(),'Already staged; inspect installation';shutil.copyfile(ROOT/'Assets/scenes/maps/Railhead/railhead.scene',dest)
 parts=[]
 for part in m['parts']:
  name=part['part']+'.obj';shutil.copyfile(ROOT/'Assets'/part['active_base'],before/name)
  shutil.copyfile(ROOT/'Assets/models/props/railhead/city_light_v1'/(part['preview']+'.obj'),stage/name)
  parts.append(dict(active_base=part['active_base'],stage_file=name))
 (stage/'node.json').write_text(json.dumps(D.scene_object(K.SceneIds('1c380621-cecc-456b-89b4-c92b52a0e13d'))))
 (OUT/'install-plan.json').write_text(json.dumps(dict(parts=parts,protected=m['protected'],files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}),indent=2))
 text=(HERE/'capture.cs.txt').read_text().replace('output/railhead/city-light-v1/native','output/railhead/city-light-v1/installed').replace('"Central Platform PA Speaker"','"Central Platform PA Speaker","East Concourse Poster Lightbox"').replace('cut=Model.Load("models/props/railhead/city_light_v1/preview.vmdl")','cut=old').replace('cutGlass=Model.Load("models/props/railhead/city_light_v1/preview_glass.vmdl")','cutGlass=oldGlass')
 start=text.index('  replacement=new GameObject');end=text.index('\n  if(old.IsError',start)
 text=text[:start]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/props/railhead/city_light_v1/lightbox.vmdl");replacement.LodOverride=0;'+text[end:]
 text=text.replace('new[]{false,true}','new[]{true}').replace('PreviewOnly=true','Installed=true')
 (HERE/'capture_installed.cs.txt').write_text(text);print('Guarded installation staged')
elif sys.argv[1]=='install':print(native.script(HERE/'install.cs.txt'))
elif sys.argv[1]=='compile':
 for part in json.loads((OUT/'manifest.json').read_text())['parts']:print(native.call('asset_compile',dict(path=part['public_model'])))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
