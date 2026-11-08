from pathlib import Path
import json,numpy as np,sys
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/bulkhead-lamp-native-v1';folder=OUT/'stage/Assets/models/props/ares/bulkhead_lamp_native_v1';counts={}
for name in ('lamp_lod1.obj','lamp_lod2.obj'):
 lines=(folder/name).read_text().splitlines();v=[];n=[];normal_lines=[];faces=[]
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(np.array(list(map(float,s[1:]))))
  elif s[0]=='vn':n.append(np.array(list(map(float,s[1:]))));normal_lines.append(i)
  elif s[0]=='f':faces.append([[int(k)-1 for k in t.split('/')] for t in s[1:]])
 repaired=0
 for f in faces:
  p=[v[t[0]] for t in f];c=np.cross(p[1]-p[0],p[2]-p[0]);c/=np.linalg.norm(c)
  if np.dot(c,np.mean([n[t[2]] for t in f],axis=0))<=0:
   for t in f:lines[normal_lines[t[2]]]='vn '+' '.join(f'{x:.8f}' for x in c)
   repaired+=1
 (folder/name).write_text('\n'.join(lines)+'\n');counts[name]=repaired
sys.path.insert(0,str(ROOT/'Sources/Ares/surface-finish-v2'));import native
script='''var root=Sandbox.Project.Current.GetRootPath();var output=System.IO.Path.Combine(root,"output/ares/bulkhead-lamp-native-v1/stage/Assets/models/props/ares/bulkhead_lamp_native_v1");
foreach(var f in new[]{"lamp_lod1.obj","lamp_lod2.obj"}){var target=System.IO.Path.Combine(root,"Assets/models/props/ares/bulkhead_lamp_native_v1",f);System.IO.File.Copy(System.IO.Path.Combine(output,f),target,true);Editor.AssetSystem.RegisterFile(target);}return true;'''
path=Path(__file__).with_name('repair_lod_normals.cs.txt');path.write_text(script);print(native.script(path));print(native.call('asset_compile',dict(path='models/props/ares/bulkhead_lamp_native_v1/lamp.vmdl')))
(OUT/'lod-normal-repair.json').write_text(json.dumps(counts,indent=2));print(counts)
