"""Walk-up information pillar review. Stage outside Assets; preserve current map and signs."""
from pathlib import Path
from collections import Counter
import json,hashlib,re,sys
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,railhead_props as P,railhead_map as R,riverdale_parts as G
OUT=ROOT/'output/railhead/info-pillar-v1';STAGE=OUT/'stage/Assets';RES='models/props/railhead/info_pillar_v1';FOLDER=STAGE/RES;FOLDER.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
F=P.frame_for(0,0,0,'+n');X,Y,Z=F.x,F.y,F.z
original=K.Model();P.info_pillar(original,0,0,facing='+n');R.configure(original)
def model(lod):
 m=K.Model()
 def box(c,size,paint='rw_steel_dark',bevel=.12):
  if lod<2:G.bevel_box(m,F.p(*c),(X,Y,Z),size,paint,bevel=min(bevel,min(size)*.3))
  else:m.oriented_box(F.p(*c),(X,Y,Z),size,paint)
 def turn(c,profile,paint='rw_stainless',axis=Y,sides=None):
  G.lathe_axis(m,F.p(*c),axis,profile,paint,sides=sides or (24,12,8)[lod])
 def pin(x,y,z,axis=Y,r=.19):turn((x,y,z),[(0,0),(r,0),(r,.09),(r*.7,.14),(0,.14)],axis=axis)
 # Folded monocoque on a flange, fitted gasketed service panels and weather cap.
 box((0,0,.32),(16,11.4,.64),'rw_stainless',.2)
 box((0,0,1.1),(13.8,9.8,1.1),'rw_rubber',.2)
 box((0,0,42.6),(13.8,9.8,81.8),bevel=.65)
 box((0,4.91,41.5),(12.3,.12,77.0),'rw_black',.35)
 box((0,4.99,41.5),(11.7,.16,76.4),'rw_steel_grey',.28)
 # Recessed intercom pan; spaced rails leave actual openings into the dark speaker cavity.
 box((0,5.11,53.5),(10.7,.18,20.3),'rw_black',.3)
 for x in (-5.05,5.05):box((x,5.24,53.5),(.45,.38,20),'rw_stainless',.1)
 for z in (43.7,63.3):box((0,5.24,z),(10.5,.38,.45),'rw_stainless',.1)
 box((0,5.24,48.5),(9.6,.38,8.8),'rw_stainless',.2)
 box((0,5.24,62.5),(9.6,.38,1.0),'rw_stainless',.1)
 for x in (-4.56,4.56):box((x,5.24,57.25),(.55,.38,8.3),'rw_stainless',.08)
 # Physical speaker grille, with a dark inset behind it instead of a black face decal.
 for z in np.linspace(53.3,61.2,12 if lod<2 else 6):box((0,5.35,float(z)),(8.7,.20,.25 if lod<2 else .5),'rw_stainless',.04)
 for x in (-3.8,3.8):
  for z in (44.6,62.6):pin(x,5.45,z)
 # Raised info/emergency controls and rubber seals: labels remain in their original artwork.
 for x,paint in ((-2.2,'rw_train_blue'),(2.2,'rw_red_paint')):
  turn((x,5.42,50),[(0,0),(1.50,0),(1.50,.14),(1.30,.27),(.98,.27),(.98,0)],'rw_stainless')
  turn((x,5.42,50),[(0,0),(1.02,0),(1.02,.30),(.90,.42),(0,.42)],paint)
  if lod==0:
   # Small tactile locator bumps around each control; decorative, no accessibility certification implied.
   for dx in (-.25,0,.25):pin(x+dx,5.44,46.5,r=.07)
 # Weather lip above the operator panel, mic aperture and lower maintenance latch.
 box((0,5.19,66.4),(11.8,.55,.55),'rw_stainless',.12)
 turn((0,5.39,45.3),[(0,0),(.28,0),(.28,.05),(0,.05)],'rw_black')
 box((0,5.12,17.5),(2.4,.18,4.5),'rw_black',.2)
 box((0,5.26,17.5),(1.6,.2,3.4),'rw_stainless',.2)
 turn((0,5.4,17.7),[(0,0),(.26,0),(.26,.06),(0,.06)],'rw_black',sides=6)
 for z in (12,72):box((-5.8,5.16,z),(.8,.22,2.5),'rw_stainless',.12)
 # Back cover and four captive anchors, all inside the original header footprint.
 box((0,-4.94,43),(11.5,.12,72),'rw_black',.25)
 box((0,-5.04,43),(11,.18,71.5),bevel=.25)
 if lod<2:
  for x in (-6.6,6.6):
   for y in (-4.2,4.2):
    turn((x,y,.64),[(0,0),(.40,0),(.40,.08),(0,.08)],axis=Z)
    turn((x,y,.72),[(0,0),(.30,0),(.30,.22),(0,.22)],axis=Z,sides=6)
 # Rounded enclosed lightbox. Original atlas quads are retained at their exact saved coordinates.
 box((0,0,92.2),(16.6,11.8,16.4),'rw_kiosk_fascia',.5)
 for z in (84.1,100.3):box((0,0,z),(17.2,12.4,1),'rw_alu_brushed',.18)
 for x in (-8.16,8.16):
  for y in (-5.76,5.76):box((x,y,92.2),(.28,.28,15.2),'rw_alu_brushed',.08)
 for paint in ('rw_signs','rw_prop_signs'):
  for i,(points,normal) in enumerate(original.polygons.get(paint,[])):
   m.polygon(paint,points,normal=normal,uv=original.polygon_uvs.get((paint,i)),normals=original.polygon_normals.get((paint,i)))
 R.configure(m);return m
