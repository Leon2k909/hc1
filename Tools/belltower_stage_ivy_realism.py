"""Stage the ivy realism candidate separately; publish town geometry after review."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import numpy as np
import map_kit as K
import belltower_ivy_realism as I
import belltower_stage_ivy as S
import belltower_stage_long_beds as L
import belltower_compact_obj as C

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/ivy-realism-v3'
ORIGINAL=ROOT/'output/belltower/ivy-3d-v1/final/before'
RESOURCE='models/maps/belltower/ivy-realism-v3'
OLD={'ivy_leaf3d','ivy_stem3d'}
LIMIT=45000


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def chunks(model):
    current=K.Model();count=0
    for paint,polygons in model.polygons.items():
        for index,(points,normal) in enumerate(polygons):
            triangles=len(points)-2
            if count+triangles>LIMIT:
                yield current;current=K.Model();count=0
            new_index=len(current.polygons[paint])
            current.polygons[paint].append((points,normal))
            if (paint,index) in model.polygon_uvs:current.polygon_uvs[(paint,new_index)]=model.polygon_uvs[(paint,index)]
            if (paint,index) in model.polygon_normals:current.polygon_normals[(paint,new_index)]=model.polygon_normals[(paint,index)]
            current.material_overrides.update(model.material_overrides)
            current.tile_overrides.update(model.tile_overrides)
            count+=triangles
    if count:yield current


def blocks(text):
    for match in re.finditer(r'_class\s*=\s*"RenderMeshFile"',text):
        start=text.rfind('{',0,match.start());level=0
        for pos in range(start,len(text)):
            if text[pos]=='{':level+=1
            elif text[pos]=='}':
                level-=1
                if level==0:
                    yield start,pos+1,text[start:pos+1]
                    break


def remap_model(original,imports):
    updated=original
    for paint,path in I.MATERIALS.items():
        pattern=r'(\{\s*from = "'+re.escape(paint)+r'\.vmat" to = ")[^"]+("\s*\})'
        if re.search(pattern,updated):
            updated=re.sub(pattern,lambda m:m[1]+path+m[2],updated)
        else:
            anchor=next(l for l in updated.splitlines(keepends=True) if 'from = "ivy_leaf3d.vmat"' in l)
            indent=anchor[:len(anchor)-len(anchor.lstrip())]
            added=indent+f'{{ from = "{paint}.vmat" to = "{path}" }},\n'
            updated=updated.replace(anchor,added+anchor,1)
    replacements=[]
    for start,end,block in blocks(updated):
        path=re.search(r'filename = "([^"]+)"',block)[1]
        kind=next((k for k in imports if path.endswith('_'+k+'.obj')),None)
        if kind is None:continue
        parts=[]
        for new_path in imports[kind]:
            chunk=re.sub(r'filename = "[^"]+"',f'filename = "{new_path}"',block,count=1)
            chunk=re.sub(r'\bname = "[^"]+"',f'name = "{Path(new_path).stem}"',chunk,count=1)
            parts.append(chunk)
        replacements.append((start,end,',\n'.join(parts)))
    assert len(replacements)==2
    for start,end,value in reversed(replacements):updated=updated[:start]+value+updated[end:]
    # Every non-ivy import and the complete collision section remain exact.
    strip=lambda text:[b for a,z,b in blocks(text) if not any(k in b for k in ('ivy_climb','ivy_hang','ivy-realism-v3'))]
    assert strip(original)==strip(updated)
    physics=original[original.index('_class = "PhysicsShapeList"'):] if '_class = "PhysicsShapeList"' in original else None
    if physics is not None:assert updated.endswith(physics)
    return updated


def stage_materials(files):
    leaf=('"Layer0"\n{\n    shader "shaders/belltower_ivy_realism_v3.shader"\n'
        f'    TexturePlants "{I.ATLAS}"\n    F_ALPHA_TEST "1"\n'
        '    g_flAlphaTestReference "0.42"\n    g_flAntiAliasedEdgeStrength "1"\n}\n')
    wood=(ROOT/'Assets/materials/belltower/wood_planks_dark.vmat').read_text()
    stem=wood.replace('[0.83 0.73 0.6 1]','[1.02 0.98 0.86 1]')
    shoot=wood.replace('[0.83 0.73 0.6 1]','[0.63 1.06 0.49 1]')
    for relative,data in [
        ('Assets/'+I.ATLAS,(ROOT/'Sources/Belltower/ivy/leaf-atlas-v3.png').read_bytes()),
        ('Assets/'+I.MATERIALS[I.LEAF],leaf.encode()),
        ('Assets/'+I.MATERIALS[I.STEM],stem.encode()),
        ('Assets/'+I.MATERIALS[I.SHOOT],shoot.encode()),
        ('Assets/shaders/belltower_ivy_realism_v3.shader',(ROOT/'Sources/Belltower/ivy/ivy-realism-v3.shader').read_bytes())]:
        files[relative]=S.stage_file(relative,data)


def preview():
    S.OUT=OUT/'preview';S.STAGE=S.OUT/'stage'
    assert not (S.STAGE/'manifest.json').exists(),'Preserve the candidate revision.'
    manifest={'revision':'ivy-realism-v3-preview','files':{},'models':{},'source_sha256':{
        p:sha(ROOT/p) for p in ['Tools/belltower_ivy_realism.py','Tools/belltower_stage_ivy_realism.py',
            'Sources/Belltower/ivy/leaf-atlas-v3.png','Sources/Belltower/ivy/ivy-realism-v3.shader']},
        'scene_sha256':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
        'private_preview_only':True,'town_assets_not_modified':True,'collision_unchanged':True}
    stage_materials(manifest['files'])
    groups={};stats=[]
    for kind in ('ivy_climb','ivy_hang'):
        original=next((ORIGINAL/'Assets/models/maps/belltower/compiler-safe/west').glob('*_'+kind+'.obj'))
        model=K.Model()
        for points,normal in S.patches(original):
            row=I.build(model,points,normal,hanging=kind=='ivy_hang')
            stats.append({'kind':kind,'centre':np.mean(points,axis=0).tolist(),**row})
        groups[kind]=model
    manifest['patches_per_half']=stats
    for side in ('west','east'):
        imports={};totals=0
        for kind,model in groups.items():
            if side=='east':model=model.mirrored()
            pieces=[]
            for index,piece in enumerate(chunks(model)):
                resource=f'{RESOURCE}/{side}_{kind}_{index:03d}.obj'
                raw=OUT/'pieces'/Path(resource).name;raw.parent.mkdir(parents=True,exist_ok=True)
                K.write_obj(raw,piece,'belltower_'+side)
                # Validate the exported coordinates, not just full-precision geometry.
                vertices=[None]
                for line in raw.read_text().splitlines():
                    if line.startswith('v '):vertices.append(np.array(list(map(float,line.split()[1:]))))
                    elif line.startswith('f '):
                        a,b,c=[vertices[int(t.split('/')[0])] for t in line.split()[1:]]
                        assert np.linalg.norm(np.cross(b-a,c-a))>1e-8,(side,kind,'collapsed triangle')
                compact=raw.with_suffix('.compact.obj');C.compact(raw,compact,deduplicate=True)
                data=re.sub(rb'^mtllib .*$',b'mtllib materials.mtl',compact.read_bytes(),count=1,flags=re.M)
                manifest['files']['Assets/'+resource]=S.stage_file('Assets/'+resource,data)
                pieces.append(resource);totals+=piece.triangle_count()
            imports[kind]=pieces
        original_path=ROOT/f'Assets/models/maps/belltower/belltower_{side}.vmdl'
        original=original_path.read_text()
        vmdl=remap_model(original,imports)
        relative=f'Assets/{RESOURCE}/preview_{side}.vmdl'
        manifest['files'][relative]=S.stage_file(relative,vmdl.encode())
        manifest['models'][side]={'imports':imports,'triangles':totals,'guard_vmdl':sha(original_path)}
    mtl=''.join(f'newmtl {paint}\nKd 1 1 1\nd 1\n' for paint in I.MATERIALS)
    relative=f'Assets/{RESOURCE}/materials.mtl';manifest['files'][relative]=S.stage_file(relative,mtl.encode())
    (S.STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'private_preview':True,'files':len(manifest['files']),'leaves':2*sum(r['leaves'] for r in stats),
        'triangles_per_half':totals,'largest_import_triangles':LIMIT,'scene_unchanged':True}))


def publish():
    preview_manifest=json.loads((OUT/'preview/stage/manifest.json').read_text())
    for path,digest in preview_manifest['source_sha256'].items():
        if path!='Tools/belltower_stage_ivy_realism.py':assert sha(ROOT/path)==digest,path
    S.OUT=OUT/'publication';S.STAGE=S.OUT/'stage'
    assert not (S.STAGE/'manifest.json').exists()
    manifest={'revision':'ivy-realism-v3','files':{},'models':{},
        'source_sha256':{p:sha(ROOT/p) for p in preview_manifest['source_sha256']},
        'scene_sha256':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
        'scene_unchanged':True,'collision_unchanged':True,'patches_per_half':preview_manifest['patches_per_half']}
    for side in ('west','east'):
        imports={};pieces=[]
        for kind,resources in preview_manifest['models'][side]['imports'].items():
            old=next((ROOT/f'Assets/models/maps/belltower/compiler-safe/{side}').glob('*_'+kind+'.obj'))
            full=OUT/'pieces'/f'{side}-{kind}-publication.obj'
            # A concatenated model for the canonical source; the bounded imports
            # retain their independent compact tables.
            models=[]
            for resource in resources:
                path=ROOT/'Assets'/resource
                assert sha(path)==preview_manifest['files']['Assets/'+resource]['after']
                models.append(path)
            v=vt=vn=0;tables=[];tail=[]
            for path in models:
                counts={'v':0,'vt':0,'vn':0}
                for line in path.read_text().splitlines():
                    head=line.split(maxsplit=1)[0] if line.strip() else ''
                    if head in counts:tables.append(line);counts[head]+=1
                    elif head=='usemtl':tail.append(line)
                    elif head=='f':
                        tokens=[]
                        for t in line.split()[1:]:
                            a,b,c=map(int,t.split('/'));tokens.append(f'{a+v}/{b+vt}/{c+vn}')
                        tail.append('f '+' '.join(tokens))
                v+=counts['v'];vt+=counts['vt'];vn+=counts['vn']
            full.write_text('\n'.join(['# concatenated ivy source','mtllib materials.mtl']+tables+tail)+'\n')
            pieces.append((old,full));targets=[]
            for index,source in enumerate(models):
                target=old if index==0 else old.with_name(f'{side}_realism_{kind}_{index:03d}.obj')
                rel=target.relative_to(ROOT).as_posix()
                manifest['files'][rel]=S.stage_file(rel,source.read_bytes())
                targets.append(target.relative_to(ROOT/'Assets').as_posix())
            imports[kind]=targets
        relative=f'Assets/models/maps/belltower/belltower_{side}.obj'
        manifest['files'][relative]=S.patch_canonical(relative,pieces,OLD)
        relative=f'Assets/models/maps/belltower/belltower_{side}.vmdl'
        original=(ROOT/relative).read_bytes().decode('utf-8');updated=remap_model(original,imports)
        manifest['files'][relative]=S.stage_file(relative,updated.encode())
        for relative in (f'Assets/models/maps/belltower/belltower_{side}.mtl',
            f'Assets/models/maps/belltower/compiler-safe/{side}/materials.mtl'):
            data=(ROOT/relative).read_bytes()
            for paint in I.MATERIALS:
                if f'newmtl {paint}\n'.encode() not in data:data+=f'newmtl {paint}\nKd 1 1 1\nd 1\n'.encode()
            manifest['files'][relative]=S.stage_file(relative,data)
        manifest['models'][side]={'all_non_ivy_obj_bytes_preserved':True,'collision_exact':True,
            'all_non_ivy_imports_exact':True,'imports':imports,'triangles':preview_manifest['models'][side]['triangles']}
    (S.STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'files':len(manifest['files']),'scene_unchanged':True,'collision_unchanged':True}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    publish() if args.publish else preview()
