"""Replace only the old town-gate triangles in the installed town halves.

All existing non-gate OBJ lines and all VMDL physics remain byte-identical.
The native editor publishes the staged files after checking their hashes.
"""
import hashlib
import json
import argparse
from collections import Counter
from pathlib import Path
import numpy as np
import map_kit as K
import belltower_gate as Gate
import belltower_detail as Detail

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/belltower/gate-v1/stage"
RESOURCE = "models/maps/belltower"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def old_gate():
    model=K.Model()
    model.box((-2346,-80,0),(-2334,80,200),"planks_dark")
    for z in (30,100,170):
        model.box((-2334,-78,z),(-2333,78,z+5),"iron_black")
    return model


def triangle_keys(model):
    result=Counter()
    for paint,faces in model.polygons.items():
        for points,_ in faces:
            vertices=[K.obj_vector(K.to_world(p)) for p in points]
            for k in range(1,len(points)-1):
                result[(paint,frozenset((vertices[0],vertices[k],vertices[k+1])))]+=1
    return result


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--baseline',type=Path,help='Preserved pre-gate Assets tree, for a revision')
    args=parser.parse_args()
    OUT=args.out.resolve()
    assert OUT.is_relative_to(ROOT/'output/belltower')
    baseline=args.baseline.resolve() if args.baseline else ROOT
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'before').mkdir(exist_ok=True)
    model=K.Model()
    Gate.build(model)
    Detail.configure(model)
    assert not model.boxes and not model.hulls
    # Check each actual emitted triangle, not just object bounding boxes.
    points=np.array([p for faces in model.polygons.values() for polygon,_ in faces for p in polygon])
    assert np.isfinite(points).all()
    assert points[:,0].min() >= -2351 and points[:,0].max() <= -2296
    assert np.max(np.abs(points[:,1])) <= 91
    assert points[:,2].min() >= 0 and points[:,2].max() <= 211
    for paint,faces in model.polygons.items():
        for polygon,normal in faces:
            for k in range(1,len(polygon)-1):
                cross=np.cross(polygon[k]-polygon[0],polygon[k+1]-polygon[0])
                assert np.linalg.norm(cross) > 1e-8, (paint,'degenerate triangle')
                assert np.dot(cross,normal) > 0, (paint,'reversed triangle')
    material_path=OUT/'Assets'/Gate.IRON_PATH
    material_path.parent.mkdir(parents=True,exist_ok=True)
    material_path.write_text('''// Tools/belltower_stage_gate.py: oxidised forged iron with bevel highlights.
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    TextureColor "materials/buildings/iron_black_color.png"
    TextureNormal "materials/buildings/iron_normal.png"
    TextureRoughness "materials/buildings/iron_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1.55 1.48 1.38 1]"
    g_flRoughnessScaleFactor ".72"
    g_flMetalness ".35"
    g_flModelTintAmount "1"
}
''',encoding='utf8')
    manifest={'version':1,'status':'staged','scene_unchanged':True,'physics_unchanged':True,
              'triangles_removed_per_half':48,'triangles_added_per_half':model.triangle_count(),
              'files':{},'sources':{f'Tools/{p}':sha(ROOT/'Tools'/p) for p in
                                  ('belltower_gate.py','belltower_stage_gate.py','map_kit.py','belltower_detail.py','belltower_furniture.py')},
              'models':{}}
    for side in ('west','east'):
        name='belltower_'+side
        previous=old_gate()
        candidate=model
        if side=='east':
            previous=previous.mirrored()
            candidate=model.mirrored()
        wanted=triangle_keys(previous)
        source=baseline/'Assets'/RESOURCE/(name+'.obj')
        raw=source.read_bytes()
        lines=raw.splitlines(keepends=True)
        vertices=[None]
        counts={'v':0,'vt':0,'vn':0}
        found=Counter(); removed=[]; material=None
        for index,line in enumerate(lines):
            if line.startswith(b'v '):
                vertices.append(line[2:].strip().decode())
                counts['v']+=1
            elif line.startswith(b'vt '): counts['vt']+=1
            elif line.startswith(b'vn '): counts['vn']+=1
            elif line.startswith(b'usemtl '): material=line[7:].strip().decode()
            elif line.startswith(b'f '):
                key=(material,frozenset(vertices[int(t.split(b'/')[0])] for t in line.split()[1:]))
                if key in wanted:
                    found[key]+=1
                    removed.append(index)
        assert found==wanted and sum(found.values())==48, (name,found-wanted,wanted-found)
        piece=OUT/(name+'-gate.obj')
        K.write_obj(piece,candidate,name)
        piece_lines=piece.read_bytes().splitlines(keepends=True)
        # Append vertex/UV/normal tables before any faces. Offset every appended
        # index; never reindex or regenerate the rest of the existing town.
        entries=[x for x in piece_lines if x.startswith((b'v ',b'vt ',b'vn '))]
        appended=[]
        for line in piece_lines:
            if line.startswith(b'usemtl '): appended.append(line)
            elif line.startswith(b'f '):
                tokens=[]
                for token in line.split()[1:]:
                    a,b,c=map(int,token.split(b'/'))
                    tokens.append(f'{a+counts["v"]}/{b+counts["vt"]}/{c+counts["vn"]}')
                appended.append(('f '+' '.join(tokens)+'\n').encode())
        first_face=next(i for i,line in enumerate(lines) if line.startswith(b'usemtl '))
        drop=set(removed)
        result=b''.join(lines[:first_face]+entries+[line for i,line in enumerate(lines[first_face:],first_face) if i not in drop]+appended)
        target=OUT/'Assets'/RESOURCE/(name+'.obj')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(result)
        assert result.count(b'\nf ')==raw.count(b'\nf ')-48+candidate.triangle_count()
        # All shared material names already exist except the one gate-only iron.
        old_mtl=source.with_suffix('.mtl').read_bytes()
        assert b'newmtl belltower_gate_iron' not in old_mtl
        target.with_suffix('.mtl').write_bytes(old_mtl+b'newmtl belltower_gate_iron\nKd 1 1 1\nd 1\n')
        old_vmdl=source.with_suffix('.vmdl').read_bytes()
        anchor=b'{ from = "iron_black.vmat"'
        line=next(x for x in old_vmdl.splitlines(keepends=True) if anchor in x)
        extra=line[:len(line)-len(line.lstrip())]+f'{{ from = "{Gate.IRON}.vmat" to = "{Gate.IRON_PATH}" }},\n'.encode()
        assert old_vmdl.count(line)==1
        new_vmdl=old_vmdl.replace(line,extra+line)
        target.with_suffix('.vmdl').write_bytes(new_vmdl)
        # Byte-for-byte preservation is stricter than regenerating physics.
        assert new_vmdl.replace(extra,b'',1)==old_vmdl
        manifest['models'][name]={'removed_face_lines':removed,'removed_triangles':48,
                                  'added_triangles':candidate.triangle_count(),
                                  'all_other_obj_lines_preserved':True,'physics_byte_identical':True,
                                  'old_vertex_counts':counts}
    for path in sorted((OUT/'Assets').rglob('*')):
        if not path.is_file(): continue
        relative=path.relative_to(OUT).as_posix()
        installed=ROOT/relative
        manifest['files'][relative]={'before':sha(installed) if installed.exists() else None,'after':sha(path)}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'files':len(manifest['files']),'removed_per_half':48,
                      'added_per_half':model.triangle_count(),'physics':'byte-identical'}))


if __name__=='__main__': main()
