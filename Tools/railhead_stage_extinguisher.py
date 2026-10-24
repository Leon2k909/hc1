"""Stage six existing extinguishers without regenerating unrelated Railhead art."""
from collections import Counter
import argparse
import ast
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import railhead_dress_detail as D
import railhead_station as S
import realistic_extinguisher as E
from belltower_safe_imports import span

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/railhead/extinguisher-v2'
STAGE = OUT/'stage-v1'


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def point(value): return tuple(int(round(float(n)*1000)) for n in value.split())


def old_function():
    path = ROOT/'Sources/Railhead/props/extinguisher-v2/legacy-railhead_dress_detail.py'
    tree = ast.parse(path.read_text())
    function = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == 'extinguisher')
    namespace = dict(vars(D))
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(path),'exec'),namespace)
    return namespace['extinguisher']


def placements(side):
    sign = 1 if side == 'east' else -1
    e = sign*(S.WALL_IN-.5); facing = '-e' if sign>0 else '+e'
    # Wing props in the source generator have not been published in the current
    # assets. Replace only the six complete assemblies verified in both OBJs.
    return [(e,-778.,facing,0.),(e,228.,facing,0.),(e,-262.,facing,S.DECK_Z)]


def lookup_polygons(model):
    lookup,faces = {},[]
    for paint,items in model.polygons.items():
        for points,_ in items:
            vertices = [point(K.obj_vector(K.to_world(p))) for p in points]
            index = len(faces); faces.append((paint.encode(),vertices))
            for tri in itertools.combinations(vertices,3):
                key = (paint.encode(),frozenset(tri))
                assert key not in lookup, ('Ambiguous old extinguisher face',key)
                lookup[key] = index
    return lookup,faces


def coverage(found,lookup,faces):
    groups = [Counter() for _ in faces]; counts = Counter()
    for key,count in found.items():
        assert count == 1
        index = lookup[key]; counts[index] += 1
        for a,b in itertools.combinations(key[1],2): groups[index][frozenset((a,b))] += 1
    for index,(paint,vertices) in enumerate(faces):
        perimeter = Counter(frozenset((p,vertices[(i+1)%len(vertices)])) for i,p in enumerate(vertices))
        assert counts[index] == len(vertices)-2, ('Missing old extinguisher polygon',index,paint,counts[index])
        assert Counter({e:n for e,n in groups[index].items() if n==1}) == perimeter


def replace_obj(source,canonical,base,wanted,addition):
    before = sha(source)
    positions = {p for paint,face in wanted for p in face}; paints = {paint for paint,face in wanted}
    sparse = {}; counts = {k:0 for k in (b'v',b'vt',b'vn')}; removed = set(); found = Counter(); paint = None
    for number,line in enumerate(source.open('rb')):
        if line.startswith(b'v '):
            counts[b'v'] += 1; p = point(line[2:].decode())
            if p in positions: sparse[counts[b'v']] = p
        elif line.startswith(b'vt '): counts[b'vt'] += 1
        elif line.startswith(b'vn '): counts[b'vn'] += 1
        elif line.startswith(b'usemtl '): paint = line.split()[1]
        elif line.startswith(b'f ') and paint in paints:
            indices = [int(token.split(b'/')[0]) for token in line.split()[1:]]
            if all(i in sparse for i in indices):
                key = (paint,frozenset(sparse[i] for i in indices))
                if key in wanted: removed.add(number); found[key] += 1
    assert removed, 'No legacy extinguisher faces matched.'
    tables,tail = [],[]
    for line in addition.open('rb'):
        if line.startswith((b'v ',b'vt ',b'vn ')): tables.append(line)
        elif line.startswith(b'usemtl '): tail.append(line)
        elif line.startswith(b'f '):
            tokens = [b'/'.join(str(int(v)+counts[k]).encode() for k,v in zip((b'v',b'vt',b'vn'),token.split(b'/'))) for token in line.split()[1:]]
            tail.append(b'f '+b' '.join(tokens)+b'\n')
    canonical.parent.mkdir(parents=True,exist_ok=True); base.parent.mkdir(parents=True,exist_ok=True)
    retained = hashlib.sha256(); inserted = False
    with canonical.open('wb') as authored,base.open('wb') as unchanged:
        for number,line in enumerate(source.open('rb')):
            if not inserted and line.startswith(b'usemtl '): authored.writelines(tables); inserted = True
            if number not in removed:
                authored.write(line); unchanged.write(line); retained.update(line)
        authored.writelines(tail)
    assert inserted and sha(base) == retained.hexdigest()
    actual = canonical.read_bytes().replace(b''.join(tables),b'',1)
    actual = actual[:-len(b''.join(tail))]
    assert hashlib.sha256(actual).hexdigest() == retained.hexdigest()
    assert sha(source) == before, 'Shared model changed while staging.'
    return {'removed_triangles':len(removed),'unrelated_obj_bytes_exact':True,
            'retained_bytes_sha256':retained.hexdigest()},found


