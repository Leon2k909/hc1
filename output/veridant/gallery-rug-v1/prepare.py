from pathlib import Path
from collections import Counter
import re,sys,json,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,veridant_map as V,veridant_parts as P,veridant_gallery_rug as B
OUT=ROOT/'output/veridant/gallery-rug-v1';RES='models/maps/veridant/gallery-rug-v1';SHARED='models/props/shared/gallery_rug_v1'
before=OUT/'before';before.mkdir(exist_ok=True);stage=OUT/'stage';dest=stage/RES;dest.mkdir(parents=True,exist_ok=True)
parent=ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl';text=parent.read_text();(before/'parent.vmdl').write_bytes(parent.read_bytes())
def keys(lines):
    vs=[];mat='';result=[]
    for l in lines:
        if l.startswith('v '):vs.append(tuple(round(float(x),3) for x in l.split()[1:]))
        elif l.startswith('usemtl '):mat=l.split()[1]
        elif l.startswith('f '):result.append((mat,tuple(sorted(vs[int(x.split('/')[0])-1] for x in l.split()[1:]))))
    return result
old=K.Model()
V.floor(old,-640,-300,-500,-260,128.2,'vr_rug')
V.configure(old);K.write_obj(OUT/'original.obj',old,'veridant_buildings');target=Counter(keys((OUT/'original.obj').read_text().splitlines()));removed=Counter();manifest=[]
for index,path in enumerate(dict.fromkeys(re.findall(r'filename = "([^"]+\.obj)"',text))):
    src=ROOT/'Assets'/path;lines=src.read_text().splitlines(keepends=True);it=iter(keys(lines));keep=[];count=0
    for line in lines:
        if line.startswith('f '):
            key=next(it)
            if key in target:removed[key]+=1;count+=1;continue
        keep.append(line)
    if not count:continue
    (before/f'{index}.obj').write_bytes(src.read_bytes());filename=f'base_without_tables_{index}.obj';(dest/filename).write_text(''.join(keep))
    mtl=re.search(r'^mtllib (.+)$',''.join(keep),re.M).group(1).strip();(dest/mtl).write_bytes((src.parent/mtl).read_bytes())
    manifest.append({'path':path,'sha256':hashlib.sha256(src.read_bytes()).hexdigest()});text=text.replace(path,RES+'/'+filename)
assert removed==target,(sum(removed.values()),sum(target.values()))
assert text.split('PhysicsShapeList',1)[1]==parent.read_text().split('PhysicsShapeList',1)[1]
(stage/'models/maps/veridant/veridant_buildings.vmdl').write_text(text)
m=K.Model();m.uv_source_name='veridant_buildings';B.build_into(m);V.configure(m);K.write_model(stage/SHARED,SHARED,'rug',m)
original=K.Model();original.uv_source_name='veridant_buildings';V.floor(original,-170,170,-120,120,0,'vr_rug');V.configure(original);oldres='models/props/shared/gallery_rug_original_v1';K.write_model(stage/oldres,oldres,'rug_original',original)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/lounge-tables');ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/gallery-rug-v1");var live=System.IO.Path.Combine(root,"Assets/models/maps/veridant/veridant_buildings.vmdl");if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"before/parent.vmdl")))throw new Exception("Parent changed");var stage=System.IO.Path.Combine(o,"stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories).OrderBy(x=>x.EndsWith(".vmdl"))){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;'''
p=ex/'import.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}))
for name,path in [('new',SHARED+'/rug.vmdl'),('original',oldres+'/rug_original.vmdl')]:
    (OUT/(name+'-compile.json')).write_text(json.dumps({'path':path,'full':True}))
for i,y in enumerate((470,)):(OUT/f'spawn-{i}.json').write_text(json.dumps({'model':SHARED+'/rug.vmdl','name':'Gallery woven rug '+str(i+1),'position':f'-380,{y},128.2'}))
(OUT/'before.png').write_bytes(Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.06.15.49.53.png').read_bytes())
(OUT/'checks.json').write_text(json.dumps({'removed_triangles':sum(removed.values()),'new_model_triangles':m.triangle_count(),'physics_unchanged':True},indent=2));print((OUT/'checks.json').read_text())

matdir=OUT/'stage/materials/veridant/gallery-rug-v1';matdir.mkdir(parents=True,exist_ok=True)
for name,tint in [('weave','[0.46 0.40 0.32 1]'),('binding','[0.16 0.13 0.10 1]'),('stripe','[0.30 0.25 0.19 1]')]:
    text=(ROOT/'Assets/materials/riverside/folded-tarp-v1/cloth.vmat').read_text().replace('[0.117647 0.27451 0.509804 1]',tint).replace('[0.72 0.72 0.72 0]','[0.98 0.98 0.98 0]')
    (matdir/(name+'.vmat')).write_text(text)
