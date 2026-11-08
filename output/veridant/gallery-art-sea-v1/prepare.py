from pathlib import Path
from collections import Counter
import re,sys,json,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,veridant_map as V,veridant_parts as P,veridant_gallery_art_sea as B
OUT=ROOT/'output/veridant/gallery-art-sea-v1';RES='models/maps/veridant/gallery-art-sea-v1';SHARED='models/props/shared/gallery_art_sea_v1'
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
P.art(old,'art_5',(-703.8,-370,192),(0,1,0),50)
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
m=K.Model();m.uv_source_name='veridant_buildings';B.build_into(m);V.configure(m);K.write_model(stage/SHARED,SHARED,'art',m)
original=K.Model();original.uv_source_name='veridant_buildings';P.art(original,'art_5',(0,0,0),(0,1,0),50);V.configure(original);oldres='models/props/shared/gallery_art_sea_original_v1';K.write_model(stage/oldres,oldres,'art_original',original)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/lounge-tables');ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/gallery-art-sea-v1");var live=System.IO.Path.Combine(root,"Assets/models/maps/veridant/veridant_buildings.vmdl");if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"before/parent.vmdl")))throw new Exception("Parent changed");var stage=System.IO.Path.Combine(o,"stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories).OrderBy(x=>x.EndsWith(".vmdl"))){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;'''
p=ex/'import.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}))
for name,path in [('new',SHARED+'/art.vmdl'),('original',oldres+'/art_original.vmdl')]:
    (OUT/(name+'-compile.json')).write_text(json.dumps({'path':path,'full':True}))
for i,y in enumerate((703.8,)):(OUT/f'spawn-{i}.json').write_text(json.dumps({'model':SHARED+'/art.vmdl','name':'Gallery sea painting '+str(i+1),'position':f'-370,{y},192'}))
(OUT/'before.png').write_bytes(Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.06.16.22.10.png').read_bytes())
(OUT/'checks.json').write_text(json.dumps({'removed_triangles':sum(removed.values()),'new_model_triangles':m.triangle_count(),'physics_unchanged':True},indent=2));print((OUT/'checks.json').read_text())

import shutil
md=OUT/'stage/materials/veridant/gallery-art-sea-v1';md.mkdir(parents=True,exist_ok=True)
shutil.copy2(Path('C:/Users/leon2/.codex/generated_images/01a1ac9b-89d5-7aa3-8fe2-8ad23ca89dc1/exec-f451df6a-7bd1-4dd5-83d5-e61b3b579dff.png'),md/'sea.png')
(md/'sea.vmat').write_text('Layer0\n{\n shader "shaders/complex.shader"\n TextureColor "materials/veridant/gallery-art-sea-v1/sea.png"\n TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "[0.9 0.9 0.9 0]"\n g_flMetalness "0"\n g_vColorTint "[1 1 1 1]"\n}\n')
