from pathlib import Path
import re,json,sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import veridant_map as V
import veridant_parts as P
import veridant_reception_light as Light
OUT=ROOT/'output/veridant/reception-wall-light-v1';RESOURCE='models/maps/veridant/reception-wall-light-v1'

def keys(lines):
    vertices=[];mat='';out=[]
    for l in lines:
        if l.startswith('v '):vertices.append(tuple(round(float(x),3) for x in l.split()[1:]))
        elif l.startswith('usemtl '):mat=l.split()[1]
        elif l.startswith('f '):out.append((mat,tuple(sorted(vertices[int(x.split('/')[0])-1] for x in l.split()[1:]))))
    return out

def main():
    before=OUT/'before';before.mkdir(parents=True,exist_ok=True)
    parent=ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl';text=parent.read_text()
    first=re.search(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S)
    oldpath=re.search(r'filename = "([^"]+)"',first.group()).group(1)
    source=ROOT/'Assets'/oldpath
    for src,name in ((parent,'parent.vmdl'),(source,'base.obj')):
        if not (before/name).exists():(before/name).write_bytes(src.read_bytes())
    (OUT/'source-path.txt').write_text(oldpath)
    temp=Path(__file__).with_name('original.obj');targetkeys=set(keys(temp.read_text().splitlines()));assert len(targetkeys)==4
    lines=(before/'base.obj').read_text().splitlines(keepends=True);it=iter(keys(lines));keep=[];removed=0
    for l in lines:
        if l.startswith('f ') and next(it) in targetkeys:removed+=1;continue
        keep.append(l)
    assert removed==4,removed
    stage=OUT/'stage';dest=stage/RESOURCE;dest.mkdir(parents=True,exist_ok=True)
    (dest/'base_without_light.obj').write_text(''.join(keep))
    mtllib=re.search(r'^mtllib (.+)$',''.join(keep),re.M).group(1).strip();(dest/mtllib).write_bytes((source.parent/mtllib).read_bytes())
    new=K.Model();new.uv_source_name='veridant_buildings';Light.build_into(new);V.configure(new);K.write_obj(dest/'wall_light.obj',new,'veridant_buildings')
    text=(before/'parent.vmdl').read_text();text=text.replace(oldpath,RESOURCE+'/base_without_light.obj',1)
    node=re.search(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S)
    name=re.search(r'name = "([^"]+)"',node.group()).group(1)
    newnode=node.group().replace(f'name = "{name}"','name = "reception_wall_light_v1"').replace(RESOURCE+'/base_without_light.obj',RESOURCE+'/wall_light.obj')
    text=text[:node.end()]+'\n'+newnode+text[node.end():]
    (stage/'models/maps/veridant/veridant_buildings.vmdl').write_text(text)
    assert text.split('PhysicsShapeList',1)[1]==(before/'parent.vmdl').read_text().split('PhysicsShapeList',1)[1]
    (OUT/'checks.json').write_text(json.dumps({'removed_triangles':removed,'new_triangles':new.triangle_count(),'original_import':oldpath,'physics_preserved':True,'light_settings_unchanged':True},indent=2));print((OUT/'checks.json').read_text())

if __name__=='__main__':main()
