from pathlib import Path
from collections import Counter
import sys,re,json,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,veridant_map as V,veridant_parts as P
OUT=ROOT/'output/veridant/colonnade-tree-fit-v1';RESOURCE='models/maps/veridant/colonnade-tree-fit-v1'
parent=ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl';text=parent.read_text();before=OUT/'before';before.mkdir(exist_ok=True)
(before/'parent.vmdl').write_bytes(parent.read_bytes())
def faces(lines):
    vs=[];mat='';out=[]
    for i,l in enumerate(lines):
        if l.startswith('v '):vs.append(tuple(round(float(x),3) for x in l.split()[1:]))
        elif l.startswith('usemtl '):mat=l.split()[1]
        elif l.startswith('f '):
            ids=[int(x.split('/')[0])-1 for x in l.split()[1:]]
            out.append((i,(mat,tuple(sorted(vs[j] for j in ids))),ids))
    return out
targets={};counts=Counter()
for name,delta in [('tree',(-7,-7.5,-1.5)),('uplight',(-22,-21,0))]:
    m=K.Model()
    if name=='tree':P.olive(m,(-226,20,22),96,seed=7,spread=.8)
    else:P.uplight(m,'Original colonnade fixture',(-222,20,22.1),light=False)
    V.configure(m);path=OUT/(name+'-original.obj');K.write_obj(path,m,'veridant_buildings')
    for _,key,_ in faces(path.read_text().splitlines()):
        targets[key]=(name,tuple(K.to_world(delta)[[1,2,0]]));counts[name]+=1
stage=OUT/'stage';dest=stage/RESOURCE;dest.mkdir(parents=True,exist_ok=True)
matched=Counter();manifest=[]
for index,path in enumerate(dict.fromkeys(re.findall(r'filename = "([^"]+\.obj)"',text))):
    src=ROOT/'Assets'/path
    lines=src.read_text().splitlines(keepends=True);fs=faces(lines);selected={};unselected=set()
    for _,key,ids in fs:
        if key in targets:
            name,delta=targets[key];matched[name]+=1
            for j in ids:
                assert j not in selected or selected[j]==delta;selected[j]=delta
        else:unselected.update(ids)
    if not selected:continue
    assert not set(selected)&unselected,'Shared vertices would move other geometry'
    (before/f'{index}.obj').write_bytes(src.read_bytes());vertex=0
    for i,line in enumerate(lines):
        if line.startswith('v '):
            if vertex in selected:
                xyz=[float(x) for x in line.split()[1:]]
                lines[i]='v '+' '.join(f'{x+d:.6f}' for x,d in zip(xyz,selected[vertex]))+'\n'
            vertex+=1
    filename=f'tree_fit_{index}.obj';(dest/filename).write_text(''.join(lines))
    mtl=re.search(r'^mtllib (.+)$',''.join(lines),re.M).group(1).strip();(dest/mtl).write_bytes((src.parent/mtl).read_bytes())
    manifest.append({'path':path,'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
    text=text.replace(path,RESOURCE+'/'+filename)
assert matched==counts,(matched,counts)
assert text.split('PhysicsShapeList',1)[1]==parent.read_text().split('PhysicsShapeList',1)[1]
(stage/'models/maps/veridant/veridant_buildings.vmdl').write_text(text)
(OUT/'manifest.json').write_text(json.dumps(manifest));(OUT/'checks.json').write_text(json.dumps({'moved_triangles':dict(matched),'physics_unchanged':True,'uvs_unchanged':True},indent=2))
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/colonnade-tree-fit');ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/colonnade-tree-fit-v1");var live=System.IO.Path.Combine(root,"Assets/models/maps/veridant/veridant_buildings.vmdl");if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"before/parent.vmdl")))throw new Exception("Parent changed since staging");foreach(var item in System.Text.Json.JsonDocument.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(o,"manifest.json"))).RootElement.EnumerateArray()){var bytes=System.IO.File.ReadAllBytes(System.IO.Path.Combine(root,"Assets",item.GetProperty("path").GetString()));var hash=System.Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes)).ToLowerInvariant();if(hash!=item.GetProperty("sha256").GetString())throw new Exception("Source changed since staging");}var stage=System.IO.Path.Combine(o,"stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories).OrderBy(x=>x.EndsWith(".vmdl"))){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;'''
p=ex/'import.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}));(OUT/'compile.json').write_text(json.dumps({'path':'models/maps/veridant/veridant_buildings.vmdl','full':True}))
(OUT/'before.png').write_bytes(Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.06.17.15.22.png').read_bytes())
print(dict(matched))

import shutil
oldroot=ROOT/'output/veridant/colonnade-planter-reuse-v1/stage/models/props/shared/colonnade_planter_v1'
alt='models/props/shared/colonnade_bronze_alternative_v1';dest=stage/alt;dest.mkdir(parents=True,exist_ok=True)
for f in oldroot.iterdir():
    if not f.is_file():continue
    data=f.read_bytes()
    if f.suffix=='.vmdl':
        txt=data.decode();assert 'rhp_bronze' in txt;data=txt.replace('models/props/shared/colonnade_planter_v1',alt).encode()
    (dest/f.name).write_bytes(data)
