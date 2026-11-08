from pathlib import Path
import sys,json,hashlib,shutil,numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/ares/pump-isolation-valve-v1'
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='stage':
 sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K
 from scipy.spatial.transform import Rotation
 m=json.loads((OUT/'manifest.json').read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 stage=OUT/'install-stage';stage.mkdir(exist_ok=True);before=OUT/'install-before';before.mkdir(exist_ok=True)
 for src,dest in ((ROOT/'Assets'/m['active_base'],before/'original-reactor.obj'),(ROOT/'Assets/scenes/maps/Ares/ares.scene',before/'ares.scene')):
  assert not dest.exists(),'Already staged; inspect installation';shutil.copyfile(src,dest)
 shutil.copyfile(OUT/'stage/Assets/models/props/ares/pump_isolation_valve_v1/preview.obj',stage/'reactor_with_valve_gap.obj')
 forward=np.array(m['world_forward']);up=np.array(m['world_up']);matrix=np.column_stack((forward,np.cross(up,forward),up));quaternion=Rotation.from_matrix(matrix).as_quat()
 ids=K.SceneIds('413ec345-1c69-46a4-b1d4-2e8dc1a04917');node=K.game_object(ids,'Northeast Pump Isolation Valve','reactor/northeast-pump-isolation-valve',m['world_position'],rotation=','.join(map(str,quaternion)),components=[K.component(ids,'Sandbox.ModelRenderer','reactor/northeast-pump-isolation-valve/renderer',Model=m['reused_approved_compiled_valve'],BodyGroups=18446744073709551615,RenderType='On',Tint='1,1,1,1')])
 (stage/'node.json').write_text(json.dumps(node))
 # Preserve the reviewed lower/upper pipe fragments for future source generation.
 raw=(stage/'reactor_with_valve_gap.obj').read_text().splitlines();v=[];uv=[];n=[];faces=[];added=False
 for l in raw:
  if l.startswith('# Fitted valve:'):added=True
  s=l.split()
  if not s:continue
  if s[0]=='v':a,z,north=map(float,s[1:]);v.append([-a,north,z])
  elif s[0]=='vt':uv.append(list(map(float,s[1:])))
  elif s[0]=='vn':a,z,north=map(float,s[1:]);n.append([-a,north,z])
  elif s[0]=='f' and added:
   f=[[int(k)-1 for k in t.split('/')] for t in s[1:]];faces.append(dict(points=[v[x] for x,t,z in f],uv=[uv[t] for x,t,z in f],normals=[n[z] for x,t,z in f]))
 assert len(faces)==96
 (HERE/'retained-pipe.json').write_text(json.dumps(dict(center=m['pipe_plan_center'],node=node,faces=faces),indent=2))
 (OUT/'install-plan.json').write_text(json.dumps(dict(active_base=m['active_base'],protected=m['protected'],files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}),indent=2))
 text=(ROOT/'Sources/Ares/control-console-native-v1/install.cs.txt').read_text().replace('control-console-native-v1','pump-isolation-valve-v1').replace('models/props/ares/control_console_native_v1/console.vmdl',m['reused_approved_compiled_valve']).replace('Core Process Console','Northeast Pump Isolation Valve').replace('dressing_without_console.obj','reactor_with_valve_gap.obj').replace('OldFacesRemoved=40','OldFacesRemoved=32,RetainedPipeTriangles=96').replace('model.IsError||model.MeshInfo.LodCount!=3','model.IsError')
 (HERE/'install.cs.txt').write_text(text)
 text=(HERE/'capture.cs.txt').read_text().replace('output/ares/pump-isolation-valve-v1/native','output/ares/pump-isolation-valve-v1/installed').replace('"ARES transport cases"','"ARES transport cases","Northeast Pump Isolation Valve"').replace('cut=Model.Load("models/props/ares/pump_isolation_valve_v1/preview.vmdl")','cut=old')
 start=text.index('  replacement=new GameObject');end=text.index('\n  if(old.IsError',start)
 text=text[:start]+'  replacement=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="'+m['reused_approved_compiled_valve']+'");replacement.LodOverride=0;'+text[end:]
 text=text.replace('new[]{false,true}','new[]{true}').replace('PreviewOnly=true','Installed=true')
 (HERE/'capture_installed.cs.txt').write_text(text);print('Guarded installation and generator patch staged')
elif sys.argv[1]=='install':print(native.script(HERE/'install.cs.txt'))
elif sys.argv[1]=='compile':print(native.call('asset_compile',dict(path='models/maps/ares/ares_reactor.vmdl')))
elif sys.argv[1]=='capture':print(native.script(HERE/'capture_installed.cs.txt'))
