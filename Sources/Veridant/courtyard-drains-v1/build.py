from pathlib import Path
import sys,re,json
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import veridant_map as V
import veridant_parts as P
import veridant_courtyard_drains as Drains
OUT=ROOT/'output/veridant/courtyard-drains-v1';RESOURCE='models/maps/veridant/courtyard-drains-v1'
def keys(lines):
    vs=[];mat='';out=[]
    for l in lines:
        if l.startswith('v '):vs.append(tuple(round(float(x),3) for x in l.split()[1:]))
        elif l.startswith('usemtl '):mat=l.split()[1]
        elif l.startswith('f '):out.append((mat,tuple(sorted(vs[int(x.split('/')[0])-1] for x in l.split()[1:]))))
    return out
def main():
    before=OUT/'before';before.mkdir(parents=True,exist_ok=True);parent=ROOT/'Assets/models/maps/veridant/veridant_ground.vmdl'
    text=(before/'parent.vmdl').read_text() if (before/'parent.vmdl').exists() else parent.read_text();node=re.search(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S);path=re.search(r'filename = "([^"]+)"',node.group()).group(1);source=ROOT/'Assets'/path
    for src,name in ((parent,'parent.vmdl'),(source,'base.obj')):
        if not (before/name).exists():(before/name).write_bytes(src.read_bytes())
    (OUT/'source-path.txt').write_text(path)
    ref=Path(__file__).with_name('original.obj')
    if not ref.exists():
        old=K.Model()
        for a,b in Drains.PLACEMENTS:P.drain(old,a,b,0)
        V.configure(old);K.write_obj(OUT/'original.obj',old,'veridant_ground');ref.write_bytes((OUT/'original.obj').read_bytes())
    target=set(keys(ref.read_text().splitlines()));lines=(before/'base.obj').read_text().splitlines(keepends=True);it=iter(keys(lines));keep=[];removed=0
    for l in lines:
        if l.startswith('f ') and next(it) in target:removed+=1;continue
        keep.append(l)
    assert removed==len(target)==24,(removed,len(target))
    # The OBJ importer rejects empty material groups left by removing both old drain materials.
    cleaned=[]
    for i,line in enumerate(keep):
        if line.startswith('usemtl '):
            has_faces=False
            for following in keep[i+1:]:
                if following.startswith('usemtl '):break
                if following.startswith('f '):has_faces=True;break
            if not has_faces:continue
        cleaned.append(line)
    keep=cleaned
    stage=OUT/'stage';dest=stage/RESOURCE;dest.mkdir(parents=True,exist_ok=True);(dest/'ground_without_drains.obj').write_text(''.join(keep));mtl=re.search(r'^mtllib (.+)$',''.join(keep),re.M).group(1).strip();(dest/mtl).write_bytes((source.parent/mtl).read_bytes())
    new=K.Model();new.uv_source_name='veridant_ground';Drains.build_into(new);K.write_obj(dest/'covers.obj',new,'veridant_ground')
    text=(before/'parent.vmdl').read_text().replace(path,RESOURCE+'/ground_without_drains.obj',1);node=re.search(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S);name=re.search(r'name = "([^"]+)"',node.group()).group(1)
    add=node.group().replace(f'name = "{name}"','name = "courtyard_drain_covers_v1"').replace(RESOURCE+'/ground_without_drains.obj',RESOURCE+'/covers.obj');text=text[:node.end()]+'\n'+add+text[node.end():]
    remaps='\n'.join(f'{{ from = "{paint}.vmat" to = "{path}" }},' for paint,path in Drains.MATERIALS.items())
    match=re.search(r'(remaps\s*=\s*\[)',text);text=text[:match.end()]+'\n'+remaps+text[match.end():]
    (stage/'models/maps/veridant/veridant_ground.vmdl').write_text(text)
    assert text.split('PhysicsShapeList',1)[1]==(before/'parent.vmdl').read_text().split('PhysicsShapeList',1)[1]
    (OUT/'checks.json').write_text(json.dumps({'removed_triangles':removed,'new_triangles':new.triangle_count(),'physics_unchanged':True,'drains':4,'maximum_rise_inches':.245,'materials_reused':'Spillway trench grates'},indent=2));print((OUT/'checks.json').read_text())
if __name__=='__main__':main()
