from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/lowtide/quay-ladder-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checked=json.loads((OUT/'runtime-trial/checked.json').read_text())
assert checked['ActualPlayMode'] and not checked['ErrorModels']
build=(HERE/'build.py').read_text();body=build[build.index('m=K.Model();N='):build.index('tris=K.write_model')].replace('m=K.Model();N=-1450.','m=K.Model();N=n')
helper='''"""Approved canal ladder geometry, retained for Lowtide generation."""
import numpy as np
import math
import map_kit as K
def model(n=-1450.):
'''+''.join('    '+line+'\n' for line in body.splitlines())+'''    return m

def append_to(target,n):
    m=model(n)
    for paint,faces in m.polygons.items():
        alias='lt_ql_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/lowtide_quay_ladders.py').write_text(helper)
import lowtide_quay_ladders as L
proof=OUT/'approved-generator.obj';K.write_obj(proof,L.model(),'quay_ladder')
assert proof.read_text().splitlines()[3:]==(ROOT/'Assets/models/maps/lowtide/quay-ladder-v1/quay_ladder.obj').read_text().splitlines()[3:]
STAGE=OUT/'install-stage';RES='models/maps/lowtide/quay-ladder-v1/installed';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True)
before=OUT/'install-before';before.mkdir(exist_ok=True)
plan={};counts={};positions=(-1450.,-560.,1020.)
for side,sign in [('east',1),('west',-1)]:
    name='lowtide_'+side;public=ROOT/f'Assets/models/maps/lowtide/{name}.vmdl'
    vmdl=public.read_text();assert 'quay-ladder-v1/installed' not in vmdl,'Already installed; inspect before retrying'
    (before/public.name).write_bytes(public.read_bytes())
    plan[str(public.relative_to(ROOT)).replace('\\','/')]=sha(public)
    source=ROOT/f'Assets/models/maps/lowtide/{name}.obj'
    lines=source.read_text().splitlines(keepends=True)
    ov=[tuple(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')];verts=[(c,-a,b) for a,b,c in ov] # plan (n,e,z)
    kept=[];removed={n:0 for n in positions};paint=''
    for line in lines:
        if line.startswith('usemtl '):paint=line.split()[1]
        target=None
        if line.startswith('f ') and paint=='iron_black':
            pts=[verts[int(t.split('/')[0])-1] for t in line.split()[1:]]
            for n in positions:
                if all(n-9.01<=nn<=n+9.01 and 233.99<=sign*e<=244.01 and -132.01<=z<=18.01 for nn,e,z in pts):target=n;break
        if target is not None:removed[target]+=1
        else:kept.append(line)
    assert all(c==168 for c in removed.values()),removed
    trimmed=side+'_without_ladders';group=side+'_ladders'
    (MODEL/f'{trimmed}.obj').write_text(''.join(kept).replace(f'mtllib {name}.mtl',f'mtllib {trimmed}.mtl'))
    (MODEL/f'{trimmed}.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
    m=K.Model()
    for n in positions:m.extend(L.model(n))
    if sign<0:m=m.mirrored()
    tris=K.write_model(MODEL,RES,group,m);assert tris==5152*3
    own=(MODEL/f'{group}.vmdl').read_text()
    node=re.search(r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},',own,re.S).group()
    oldnode=re.search(r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},',vmdl,re.S).group()
    newnode=oldnode.replace(f'models/maps/lowtide/{name}.obj',f'{RES}/{trimmed}.obj')
    vmdl=vmdl.replace(oldnode,newnode+'\n'+node)
    remaps=re.findall(r'\{ from = "[^\n]+?\}',own)
    marker='\t'*7+'{ from = "ashlar_grey.vmat"';assert marker in vmdl
    vmdl=vmdl.replace(marker,'\n'.join('\t'*7+r+',' for r in remaps)+'\n'+marker,1)
    original=public.read_text();assert original[original.index('_class = "PhysicsShapeList"'):]==vmdl[vmdl.index('_class = "PhysicsShapeList"'):]
    staged=STAGE/public.relative_to(ROOT);staged.parent.mkdir(parents=True,exist_ok=True);staged.write_text(vmdl)
    counts[side]=dict(removed=removed,new_triangles=tris)
paths=list((ROOT/'Assets/models/maps/lowtide').rglob('*'))+list((ROOT/'Assets/materials/lowtide').rglob('*'))+[ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.is_file() and p.suffix!='.meta' and not p.name.endswith('_c')}
(OUT/'install-source-guard.json').write_text(json.dumps(guard,indent=2))
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'install-plan.json').write_text(json.dumps(dict(files=files,before=plan,counts=counts),indent=2))
generator=ROOT/'Tools/lowtide_map.py';g=generator.read_text();(before/'lowtide_map.py').write_bytes(generator.read_bytes())
start=g.index('def quay_ladder( m, n ):');end=g.index('\ndef ground(',start)
g=g[:start]+'''def quay_ladder( m, n ):
    """Approved smooth canal ladder; render only, no new collision."""
    from lowtide_quay_ladders import append_to
    append_to(m,n)

'''+g[end:]
g=g.replace('if paint.startswith( "lt_" ):','if paint.startswith( "lt_ql_" ) and paint in model.material_overrides:\n            continue\n        if paint.startswith( "lt_" ):',1)
generator.write_text(g)
print(json.dumps(dict(ladders=6,files=len(files),generator_matches_approved=True,counts=counts),indent=2))