counts=[];models=[]
for lod in range(3):
 m=model(lod);models.append(m);counts.append(K.write_obj(FOLDER/f'pillar_lod{lod}.obj',m,f'pillar_lod{lod}'))
K.write_vmdl(FOLDER/'pillar.vmdl',RES,'pillar_lod0',models[0]);doc=(FOLDER/'pillar.vmdl').read_text();a=doc.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=doc.index('\n\t\t\t},',a)+len('\n\t\t\t},')
meshes='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/pillar_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,20,60)))
(FOLDER/'pillar.vmdl').write_text(doc[:a]+f'{{ _class = "RenderMeshList" children = [ {meshes} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+doc[b:])
# Match this specific live pillar, never a loose spatial deletion.
legacy=K.Model();P.info_pillar(legacy,0,1500,facing='+n');R.configure(legacy);K.write_obj(OUT/'baseline.obj',legacy,'baseline')
def records(path):
 raw=path.read_text().splitlines(keepends=True);v=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in raw if l.startswith('v ')];paint='';rows=[]
 for i,line in enumerate(raw):
  if line.startswith('usemtl '):paint=line.split()[1]
  elif line.startswith('f '):rows.append((i,(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in line.split()[1:])))))
 return raw,rows
_,old=records(OUT/'baseline.obj');wanted=Counter(key for i,key in old)
public=ROOT/'Assets/models/maps/railhead/railhead_dress_centre.vmdl';doc=public.read_text();imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',doc);matches=[]
for path in imports:
 raw,rows=records(ROOT/'Assets'/path);remaining=wanted.copy();cut=set()
 for i,key in rows:
  if remaining[key]:remaining[key]-=1;cut.add(i)
 if not +remaining:matches.append((path,raw,cut))
assert len(matches)==1,'Published target differs/already upgraded'
path,raw,cut=matches[0];(FOLDER/'preview.obj').write_text(''.join(l for i,l in enumerate(raw) if i not in cut))
for name in re.findall(r'^mtllib (.+)$',''.join(raw),re.M):(FOLDER/name.strip()).write_bytes((ROOT/'Assets'/path).parent.joinpath(name.strip()).read_bytes())
(FOLDER/'preview.vmdl').write_text(doc.replace(path,f'{RES}/preview.obj'))
protected=[public,ROOT/'Assets/scenes/maps/Railhead/railhead.scene',*[ROOT/'Assets'/x for x in imports],ROOT/'Tools/railhead_map.py',ROOT/'Tools/railhead_props.py',ROOT/'Tools/railhead_furniture.py']
manifest=dict(preview_only=True,triangles=counts,old_faces=len(cut),active_base=path,cut=sorted(cut),position_world=[1500,0,0],protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'existing-upgrade-audit.json').write_text(json.dumps(dict(target='Booking hall information pillar at plan 0,1500',existing_replacement_found=False,checked=['Sources filenames/readmes for info_pillar, help point, SOS and information pillar','Tools railhead_props.info_pillar and railhead_furniture.info_pillar_head','Current dressing ModelDoc imports and exact original face match','Railhead ticket machine/pallet truck/bench upgrades excluded as already improved'],reuse=['Original info/SOS atlas quads and existing materials','Existing collision retained unchanged','Existing bevel and lathe helpers']),indent=2));print({'triangles':counts,'old_faces':len(cut),'preview_only':True,'base':path})
