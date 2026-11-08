"""One concourse poster lightbox: existing artwork/glass in a manufactured enclosure."""
from pathlib import Path
import sys,json,re,hashlib,collections,shutil,math
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,railhead_map as R,railhead_dress_detail as D,riverdale_parts as G
OUT=ROOT/'output/railhead/city-light-v1';STAGE=OUT/'stage/Assets';RES='models/props/railhead/city_light_v1';DEST=STAGE/RES;DEST.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
F=D.Frame(545.,1299.5,34.,'-n');w,h=D.CITY_LIGHT;W,H=w+4.8,h+4.8
old=K.Model();D.legacy_city_light(old,545.,1299.5,'-n','poster_sea',bottom=34.);R.configure(old);K.write_obj(OUT/'expected.obj',old,'expected')
m=K.Model()
def box(c,size,paint='rw_steel_grey',b=.1):G.bevel_box(m,F.p(*c),(F.x,F.y,F.z),size,paint,bevel=b)
def turn(c,axis,profile,paint='rw_stainless',sides=24):G.lathe_axis(m,F.p(*c),axis,profile,paint,sides=sides)
def rounded(width,height,r):
 result=[]
 for x,z,a in ((width/2-r,height/2-r,0),(-width/2+r,height/2-r,math.pi/2),(-width/2+r,-height/2+r,math.pi),(width/2-r,-height/2+r,3*math.pi/2)):
  for k in range(7):
   theta=a+k*math.pi/12;result.append((x+r*math.cos(theta),h/2+z+r*math.sin(theta)))
 return result
def join(a,b,paint,mode):
 da,wa,ha,ra=a;db,wb,hb,rb=b;A=rounded(wa,ha,ra);B=rounded(wb,hb,rb)
 for i in range(len(A)):
  j=(i+1)%len(A);radial=F.x*(A[i][0]+A[j][0])+F.z*(A[i][1]+A[j][1]-h)
  toward=F.y if mode=='front' else radial*(1 if mode=='outer' else -1)
  D._face(m,paint,[F.p(A[i][0],da,A[i][1]),F.p(A[j][0],da,A[j][1]),F.p(B[j][0],db,B[j][1]),F.p(B[i][0],db,B[i][1])],toward)
# A continuous formed backbox and rolled front frame, with a real gasket return.
profiles=[(.10,W,H,.70),(2.82,W,H,.70),(3.2,W-.65,H-.65,.65),(3.2,w+.4,h+.4,.22),(2.76,w+.4,h+.4,.22),(2.74,w,h,.20)]
for i,paint,mode in ((0,'rw_steel_grey','outer'),(1,'rw_steel_grey','outer'),(2,'rw_kiosk_clad','front'),(3,'rw_kiosk_clad','inner'),(4,'rw_black','front')):join(profiles[i],profiles[i+1],paint,mode)
box((0,.12,h/2),(W-.5,.15,H-.5),'rw_steel_grey',.06)
# Preserve the original poster, glass, luminous edge strip, UVs and normals exactly.
for paint in ('rw_posters','rw_glass','rw_lamp_cool'):
 for i,(points,normal) in enumerate(old.polygons.get(paint,[])):
  m.polygon(paint,points,normal,uv=old.polygon_uvs.get((paint,i)),normals=old.polygon_normals.get((paint,i)))
# Two captured side hinges, anchor screws, and an accessible quarter-turn release.
for z in (12.,h-12.):
 for dz,length in ((-.95,.60),(-.25,.50),(.45,.60)):
  turn((-W/2+.12,1.6,z+dz),F.z,[(0,0),(.31,0),(.31,length),(0,length)],'rw_stainless',32)
 box((-W/2+.55,1.63,z),(.8,.35,1.9),'rw_kiosk_clad',.07)
 for zz in (z-.58,z+.58):turn((-W/2+.65,1.86,zz),F.y,[(0,0),(.13,0),(.13,.07),(0,.07)],sides=16)
