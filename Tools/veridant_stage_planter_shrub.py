"""Replace precisely one authored olive in the live foliage mesh."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import map_kit as K
import veridant_parts as P
import veridant_map as M
import veridant_planter_shrub as S
from veridant_stage_stone_pine import parsed,face_keys
from railhead_stage_extinguisher import sha
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/olive-v2'
STAGE=OUT/'stage-v4-active'


def main():
    assert not STAGE.exists();STAGE.mkdir()
    inputs={p:sha(ROOT/p) for p in ('Tools/veridant_planter_shrub.py','Tools/veridant_stage_planter_shrub.py',
        'Tools/veridant_map.py','Tools/map_kit.py','Tools/riverdale_parts.py',
        'Sources/Veridant/planter-shrub-v1/legacy-olive.py.txt','Sources/Veridant/planter-shrub-v1/beech-source.json')}
    ns=dict(vars(P));exec((ROOT/'Sources/Veridant/planter-shrub-v1/legacy-olive.py.txt').read_text(),ns)
    old=K.Model();ns['olive'](old,(-470.,740.,148.),95,seed=32)
    new=K.Model();S.build_into(new)
    M.configure(old);M.configure(new)
    assert not old.boxes and not old.hulls and not new.boxes and not new.hulls
    K.write_obj(STAGE/'old-tree.obj',old,'veridant_foliage')
    K.write_obj(STAGE/'new-tree.obj',new,'veridant_foliage')
    old_lines,old_vertices,_=parsed((STAGE/'old-tree.obj').read_text())
    wanted=Counter(key for _,key in face_keys(old_lines,old_vertices))
    model=Path('Assets/models/maps/veridant/pergola-flowers-v2/foliage-base.obj')
    source=ROOT/model;before=sha(source)
    lines,vertices,counts=parsed(source.read_text())
    removed=set()
    for index,key in face_keys(lines,vertices):
        if wanted[key]:wanted[key]-=1;removed.add(index)
    assert not sum(wanted.values()) and len(removed)==old.triangle_count(),(len(removed),old.triangle_count())
    new_lines,_,_=parsed((STAGE/'new-tree.obj').read_text())
    extra=[]
    for line in new_lines:
        if line.startswith(('v ','vt ','vn ','usemtl ')):extra.append(line)
        elif line.startswith('f '):
            tokens=['/'.join(str(int(part)+offset) for part,offset in zip(token.split('/'),counts)) for token in line.split()[1:]]
            extra.append('f '+' '.join(tokens)+'\n')
    retained=''.join(line for i,line in enumerate(lines) if i not in removed).encode()
    addition=''.join(extra).encode()
    target=STAGE/model;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(retained+addition)
    assert target.read_bytes()[:-len(addition)]==retained
    # Appending the tables preserves every original vertex/UV/normal index.
    assert all(sum(line.startswith(prefix) for line in lines)==count for prefix,count in zip(('v ','vt ','vn '),counts))
    mtl=model.parent/next(line.split(maxsplit=1)[1].strip() for line in lines if line.startswith('mtllib '))
    vmdl=Path('Assets/models/maps/veridant/veridant_foliage.vmdl')
    old_mtl=(ROOT/mtl).read_bytes();old_vmdl=(ROOT/vmdl).read_text()
    new_mtl=old_mtl+b'\n'+(STAGE/'new-tree.mtl').read_bytes()
    (STAGE/mtl).write_bytes(new_mtl)
    remaps=''.join(f'{{ from = "{paint}.vmat" to = "{resource}" }},\n' for paint,resource in new.material_overrides.items()
                   if f'from = "{paint}.vmat"' not in old_vmdl)
    at=old_vmdl.index('[',old_vmdl.index('remaps ='))+1
    new_vmdl=old_vmdl[:at]+'\n'+remaps+old_vmdl[at:]
    a,b=span(old_vmdl,'_class = "RenderMeshList"');c,d=span(new_vmdl,'_class = "RenderMeshList"')
    assert old_vmdl[a:b]==new_vmdl[c:d] and 'PhysicsShapeList' not in old_vmdl
    assert model.relative_to('Assets').as_posix() in old_vmdl[a:b]
    (STAGE/vmdl).write_text(new_vmdl)
    material_dir=Path('Assets/materials/veridant/planter-shrub-v1')
    S.write_materials(STAGE/material_dir)
    files={}
    for relative in (model,mtl,vmdl,*[p.relative_to(STAGE) for p in (STAGE/material_dir).iterdir()]):
        original=ROOT/relative;digest=sha(original) if original.exists() else None
        backup=STAGE/'before'/relative
        if digest:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,backup);assert sha(backup)==digest
        files[relative.as_posix()]={'before':digest,'after':sha(STAGE/relative),
            'source':(STAGE/relative).relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if digest else None}
    assert sha(source)==before
    for path,digest in inputs.items():assert sha(ROOT/path)==digest,path
    manifest={'revision':'veridant-garden-planter-shrub-v1','source_sha256':inputs,'files':files,
        'old_triangles_removed':len(removed),'new_triangles':new.triangle_count(),
        'plant_position_plan':[-470,740,148],'plants_changed':1,'scene_unwritten':True,
        'physics_unchanged':True,'retained_obj_bytes_exact':True,'original_indices_preserved':True,
        'retained_obj_sha256':hashlib.sha256(retained).hexdigest(),
        'source_model':json.loads(S.SOURCE.read_text())['SourceModel'],
        'source_material':new.material_overrides[S.LEAVES],'native_mesh_scale':.43,'root_embed_inches':1.0}
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','source_sha256')}))


if __name__=='__main__':main()
