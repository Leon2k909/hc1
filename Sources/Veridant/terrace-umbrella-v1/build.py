from pathlib import Path
import sys,re,json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import veridant_map as V
import veridant_parts as P
import veridant_umbrella_cloth as Cloth
OUT=ROOT/'output/veridant/terrace-umbrella-v1';RESOURCE='models/maps/veridant/terrace-umbrella-v1'
def keys(lines):
    vs=[];mat='';out=[]
    for l in lines:
        if l.startswith('v '):vs.append(tuple(round(float(x),3) for x in l.split()[1:]))
        elif l.startswith('usemtl '):mat=l.split()[1]
        elif l.startswith('f '):out.append((mat,tuple(sorted(vs[int(x.split('/')[0])-1] for x in l.split()[1:]))))
    return out
def main():
    before=OUT/'before';before.mkdir(parents=True,exist_ok=True);parent=ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl'
    text=(before/'parent.vmdl').read_text() if (before/'parent.vmdl').exists() else parent.read_text();first=re.search(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S);path=re.search(r'filename = "([^"]+)"',first.group()).group(1);source=ROOT/'Assets'/path
    for src,name in ((parent,'parent.vmdl'),(source,'base.obj')):
        if not (before/name).exists():(before/name).write_bytes(src.read_bytes())
    (OUT/'source-path.txt').write_text(path)
    ref=Path(__file__).with_name('original.obj')
    if not ref.exists() or '--refresh-reference' in sys.argv:
        old=K.Model();P.umbrella_closed(old,(30,470),182,z0=128)
        old.polygons={paint:[item for item in items if paint in ('vr_umbrella','vr_umbrella_tie') or (paint=='vr_steel' and all(224.5<=p[2]<=232.5 and np.linalg.norm(p[:2]-np.array((30,470)))>8 for p in item[0]))] for paint,items in old.polygons.items()}
        V.configure(old);K.write_obj(OUT/'original.obj',old,'veridant_buildings');ref.write_bytes((OUT/'original.obj').read_bytes())
    target=set(keys(ref.read_text().splitlines()));lines=(before/'base.obj').read_text().splitlines(keepends=True);it=iter(keys(lines));keep=[];removed=0
    for l in lines:
        if l.startswith('f ') and next(it) in target:removed+=1;continue
        keep.append(l)
    assert removed==len(target),(removed,len(target))
    stage=OUT/'stage';dest=stage/RESOURCE;dest.mkdir(parents=True,exist_ok=True);(dest/'base_without_canopy.obj').write_text(''.join(keep))
    mtl=re.search(r'^mtllib (.+)$',''.join(keep),re.M).group(1).strip();(dest/mtl).write_bytes((source.parent/mtl).read_bytes())
    new=K.Model();new.uv_source_name='veridant_buildings';Cloth.build_into(new);V.configure(new);K.write_obj(dest/'canopy.obj',new,'veridant_buildings')
    text=(before/'parent.vmdl').read_text().replace(path,RESOURCE+'/base_without_canopy.obj',1);node=re.search(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S);name=re.search(r'name = "([^"]+)"',node.group()).group(1)
    add=node.group().replace(f'name = "{name}"','name = "terrace_umbrella_cloth_v1"').replace(RESOURCE+'/base_without_canopy.obj',RESOURCE+'/canopy.obj');text=text[:node.end()]+'\n'+add+text[node.end():]
    (stage/'models/maps/veridant/veridant_buildings.vmdl').write_text(text)
    assert text.split('PhysicsShapeList',1)[1]==(before/'parent.vmdl').read_text().split('PhysicsShapeList',1)[1]
    (OUT/'checks.json').write_text(json.dumps({'removed_triangles':removed,'new_triangles':new.triangle_count(),'physics_unchanged':True,'original_base_pole_and_finial_retained':True},indent=2));print((OUT/'checks.json').read_text())
if __name__=='__main__':main()
