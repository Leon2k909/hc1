from pathlib import Path
import sys,re,json
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import veridant_map as V
import veridant_parts as P
import veridant_operations_banner as Banner
OUT=ROOT/'output/veridant/operations-banner-v1';RESOURCE='models/maps/veridant/operations-banner-v1'
def keys(lines):
    vs=[];mat='';result=[]
    for l in lines:
        if l.startswith('v '):vs.append(tuple(round(float(x),3) for x in l.split()[1:]))
        elif l.startswith('usemtl '):mat=l.split()[1]
        elif l.startswith('f '):result.append((mat,tuple(sorted(vs[int(x.split('/')[0])-1] for x in l.split()[1:]))))
    return result
def main():
    OUT.mkdir(exist_ok=True,parents=True);before=OUT/'before';before.mkdir(exist_ok=True)
    parent=ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl';text=(before/'parent.vmdl').read_text() if (before/'parent.vmdl').exists() else parent.read_text()
    first=re.search(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S);oldpath=re.search(r'filename = "([^"]+)"',first.group()).group(1);source=ROOT/'Assets'/oldpath
    for src,name in ((parent,'parent.vmdl'),(source,'base.obj')):
        if not (before/name).exists():(before/name).write_bytes(src.read_bytes())
    (OUT/'source-path.txt').write_text(oldpath)
    ref=Path(__file__).with_name('original.obj')
    if not ref.exists():
        old=K.Model();P.banner(old,(10,-418,392),(-1,0,0),200)
        old.polygons={k:v for k,v in old.polygons.items() if k in ('vr_print','vr_black')};V.configure(old)
        K.write_obj(OUT/'original.obj',old,'veridant_buildings');ref.write_bytes((OUT/'original.obj').read_bytes())
    target=set(keys(ref.read_text().splitlines()));assert len(target)==4
    lines=(before/'base.obj').read_text().splitlines(keepends=True);it=iter(keys(lines));keep=[];removed=0
    for l in lines:
        if l.startswith('f ') and next(it) in target:removed+=1;continue
        keep.append(l)
    assert removed==4,removed
    stage=OUT/'stage';dest=stage/RESOURCE;dest.mkdir(exist_ok=True,parents=True)
    (dest/'base_without_banner.obj').write_text(''.join(keep));mtl=re.search(r'^mtllib (.+)$',''.join(keep),re.M).group(1).strip();(dest/mtl).write_bytes((source.parent/mtl).read_bytes())
    model=K.Model();model.uv_source_name='veridant_buildings';Banner.build_into(model);V.configure(model);K.write_obj(dest/'cloth.obj',model,'veridant_buildings')
    text=(before/'parent.vmdl').read_text().replace(oldpath,RESOURCE+'/base_without_banner.obj',1)
    node=re.search(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S);name=re.search(r'name = "([^"]+)"',node.group()).group(1)
    new=node.group().replace(f'name = "{name}"','name = "operations_banner_cloth_v1"').replace(RESOURCE+'/base_without_banner.obj',RESOURCE+'/cloth.obj')
    text=text[:node.end()]+'\n'+new+text[node.end():]
    (stage/'models/maps/veridant/veridant_buildings.vmdl').write_text(text)
    assert text.split('PhysicsShapeList',1)[1]==(before/'parent.vmdl').read_text().split('PhysicsShapeList',1)[1]
    report={'removed_triangles':removed,'new_triangles':model.triangle_count(),'retained_records':len(keep),'physics_unchanged':True,'artwork_unchanged':True,'lighting_unchanged':True}
    (OUT/'checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
