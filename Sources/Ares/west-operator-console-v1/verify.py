from pathlib import Path
import json,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/west-operator-console-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
folder=OUT/'stage/Assets/models/props/ares/west_operator_console_v1'
raw=(ROOT/'Assets'/m['active_base']).read_text().splitlines(keepends=True);assert (folder/'preview.obj').read_text()==''.join(l for i,l in enumerate(raw) if i not in set(m['cut'])) and len(m['cut'])==40
reports=[]
for lod,name in enumerate(('after.obj','after_lod1.obj','after_lod2.obj')):
 lines=(folder/name).read_text().splitlines();v=[];uv=[];n=[];f=[];paint='';paints=[]
 for l in lines:
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(list(map(float,s[1:])))
  elif s[0]=='vt':uv.append(list(map(float,s[1:])))
  elif s[0]=='vn':n.append(list(map(float,s[1:])))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':f.append([[int(k)-1 for k in t.split('/')] for t in s[1:]]);paints.append(paint)
 v=np.array(v);uv=np.array(uv);n=np.array(n);f=np.array(f);t=v[f[:,:,0]];c=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);assert np.isfinite(v).all() and np.isfinite(uv).all() and np.isfinite(n).all() and (np.linalg.norm(c,axis=1)>1e-12).all()
 agreement=float(((c*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement==1,agreement
 source=ROOT/'Assets/models/props/ares/control_console_native_v1'/('console.obj' if lod==0 else f'console_lod{lod}.obj');assert [l for l in lines if l.startswith('v ')]==[l for l in source.read_text().splitlines() if l.startswith('v ')],'Approved vertex positions changed'
 screen_uv=np.array([uv[t] for p,face in zip(paints,f) if p=='Original_approved_Ares_display_atlas' for x,t,z in face]);bounds=np.array(m['screen_uv_bounds']);assert np.allclose(screen_uv.min(0),bounds[0]) and np.allclose(screen_uv.max(0),bounds[1])
 assert len(f)==m['triangles'][lod];reports.append(dict(lod=lod,triangles=len(f),normal_agreement=agreement,source_positions_preserved=True,original_station_atlas_region_preserved=True))
report=dict(preview_only=True,public_map_scene_materials_unchanged=True,exact_old_faces_in_private_preview=40,lods=reports)
if (OUT/'native/validation.json').exists():
 native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['SceneUnchanged'] and native['PlayStateUnchanged'] and native['AddedColliders']==0 and native['Lods']==3 and native['LodTriangles']==m['triangles'];report['native']=native
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
