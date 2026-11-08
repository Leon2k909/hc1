from pathlib import Path
import sys,re,json,hashlib
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import veridant_map as V
import veridant_parts as P
import veridant_reception_desk as Desk
OUT=ROOT/'output/veridant/reception-desk-v1'
RESOURCE='models/maps/veridant/reception-desk-v1'

def keys(lines):
    vertices=[];mat='';result=[]
    for line in lines:
        if line.startswith('v '):vertices.append(tuple(round(float(x),3) for x in line.split()[1:]))
        elif line.startswith('usemtl '):mat=line.split()[1]
        elif line.startswith('f '):result.append((mat,tuple(sorted(vertices[int(x.split('/')[0])-1] for x in line.split()[1:]))))
    return result

def main():
    OUT.mkdir(exist_ok=True,parents=True);before=OUT/'before';before.mkdir(exist_ok=True)
    source=ROOT/'Assets/models/maps/veridant/lounger-v2/veridant_buildings-base.obj'
    parent=ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl'
    for src in (source,parent):
        dst=before/src.name
        if not dst.exists():dst.write_bytes(src.read_bytes())
    path=Path(__file__).with_name('original.obj')
    targetkeys=set(keys(path.read_text().splitlines()))
    assert len(targetkeys)==24
    lines=(before/source.name).read_text().splitlines(keepends=True);allkeys=iter(keys(lines));keep=[];removed=0
    for line in lines:
        if line.startswith('f ') and next(allkeys) in targetkeys:removed+=1;continue
        keep.append(line)
    assert removed==24,removed
    stage=OUT/'stage';dest=stage/RESOURCE;dest.mkdir(exist_ok=True,parents=True)
    (dest/'buildings_without_desk.obj').write_text(''.join(keep))
    mtl=re.search(r'^mtllib (.+)$',''.join(keep),re.M).group(1).strip();(dest/mtl).write_bytes((source.parent/mtl).read_bytes())
    model=K.Model();model.uv_source_name='veridant_buildings';Desk.build_into(model,False);V.configure(model)
    model.material_overrides['vr_table_honed']='materials/veridant/table-v2/honed.vmat'
    model.tile_overrides['vr_table_honed']=192
    K.write_obj(dest/'desk.obj',model,'veridant_buildings')
    text=(before/parent.name).read_text();text=text.replace('models/maps/veridant/lounger-v2/veridant_buildings-base.obj',RESOURCE+'/buildings_without_desk.obj',1)
    node=re.search(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S)
    newnode=node.group().replace('name = "veridant_buildings"','name = "reception_desk_v1"').replace(RESOURCE+'/buildings_without_desk.obj',RESOURCE+'/desk.obj')
    text=text[:node.end()]+'\n'+newnode+text[node.end():]
    (stage/'models/maps/veridant/veridant_buildings.vmdl').write_text(text)
    assert text.split('PhysicsShapeList',1)[1]==(before/parent.name).read_text().split('PhysicsShapeList',1)[1]
    (OUT/'checks.json').write_text(json.dumps({'removed_triangles':removed,'new_triangles':model.triangle_count(),'physics_unchanged':True,'preserved_records':len(keep)},indent=2))
    print((OUT/'checks.json').read_text())

if __name__=='__main__':main()