def material(name,atlas=False,tint=(1,1,1),rough=.5,metal=0):
    color = 'materials/props/extinguisher-v2/atlas.png' if atlas else 'materials/default/default_color.tga'
    return ('// Tools/railhead_stage_extinguisher.py\n"Layer0"\n{\n'
            '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
            f'    g_flRoughnessScaleFactor "{rough/(124/255):.4f}"\n    g_flMetalness "{metal}"\n'
            f'    TextureColor "{color}"\n'
            '    TextureNormal "materials/railhead/plain_normal.png"\n'
            '    TextureRoughness "materials/railhead/plain_rough.png"\n'
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
            f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1.0]"\n'
            '    g_flModelTintAmount "1.0"\n}\n')


def main():
    global STAGE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',default='stage-v1')
    args=parser.parse_args()
    assert re.fullmatch('[a-z0-9-]+',args.stage)
    STAGE=OUT/args.stage
    assert not STAGE.exists(), 'Keep each staged revision.'
    STAGE.mkdir(parents=True)
    files = {}; models = {}; legacy = old_function()
    inputs = {p:sha(ROOT/p) for p in ('Tools/realistic_extinguisher.py','Tools/railhead_dress_detail.py',
              'Tools/railhead_stage_extinguisher.py','Tools/map_kit.py',
              'Sources/Railhead/props/extinguisher-v2/legacy-railhead_dress_detail.py',
              'Sources/Railhead/props/extinguisher-v2/extinguisher-atlas-v1.png')}
    protected = {p:sha(ROOT/p) for p in ('Assets/scenes/maps/Railhead/railhead.scene',
                 'Assets/materials/railhead/plain_normal.png','Assets/materials/railhead/plain_rough.png')}
    def record(relative,path):
        relative = Path(relative).as_posix(); original = ROOT/relative
        before = sha(original) if original.exists() else None
        backup = STAGE/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(original,backup)
            assert sha(backup) == before
        files[relative] = {'before':before,'after':sha(path),
                           'source':path.relative_to(ROOT).as_posix(),
                           'backup':backup.relative_to(ROOT).as_posix() if before else None}
    relative = Path('Assets/materials/props/extinguisher-v2/atlas.png')
    target = STAGE/relative; target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'Sources/Railhead/props/extinguisher-v2/extinguisher-atlas-v1.png',target); record(relative,target)
    specs = {'red':(True,(1,1,1),.34,.08),'label':(True,(1,1,1),.72,0),
             'sign':(True,(1,1,1),.49,.05),'gauge':(True,(1,1,1),.54,0),
             'rubber':(False,(.022,.024,.025),.76,0),'steel':(False,(.54,.57,.59),.28,.96),
             'brass':(False,(.56,.38,.13),.35,.94),'dark':(False,(.038,.042,.044),.40,.08),
             'seal':(False,(.47,.018,.013),.46,0)}
    for name,(atlas,tint,rough,metal) in specs.items():
        relative = Path(f'Assets/materials/props/extinguisher-v2/{name}.vmat')
        path = STAGE/relative; path.write_text(material(name,atlas,tint,rough,metal)); record(relative,path)
    for side in ('east','west'):
        old,new = K.Model(),K.Model()
        for e,n,facing,z0 in placements(side):
            legacy(old,e,n,facing,z0); E.build_into(new,D.Frame(e,n,z0,facing))
        assert not old.boxes and not old.hulls and not new.boxes and not new.hulls
        assert new.triangle_count() < 65000
        for (paint,index),normals in new.polygon_normals.items():
            assert np.isfinite(normals).all()
        leaf = Path(f'Assets/models/maps/railhead/extinguisher-v2/{side}.obj')
        piece = STAGE/leaf; piece.parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(piece,new,'extinguisher_'+side); record(leaf,piece); record(leaf.with_suffix('.mtl'),piece.with_suffix('.mtl'))
        canonical = Path(f'Assets/models/maps/railhead/railhead_dress_{side}.obj')
        base = Path(f'Assets/models/maps/railhead/extinguisher-v2/{side}-base.obj')
        lookup,faces = lookup_polygons(old)
        result,found = replace_obj(ROOT/canonical,STAGE/canonical,STAGE/base,lookup,piece)
        coverage(found,lookup,faces)
        record(canonical,STAGE/canonical); record(base,STAGE/base)
        old_mtl = canonical.with_suffix('.mtl')
        base_mtl = base.with_name(old_mtl.name)
        path = STAGE/base_mtl; shutil.copyfile(ROOT/old_mtl,path); record(base_mtl,path)
        path = STAGE/old_mtl
        original_mtl = (ROOT/old_mtl).read_bytes()
        path.write_bytes(original_mtl+b'\n'+piece.with_suffix('.mtl').read_bytes()); record(old_mtl,path)
        vmdl = canonical.with_suffix('.vmdl'); raw = (ROOT/vmdl).read_bytes().decode()
        a,b = span(raw,'_class = "RenderMeshList"'); render = raw[a:b]
        x,y = span(render,'_class = "RenderMeshFile"'); template = render[x:y]
        old_resource = canonical.relative_to('Assets').as_posix()
        assert render.count(f'filename = "{old_resource}"') == 1
        new_render = render.replace(f'filename = "{old_resource}"',f'filename = "{base.relative_to("Assets").as_posix()}"',1)
        node = re.sub(r'name = "[^"]+"',f'name = "extinguisher_v2_{side}"',template,count=1)
        node = re.sub(r'filename = "[^"]+"',f'filename = "{leaf.relative_to("Assets").as_posix()}"',node,count=1)
        end = new_render.rfind(']'); prefix = new_render[:end].rstrip()
        new_render = prefix+('' if prefix.endswith(',') else ',')+'\n'+node+'\n'+new_render[end:]
        updated = raw[:a]+new_render+raw[b:]
        remaps = ''.join(f'{{ from = "{paint}.vmat" to = "{resource}" }},\n' for paint,resource in E.MATERIALS.items())
        at = updated.index('[',updated.index('remaps ='))+1
        updated = updated[:at]+'\n'+remaps+updated[at:]
        a,b = span(raw,'_class = "PhysicsShapeList"'); c,d = span(updated,'_class = "PhysicsShapeList"')
        assert raw[a:b] == updated[c:d]
        path = STAGE/vmdl; path.write_bytes(updated.encode()); record(vmdl,path)
        models[side] = {**result,'placements':placements(side),'new_triangles':new.triangle_count(),
                        'physics_bytes_exact':True,'replacement_import':leaf.relative_to('Assets').as_posix(),
                        'retained_import':base.relative_to('Assets').as_posix()}
    # Also provide an ordinary reusable wall assembly, with the vessel foot at Z=0.
    model = K.Model(); E.build_into(model,D.Frame(0,0,-18.12,'+n'))
    obj = Path('Assets/models/props/extinguisher-v2/extinguisher.obj')
    path = STAGE/obj; path.parent.mkdir(parents=True,exist_ok=True)
    K.write_obj(path,model,'extinguisher_v2'); record(obj,path); record(obj.with_suffix('.mtl'),path.with_suffix('.mtl'))
    vmdl = obj.with_suffix('.vmdl')
    text = (ROOT/'Assets/models/maps/railhead/railhead_canopy_pane.vmdl').read_text()
    text = text.replace('railhead_canopy_pane','extinguisher_v2')
    text = text.replace('models/maps/railhead/extinguisher_v2.obj',obj.relative_to('Assets').as_posix())
    text = re.sub(r'\{ from = "rw_canopy_glass.vmat" to = "[^"]+" \}',
                  ',\n'.join(f'{{ from = "{paint}.vmat" to = "{resource}" }}' for paint,resource in E.MATERIALS.items()),text,count=1)
    path = STAGE/vmdl; path.write_bytes(text.encode()); record(vmdl,path)
    manifest = {'revision':'railhead-extinguisher-v2','models':models,'files':files,
                'source_sha256':inputs,'protected_sha256':protected,
                'placements_replaced':6,'triangles_per_instance':model.triangle_count(),
                'standalone_model':vmdl.relative_to('Assets').as_posix(),
                'scene_unchanged':True,'collision_unchanged':True,
                'reference':'Sources/Belltower/generated/fire-extinguisher-taste-20261025-v1.png'}
    (STAGE/'plan-draft.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for group in (inputs,protected):
        for relative,digest in group.items(): assert sha(ROOT/relative) == digest, ('Shared input changed',relative)
    for relative,item in files.items():
        assert sha(ROOT/item['source']) == item['after']
        if item['before']: assert sha(ROOT/relative) == item['before'], ('Shared target changed',relative)
        else: assert not (ROOT/relative).exists()
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':STAGE.name})+'\n')
    print(json.dumps({'files':len(files),'models':models,'triangles_per_instance':model.triangle_count(),'placements_replaced':6}))


if __name__=='__main__': main()
