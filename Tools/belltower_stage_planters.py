"""Stage only the six masonry planter replacements, preserving the installed town.

No complete model regeneration: this retains the gate and firewood integrations,
lorry removal, scene foliage placements and all existing gameplay collision.
"""
import hashlib
import json
import argparse
from collections import Counter
from pathlib import Path
import numpy as np
import map_kit as K
import belltower_detail as D
import belltower_planters as P

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/planter-v1/stage'
SHADER='shaders/belltower_planter_v1.shader'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def keys(model):
    result=Counter()
    for paint,faces in model.polygons.items():
        for points,_ in faces:
            p=[K.obj_vector(K.to_world(v)) for v in points]
            for k in range(1,len(p)-1):result[(paint,frozenset((p[0],p[k],p[k+1])))]+=1
    return result


def vmat(stone):
    prefix='materials/belltower/scans/medieval_blocks_03' if stone else 'materials/buildings/soil'
    suffixes=('diffuse_4k','nor_gl_4k','rough_4k','ao_4k') if stone else ('color','normal','rough',None)
    lines=['// Tools/belltower_stage_planters.py; unchanged source texture pixels.','"Layer0"','{',f'    shader "{SHADER}"']
    for key,suffix in zip(('Color','Normal','Roughness','AmbientOcclusion'),suffixes):
        path=f'{prefix}_{suffix}.png' if suffix else 'materials/default/default_ao.tga'
        lines.append(f'    Texture{key} "{path}"')
    lines.extend([f'    g_flTintColor "{("[1.12 1.09 1.01]" if stone else "[.64 .56 .46]")}"',
                  f'    g_flPlanterNormal "{.42 if stone else .75}"',
                  f'    g_flPlanterAo "{.68 if stone else .78}"',
                  f'    g_flPlanterRoughness "{.72 if stone else .93}"','}'])
    return '\n'.join(lines)+'\n'


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--baseline',type=Path,help='Preserved pre-planter project tree, for a revision')
    args=parser.parse_args()
    OUT=args.out.resolve();assert OUT.is_relative_to(ROOT/'output/belltower')
    baseline=args.baseline.resolve() if args.baseline else ROOT
    if (OUT/'manifest.json').exists():raise FileExistsError('Preserve the recorded planter stage.')
    OUT.mkdir(parents=True,exist_ok=True)
    old=K.Model();new=K.Model();counts=[]
    for e,n in P.CENTRES:
        old.box((e-20,n-20,0),(e+20,n+20,28),{'default':'ashlar','+z':'soil'})
        counts.append(P.build(new,(e,n),seed=abs(int(e*7+n))))
    D.configure(new)
    assert not new.boxes and not new.hulls and not new.props
    for paint,faces in new.polygons.items():
        for points,normal in faces:
            assert np.isfinite(points).all()
            for k in range(1,len(points)-1):assert np.dot(np.cross(points[k]-points[0],points[k+1]-points[0]),normal)>1e-9
    shader=OUT/'Assets'/SHADER;shader.parent.mkdir(parents=True,exist_ok=True)
    shader.write_bytes((ROOT/'Sources/Belltower/planters/planter-stone-v1.shader').read_bytes())
    for filename,stone in (('cut_stone.vmat',True),('compost.vmat',False)):
        path=OUT/'Assets'/P.RESOURCE/filename;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(vmat(stone),encoding='utf8')
    manifest={'revision':'worn-planters-v1','planters':6,'west_planters':P.CENTRES,
              'triangles_per_west_planter':counts,'removed_triangles_per_half':36,
              'added_triangles_per_half':new.triangle_count(),'files':{},'models':{},
              'source_sha256':{p:sha(ROOT/p) for p in ('Tools/belltower_planters.py','Tools/belltower_stage_planters.py',
                                'Tools/map_kit.py','Tools/belltower_furniture.py','Tools/belltower_detail.py',
                                'Sources/Belltower/planters/planter-stone-v1.shader')},
              'texture_sha256':{},'scene_sha256':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
              'physics_unchanged':True,'foliage_placements_unchanged':True}
    for side in ('west','east'):
        name='belltower_'+side;relative=f'Assets/models/maps/belltower/{name}.obj'
        source=baseline/relative;raw=source.read_bytes();lines=raw.splitlines(keepends=True)
        before=old if side=='west' else old.mirrored()
        candidate=new if side=='west' else new.mirrored()
        wanted=keys(before);found=Counter();remove=[];vertices=[None];paint=None
        offset={'v':0,'vt':0,'vn':0}
        for i,line in enumerate(lines):
            if line.startswith(b'v '):vertices.append(line[2:].strip().decode());offset['v']+=1
            elif line.startswith(b'vt '):offset['vt']+=1
            elif line.startswith(b'vn '):offset['vn']+=1
            elif line.startswith(b'usemtl '):paint=line[7:].strip().decode()
            elif line.startswith(b'f '):
                key=(paint,frozenset(vertices[int(t.split(b'/')[0])] for t in line.split()[1:]))
                if key in wanted:found[key]+=1;remove.append(i)
        assert found==wanted and len(remove)==36,(side,found-wanted,wanted-found)
        piece=OUT/(name+'-planters.obj');K.write_obj(piece,candidate,name)
        piece_lines=piece.read_bytes().splitlines(keepends=True)
        tables=[line for line in piece_lines if line.startswith((b'v ',b'vt ',b'vn '))];faces=[]
        for line in piece_lines:
            if line.startswith(b'usemtl '):faces.append(line)
            elif line.startswith(b'f '):
                indices=[]
                for token in line.split()[1:]:
                    a,b,c=map(int,token.split(b'/'));indices.append(f'{a+offset["v"]}/{b+offset["vt"]}/{c+offset["vn"]}')
                faces.append(('f '+' '.join(indices)+'\n').encode())
        cut=next(i for i,line in enumerate(lines) if line.startswith(b'usemtl '));drop=set(remove)
        result=b''.join(lines[:cut]+tables+[line for i,line in enumerate(lines[cut:],cut) if i not in drop]+faces)
        assert result.count(b'\nf ')==raw.count(b'\nf ')-36+candidate.triangle_count()
        target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result)
        mtl=source.with_suffix('.mtl').read_bytes()
        extra_mtl=b''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n'.encode() for p in (P.STONE,P.SOIL))
        assert all(f'newmtl {p}\n'.encode() not in mtl for p in (P.STONE,P.SOIL))
        target.with_suffix('.mtl').write_bytes(mtl+extra_mtl)
        original=source.with_suffix('.vmdl').read_bytes()
        anchor=next(line for line in original.splitlines(keepends=True) if b'from = "soil.vmat"' in line)
        whitespace=anchor[:len(anchor)-len(anchor.lstrip())]
        extra=b''.join(whitespace+f'{{ from = "{p}.vmat" to = "{candidate.material_overrides[p]}" }},\n'.encode()
                       for p in (P.STONE,P.SOIL))
        assert original.count(anchor)==1
        updated=original.replace(anchor,extra+anchor);assert updated.replace(extra,b'',1)==original
        target.with_suffix('.vmdl').write_bytes(updated)
        manifest['models'][name]={'removed_face_lines':remove,'all_other_obj_lines_preserved':True,
                                  'physics_byte_identical':True,'vmdl_inserted_remaps':extra.decode(),
                                  'old_vertex_counts':offset}
    textures=[f'Assets/materials/belltower/scans/medieval_blocks_03_{s}_4k.png' for s in ('diffuse','nor_gl','rough','ao')]
    textures.extend(f'Assets/materials/buildings/soil_{s}.png' for s in ('color','normal','rough'))
    manifest['texture_sha256']={p:sha(ROOT/p) for p in textures}
    for path in sorted((OUT/'Assets').rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(OUT).as_posix();installed=ROOT/rel
        manifest['files'][rel]={'before':sha(installed) if installed.exists() else None,'after':sha(path)}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'files':len(manifest['files']),'planters':6,'per_west_planter':counts,
                      'added_triangles_per_half':new.triangle_count(),'removed_per_half':36,'physics_unchanged':True}))


if __name__=='__main__':main()
