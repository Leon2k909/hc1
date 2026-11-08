from pathlib import Path
from collections import Counter
import sys,re,json
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,veridant_map as V,veridant_parts as P,veridant_east_lantern as B
OUT=ROOT/'output/veridant/all-lanterns-v1';stage=OUT/'stage';stage.mkdir(parents=True,exist_ok=True)
RES='models/maps/veridant/all-lanterns-v1';shared='models/props/shared/veridant_framed_lanterns_v1'
groups={
 'veridant_buildings':[((-164,240,128),96),((-92,724,128),96),((240,580,128),96)],
 'veridant_dress':[((-686,260,128),96),((-686,680,128),96),((-600,960,128),96)]
 +[((-1690,n,0),140) for n in (-1080,-780,-480,-180,120,420,720,950)]
 +[((e,n,0),120) for e,n in ((-300,-760),(300,-760),(900,-760),(1500,-800),(-600,-1300),(1100,-1300))]
 +[((1894,n+s*100,150),30) for n in (-300,500) for s in (-1,1)]
 +[((e,n,0),140) for e,n in ((1500,-640),(1500,950),(1820,150))]}
def keys(lines):
 vs=[];mat='';out=[]
 for l in lines:
  if l.startswith('v '):vs.append(tuple(round(float(x),3) for x in l.split()[1:]))
  elif l.startswith('usemtl '):mat=l.split()[1]
  elif l.startswith('f '):out.append((mat,tuple(sorted(vs[int(x.split('/')[0])-1] for x in l.split()[1:]))))
 return out
checks={};new=K.Model();guards=[]
for name,fixtures in groups.items():
 before=OUT/'before'/name;before.mkdir(parents=True,exist_ok=True)
 parent=ROOT/'Assets/models/maps/veridant'/f'{name}.vmdl';text=parent.read_text();(before/'parent.vmdl').write_bytes(parent.read_bytes());guards.append(name)
 old=K.Model()
 for i,(base,h) in enumerate(fixtures):
  if name=='veridant_dress' and i>=len(fixtures)-3:
   # The three forecourt shafts already live in separate scene props.
   head=K.Model();P.lantern_post(head,'Original',base,h,light=False)
   shaft=K.Model();P.cylinder(shaft,base[:2],4.5,0,10,'vr_steel',10,top='vr_steel');P.cylinder(shaft,base[:2],2.2,10,124,'vr_steel',8)
   V.configure(head);V.configure(shaft)
   K.write_obj(OUT/'head.obj',head,name);K.write_obj(OUT/'shaft.obj',shaft,name)
   skip=Counter(keys((OUT/'shaft.obj').read_text().splitlines()))
   # Geometry filtering below uses a separate target counter for these heads.
   if 'headtargets' not in locals():headtargets=Counter()
   headtargets+=Counter(keys((OUT/'head.obj').read_text().splitlines()))-skip
  else:P.lantern_post(old,'Original '+str(i),base,h,light=False)
  B.build_one(new,base,h)
 V.configure(old);K.write_obj(OUT/'old.obj',old,name);target=Counter(keys((OUT/'old.obj').read_text().splitlines()))
 if name=='veridant_dress':target+=headtargets
 removed=Counter();dest=stage/RES/name;dest.mkdir(parents=True,exist_ok=True)
 for i,path in enumerate(dict.fromkeys(re.findall(r'filename = "([^"]+\.obj)"',text))):
  src=ROOT/'Assets'/path;lines=src.read_text().splitlines(keepends=True);it=iter(keys(lines));keep=[];count=0
  for line in lines:
   if line.startswith('f '):
    key=next(it)
    if key in target:removed[key]+=1;count+=1;continue
   keep.append(line)
  if not count:continue
  (before/f'{i}.obj').write_bytes(src.read_bytes());fn=f'without_lanterns_{i}.obj';(dest/fn).write_text(''.join(keep))
  mtl=re.search(r'^mtllib (.+)$',''.join(keep),re.M).group(1).strip();(dest/mtl).write_bytes((src.parent/mtl).read_bytes());text=text.replace(path,RES+'/'+name+'/'+fn)
 assert removed==target,(name,sum(removed.values()),sum(target.values()),list((target-removed).items())[:2])
 assert text.split('PhysicsShapeList',1)[1]==parent.read_text().split('PhysicsShapeList',1)[1]
 (stage/'models/maps/veridant'/f'{name}.vmdl').parent.mkdir(parents=True,exist_ok=True);(stage/'models/maps/veridant'/f'{name}.vmdl').write_text(text)
 checks[name]={'fixtures':len(fixtures),'removed_triangles':sum(removed.values()),'physics_unchanged':True}
V.configure(new);K.write_model(stage/shared,shared,'lanterns',new)
for h in (30,96,120,140):
 m=K.Model();P.lantern_post(m,'Original retained',(0,0,0),h,light=False);V.configure(m)
 res=f'models/props/shared/veridant_lantern_original_h{h}';K.write_model(stage/res,res,'lantern',m)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/all-lanterns');ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/all-lanterns-v1");foreach(var n in new[]{"veridant_buildings","veridant_dress"}){if(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"Assets/models/maps/veridant",n+".vmdl"))!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"before",n,"parent.vmdl")))throw new Exception("Parent changed "+n);}var stage=System.IO.Path.Combine(o,"stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories).OrderBy(x=>x.EndsWith(".vmdl"))){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;'''
p=ex/'import.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}))
(OUT/'compile.json').write_text(json.dumps({'path':shared+'/lanterns.vmdl','full':True}))
(OUT/'spawn.json').write_text(json.dumps({'model':shared+'/lanterns.vmdl','name':'Veridant remaining framed lanterns','position':'0,0,0'}))
(OUT/'checks.json').write_text(json.dumps(checks,indent=2));print(checks)
