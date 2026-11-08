from pathlib import Path
import math,random,json,re
root=Path.cwd();out=root/'output/veridant/garden-grass-blades-v1';res='models/props/shared/veridant_short_garden_grass_v1';stage=out/'stage'/res;stage.mkdir(parents=True,exist_ok=True)
# Reuse actual bent blade geometry from the installed grass family, retaining its
# UVs and LODs. OBJ coordinates are Y-up (world Y,world Z,world X).
rng=random.Random(664)
placements=[]
for x in range(674,1170,4):
 for n in range(-1332,-1237,4):
  e=x+rng.uniform(-1.1,1.1);north=n+rng.uniform(-1.1,1.1)
  placements.append((e,north,rng.uniform(0,math.tau),rng.uniform(1.1,1.5),rng.uniform(.25,.36)))
for lod,step in ((0,1),(1,2),(2,4)):
 lines=(root/f'Assets/models/grass/grass_tuft_lod{lod}.obj').read_text().splitlines()
 data={k:[] for k in ('v','vt','vn')};faces=[]
 for l in lines:
  w=l.split()
  if not w:continue
  if w[0] in data:data[w[0]].append(tuple(float(a) for a in w[1:]))
  elif w[0]=='f':faces.append([tuple(int(a) if a else 0 for a in q.split('/')) for q in w[1:]])
 # The installed tuft was authored for taller meadow grass. Narrow each blade
 # across its paired edge vertices to match the reduced maintained-lawn height.
 verts=data['v']
 for j in range(0,len(verts)-1,2):
  a,b=verts[j],verts[j+1];mid=tuple((x+y)*.5 for x,y in zip(a,b))
  verts[j]=tuple(c+(x-c)*.25 for x,c in zip(a,mid))
  verts[j+1]=tuple(c+(x-c)*.25 for x,c in zip(b,mid))
 result=['o garden_grass\n'];offset={k:0 for k in data}
 for index,(e,n,a,sxy,sz) in enumerate(placements):
  if index%step:continue
  ca,sa=math.cos(a),math.sin(a)
  for x,y,z in data['v']:
   xx=x*sxy;zz=z*sxy
   result.append(f'v {920-e+xx*ca-zz*sa:.5f} {y*sz-.08:.5f} {1285+n+xx*sa+zz*ca:.5f}\n')
  result.extend('vt '+' '.join(str(x) for x in p)+'\n' for p in data['vt'])
  for x,y,z in data['vn']:
   xx=x/sxy;yy=y/sz;zz=z/sxy;length=math.sqrt(xx*xx+yy*yy+zz*zz)
   result.append(f'vn {(xx*ca-zz*sa)/length:.6f} {yy/length:.6f} {(xx*sa+zz*ca)/length:.6f}\n')
  for face in faces:
   result.append('f '+' '.join('/'.join(str(q+offset[k]) if q else '' for q,k in zip(c,data)) for c in face)+'\n')
  for k in data:offset[k]+=len(data[k])
 (stage/f'grass_lod{lod}.obj').write_text(''.join(result))
mat=(root/'Assets/models/grass/grass.vmat').read_text()
for old,new in (('g_flBladeHeight "26.000"','g_flBladeHeight "4.000"'),('g_flSwayAmount "1.200"','g_flSwayAmount "0.080"'),('g_flGustAmount "3.000"','g_flGustAmount "0.150"')):mat=mat.replace(old,new)
(stage/'grass.vmat').write_text(mat)
model=(root/'Assets/models/grass/grass_tuft.vmdl').read_text().replace('models/grass/grass.vmat',res+'/grass.vmat')
for lod in range(3):model=model.replace(f'models/grass/grass_tuft_lod{lod}.obj',res+f'/grass_lod{lod}.obj')
# Keep the complete blade field for this single near-player review bed. The
# meadow tuft LODs discard too much coverage when used as a low lawn carpet.
model='\n'.join(l for l in model.splitlines() if 'name = "lod1"' not in l and 'name = "lod2"' not in l)
model=re.sub(r'   \{ _class = "LODGroupList" children = \[.*?   \] \},\n','',model,flags=re.S)
(stage/'grass.vmdl').write_text(model)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/garden-grass-blades');ex.mkdir(parents=True,exist_ok=True)
p=ex/'import.cs';p.write_text('''var root=Sandbox.Project.Current.GetRootPath();var stage=System.IO.Path.Combine(root,"output/veridant/garden-grass-blades-v1/stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories).OrderBy(x=>x.EndsWith(".vmdl"))){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;''')
(out/'import.json').write_text(json.dumps({'path':str(p)}));(out/'compile.json').write_text(json.dumps({'path':res+'/grass.vmdl','full':True}));(out/'spawn.json').write_text(json.dumps({'model':res+'/grass.vmdl','name':'South garden short grass blades - review','position':'-1285,-920,0'}))
(out/'checks.json').write_text(json.dumps({'tufts':len(placements),'bounds_plan':[667,1177,-1345,-1222],'collision':False,'source':'models/grass/grass_tuft.vmdl','height_inches':[2.65,3.82]},indent=2));print((out/'checks.json').read_text())