turn((W/2-1.0,3.21,h*.46),F.y,[(0,0),(.43,0),(.43,.10),(.35,.16),(0,.16)],'rw_stainless',40)
box((W/2-1.0,3.38,h*.46),(.09,.02,.42),'rw_black',.01)
# A slim compression seal outlines the glazing; the lower lip has two drainage weeps.
for x in (-W*.33,W*.33):box((x,3.205,-1.28),(.60,.025,.10),'rw_black',.025)
turn((W/2-3.,1.,-2.4),-F.z,[(0,0),(.42,0),(.42,.40),(.30,.55),(0,.55)],'rw_black',24)
R.configure(m);K.write_obj(DEST/'lightbox.obj',m,'lightbox');K.write_vmdl(DEST/'lightbox.vmdl',RES,'lightbox',m)
def records(lines):
 vertices=[];paint='';result=[]
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':vertices.append(tuple(round(float(v),3) for v in s[1:]))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':result.append((i,(paint,tuple(sorted(vertices[int(t.split('/')[0])-1] for t in s[1:])))))
 return result
wanted=collections.Counter(k for i,k in records((OUT/'expected.obj').read_text().splitlines()));matches=[]
targets={part:collections.Counter({k:v for k,v in wanted.items() if (k[0]=='rw_glass')==(part=='glass')}) for part in ('opaque','glass')}
for docpath in (ROOT/'Assets/models/maps/railhead').glob('railhead_dress_*.vmdl'):
 doc=docpath.read_text();imports=re.findall(r'filename\s*=\s*"([^\"]+\.obj)"',doc)
 for rel in imports:
  lines=(ROOT/'Assets'/rel).read_text().splitlines(keepends=True);saved=records(lines)
  for part,target in targets.items():
   remaining=target.copy();cut=[]
   for i,k in saved:
    if remaining[k]:remaining[k]-=1;cut.append(i)
   if len(cut)==sum(target.values()) and not +remaining:matches.append((part,docpath,doc,imports,rel,lines,cut))
assert len(matches)==2 and {r[0] for r in matches}=={'opaque','glass'},'Saved lightbox differs from original helper'
parts=[];protected=[ROOT/'Assets/scenes/maps/Railhead/railhead.scene']
for part,docpath,doc,imports,rel,lines,cut in matches:
 name='preview_glass' if part=='glass' else 'preview';removed=set(cut);(DEST/f'{name}.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed))
 for library in re.findall(r'^mtllib (.+)$',''.join(lines),re.M):shutil.copyfile((ROOT/'Assets'/rel).parent/library.strip(),DEST/library.strip())
 (DEST/f'{name}.vmdl').write_text(doc.replace(rel,RES+f'/{name}.obj'))
 parts.append(dict(part=part,public_model=docpath.relative_to(ROOT/'Assets').as_posix(),active_base=rel,cut=cut,preview=name,original_faces=len(cut)))
 protected.extend([docpath,*[ROOT/'Assets'/p for p in imports]])
# Copy actual exported face attributes: automatically projected UVs depend on the
# original export, so rebuilding the helper alone would subtly change those UVs.
preserved={'rw_posters','rw_glass','rw_lamp_cool'}
for paint in preserved:
 m.polygons.pop(paint,None)
 for table in (m.polygon_uvs,m.polygon_normals):
  for key in [key for key in table if key[0]==paint]:del table[key]
for part,docpath,doc,imports,rel,lines,cut in matches:
 v=[];uv=[];normals=[];paint='';selected=set(cut)
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':
   x,y,z=map(float,s[1:]);v.append(np.array((-x,z,y)))
  elif s[0]=='vt':uv.append(tuple(map(float,s[1:])))
  elif s[0]=='vn':
   x,y,z=map(float,s[1:]);normals.append(np.array((-x,z,y)))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f' and i in selected and paint in preserved:
   corners=[tuple(int(k)-1 for k in t.split('/')) for t in s[1:]]
   ns=[normals[c] for a,b,c in corners]
   m.polygon(paint,[v[a] for a,b,c in corners],np.mean(ns,axis=0),uv=[uv[b] for a,b,c in corners],normals=ns)
K.write_obj(DEST/'lightbox.obj',m,'lightbox');K.write_vmdl(DEST/'lightbox.vmdl',RES,'lightbox',m)
for path in set(m.material_overrides.values()):
 p=ROOT/'Assets'/path;protected.append(p)
 for texture in re.findall(r'Texture\w+\s+"([^\"]+)"',p.read_text()):
  q=ROOT/'Assets'/texture
  if q.is_file():protected.append(q)
manifest=dict(review_only=True,parts=parts,original_faces=sum(p['original_faces'] for p in parts),triangles=m.triangle_count(),protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k not in ('parts','protected','files')}))
