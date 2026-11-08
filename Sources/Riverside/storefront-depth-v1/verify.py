from pathlib import Path
import json,hashlib,re,collections,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/riverside/storefront-depth-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();folder=ROOT/'Assets/models/props/riverside/storefront_depth_v1'
for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
original=(ROOT/'Assets'/m['active_base']).read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==20 and all(original[i].startswith('f ') for i in cut)
assert (folder/'preview.obj').read_text()==''.join(l for i,l in enumerate(original) if i not in cut)
public=(ROOT/'Assets/models/maps/riverside/riverside_store.vmdl').read_text();preview=(folder/'preview.vmdl').read_text();assert preview.replace('models/props/riverside/storefront_depth_v1/preview.obj',m['active_base'])==public
reports=[]
for lod,expected in enumerate(m['triangles']):
 v=[];uv=[];n=[];f=[];paint='';paints=[]
 for l in (folder/f'windows_lod{lod}.obj').read_text().splitlines():
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(list(map(float,s[1:])))
  elif s[0]=='vt':uv.append(list(map(float,s[1:])))
  elif s[0]=='vn':n.append(list(map(float,s[1:])))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':f.append([[int(k)-1 for k in t.split('/')] for t in s[1:]]);paints.append(paint)
 v=np.array(v);uv=np.array(uv);n=np.array(n);f=np.array(f);p=v[f[:,:,0]];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);length=np.linalg.norm(cross,axis=1)
 assert len(f)==expected and np.isfinite(v).all() and np.isfinite(uv).all() and np.isfinite(n).all() and (length>1e-10).all()
 agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement==1,(lod,agreement)
 for plane in (640.,646.):
  surface=np.array([paint=='rs_boards_dark' and np.allclose(pts[:,2],plane) for paint,pts in zip(paints,p)])
  area=float(length[surface].sum()/2);assert abs(area-(230*130-(92+72)*54))<.01,(lod,plane,area)
 glass=np.array([paint=='glass' for paint in paints]);assert glass.sum()==16 and p[glass,:,2].min()>642 and p[glass,:,2].max()<643
 reports.append(dict(lod=lod,triangles=expected,finite_nondegenerate=True,normal_agreement=agreement,both_wall_faces_rebuilt_with_real_openings=True))
doc=(folder/'windows.vmdl').read_text();assert 'PhysicsShapeBox' not in doc and 'PhysicsHullFile' not in doc
for path in re.findall(r'(?:filename|to)\s*=\s*"([^\"]+)"',doc):assert (ROOT/'Assets'/path).exists(),path
native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['Lods']==3 and native['Triangles']==sum(m['triangles']) and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged']
report=dict(review_only=True,only_original_20_faces_removed_in_preview=True,all_other_obj_records_preserved=True,complete_public_modeldoc_physics_and_all_other_imports_preserved=True,public_scene_models_and_shared_materials_unchanged=True,existing_stocked_interior_preserved=True,all_lods=reports,native=native)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
