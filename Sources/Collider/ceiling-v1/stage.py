"""Stage only the ceiling faces, preserving the current published model around them."""
from pathlib import Path
from collections import Counter
import sys, json, hashlib, re, argparse
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import collider_ceiling as CE
import map_kit as K

OUT=ROOT/'output/collider-ceiling-v1-20261027'
REL=Path('models/maps/collider/collider_structure.obj')
MARKER='# Collider ceiling-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def key(paint,points):
    return paint,tuple(sorted(tuple(np.round(p,3)) for p in points))


def tris(model):
    for paint,items in model.polygons.items():
        for points,normal in items:
            for i in range(1,len(points)-1):
                yield paint,[points[0],points[i],points[i+1]],normal


def stage(number,baseline=None):
    dest=OUT/f'stage-v{number}'
    assert not dest.exists(),dest
    dest.mkdir(parents=True)
    before=dest/'before'
    for suffix in ('.obj','.mtl','.vmdl'):
        rel=REL.with_suffix(suffix)
        target=before/rel;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/'Assets'/rel).read_bytes())
    src=(baseline/'before'/REL if baseline else before/REL)
    lines=src.read_text(encoding='utf-8').splitlines(keepends=True)
    assert not any(MARKER in line for line in lines),'Use the original before folder for further revisions'
    expected=Counter(key(p,pnts) for p,pnts,_ in tris(CE.old_parts(published=True)))
    remaining=expected.copy()
    vertices=[];normals=[];uvs=[];kept=[];paint=None;removed=Counter()
    for line in lines:
        if line.startswith('v '):
            a,b,c=map(float,line.split()[1:]);vertices.append(np.array((-a,c,b)))
        elif line.startswith('vn '):
            a,b,c=map(float,line.split()[1:]);normals.append(np.array((-a,c,b)))
        elif line.startswith('vt '):uvs.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            ix=[tuple(map(int,w.split('/'))) for w in line.split()[1:]]
            assert len(ix)==3
            points=[vertices[t[0]-1] for t in ix]
            normal=normals[ix[0][2]-1]
            sig=key(paint,points)
            if remaining[sig]:
                remaining[sig]-=1;removed['old_blocks_beams']+=1;continue
            if paint=='co_steel' and CE.is_panel(points,normal):
                removed['ceiling_faces']+=1;continue
        kept.append(line)
    assert not +remaining, ('Unmatched original ceiling parts',sum((+remaining).values()))
    assert removed['old_blocks_beams']==540 and removed['ceiling_faces']==6,removed
    extra=CE.additions()
    assert not extra.boxes and not extra.hulls,'Visual detail must not introduce collision'
    generated=dest/'generated';generated.mkdir()
    K.write_obj(generated/'collider_structure.obj',extra,'collider_structure')
    appended=['\n'+MARKER+': fabricated luminaires, beams and recessed ceiling joints\n','o collider_ceiling_v1\n']
    offsets=(len(vertices),len(uvs),len(normals));added=0
    for line in (generated/'collider_structure.obj').read_text().splitlines(keepends=True):
        if line.startswith(('#','o ','mtllib ')):continue
        if line.startswith('f '):
            line='f '+' '.join('/'.join(str(int(s)+offsets[j]) for j,s in enumerate(w.split('/')))
                for w in line.split()[1:])+'\n';added+=1
        appended.append(line)
    assets=dest/'assets';target=assets/REL;target.parent.mkdir(parents=True)
    target.write_text(''.join(kept+appended),encoding='utf-8',newline='')
    docsrc=(baseline/'before' if baseline else before)/REL.with_suffix('.vmdl')
    mtlsrc=(baseline/'before' if baseline else before)/REL.with_suffix('.mtl')
    doc=docsrc.read_text()
    mapping=''.join(f'\n\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "{CE.MATERIAL_DIR}/{p}.vmat" }},' for p in CE.TILES)
    pattern=r'(\bremaps\s*=\s*\[)([\s\S]*?)(\n\t{6}\])'
    revised,count=re.subn(pattern,lambda m:m[1]+m[2].rstrip().rstrip(',')+','+mapping.rstrip(',')+m[3],doc,count=1)
    assert count==1
    physics='\t\t\t{\n\t\t\t\t_class = "PhysicsShapeList"'
    assert doc[doc.index(physics):]==revised[revised.index(physics):]
    (assets/REL.with_suffix('.vmdl')).write_text(revised,encoding='utf-8',newline='')
    (assets/REL.with_suffix('.mtl')).write_bytes(mtlsrc.read_bytes()+
        ''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n' for p in CE.TILES).encode())
    CE.materials(assets/CE.MATERIAL_DIR)
    # Check the actual rounded/exported geometry, not just authoring floats.
    vs=[];ns=[];bad=[];minimum=1e9;winding=0
    for line in (generated/'collider_structure.obj').read_text().splitlines():
        if line.startswith('v '):vs.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):ns.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('f '):
            ids=[tuple(map(int,w.split('/'))) for w in line.split()[1:]]
            a,b,c=[vs[t[0]-1] for t in ids];normal=np.cross(b-a,c-a);area=np.linalg.norm(normal)/2
            minimum=min(minimum,area)
            if area<1e-8:bad.append(ids)
            if np.dot(normal,sum((ns[t[2]-1] for t in ids)))<0:winding+=1
    assert not bad and not winding,(len(bad),winding)
    files=[]
    for p in sorted(assets.rglob('*')):
        if p.is_file():
            relative=p.relative_to(assets).as_posix()
            files.append(dict(relative=relative,before=sha(ROOT/'Assets'/relative),after=sha(p)))
    stats=dict(before_triangles=sum(l.startswith('f ') for l in lines),removed=dict(removed),
        added_triangles=added,after_triangles=sum(l.startswith('f ') for l in kept)+added,
        exported_minimum_triangle_area=minimum,winding_errors=winding,fixtures=36,
        ceiling_planes=3,physics_preserved=True,unchanged_face_lines_preserved=True)
    report=dict(revision='collider-ceiling-v1',stage=dest.relative_to(ROOT).as_posix(),
        files=files,geometry=stats,scene_sha256=sha(ROOT/'Assets/scenes/maps/Collider/collider.scene'),
        generators={p:sha(ROOT/p) for p in ('Tools/collider_ceiling.py','Tools/collider_map.py')})
    (dest/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':report['stage']},indent=2))
    print(json.dumps({'stage':report['stage'],'files':len(files),'geometry':stats},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--revision',type=int,default=1)
    ap.add_argument('--baseline',type=Path);a=ap.parse_args()
    baseline=ROOT/a.baseline if a.baseline and not a.baseline.is_absolute() else a.baseline
    stage(a.revision,baseline)
