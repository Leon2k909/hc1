from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
old=ROOT/'Sources/Riverdale/sand-bin-v1'
t=(old/'model.py').read_text();start=t.index(' def loft(');end=t.index(' # Tapered',start)
t=t[:start]+''' def loft(rings,paint,caps=True):
  if caps:face(paint,rings[0],-Z);face(paint,rings[-1],Z)
  N=len(rings[0]);normals={}
  for i in range(len(rings)-1):
   for k in range(N):
    j=(k+1)%N;a=rings[i];b=rings[i+1]
    n=K.normalise(np.cross(a[j]-a[k],b[k]-a[k]));hint=(a[k]+a[j]+b[k]+b[j])/4-C;hint[2]=0
    normals[i,k]=n if np.dot(n,hint)>0 else -n
  def normal(i,k):return K.normalise(sum((normals[q,p] for q in (i-1,i) if 0<=q<len(rings)-1 for p in ((k-1)%N,k)),np.zeros(3)))
  for i,(a,b) in enumerate(zip(rings,rings[1:])):
   for k in range(N):
    j=(k+1)%N
    D._face(m,paint,[a[k],a[j],b[j],b[k]],normals[i,k],normals=[normal(i,k),normal(i,j),normal(i+1,j),normal(i+1,k)])
'''+t[end:]
t=t.replace(' R.configure(m)\n return m',''' R.configure(m)
 # Object-space UVs keep contact dirt at the foot and the lid's wear on its top.
 for paint,faces in list(m.polygons.items()):
  if paint!='rv_yd_bin':continue
  for i,(points,n) in enumerate(faces):
   local=[p-C for p in points];is_lid=abs(n[2])>.65 and sum(p[2] for p in local)/len(local)>25
   alias='sb_lid' if is_lid else 'sb_body'
   if is_lid:uv=[(p[0]/36+.5,p[1]/25+.5) for p in local]
   else:uv=[((p[0] if abs(n[1])>=abs(n[0]) else p[1])/36+.5,p[2]/32) for p in local]
   m.polygon(alias,points,n,uv=uv,normals=m.polygon_normals.get((paint,i)))
  del m.polygons[paint]
 for alias in ('sb_body','sb_lid'):
  m.material_overrides[alias]='models/maps/riverdale/sand-bin-v2/'+alias+'.vmat';m.tile_overrides[alias]=36
 return m''')
(HERE/'model.py').write_text(t)
t=(old/'build.py').read_text().replace('sand-bin-v1','sand-bin-v2')
t=t.replace('files={str(p.relative_to(STAGE))',"from surfaces import write_surfaces\nwrite_surfaces(MODEL,RES)\nfiles={str(p.relative_to(STAGE))")
(HERE/'build.py').write_text(t)
t=(old/'verify.py').read_text().replace('sand-bin-v1','sand-bin-v2').replace("len(manifest['files'])==6","len(manifest['files'])==16")
(HERE/'verify.py').write_text(t)
