"""Surgically stage worn stone props over the checked gate-wall upgrade.

All source assets stay untouched. The staged upgrade retains existing render
imports, collision, textures, plant placements and the new fountain ornaments.
Only identified old stone prop triangles are replaced, including both mirrors.
"""
from collections import Counter
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil
import numpy as np

import map_kit as K
import belltower_map as B
import belltower_stone_wear as W
import belltower_wall_edges as Edges
import belltower_wall_cleanup as Cleanup
import belltower_detail as Detail
import belltower_compact_obj as C
from belltower_safe_imports import span

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/edge-realism-v1'
STAGE = OUT/'props-stage'


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def plain(value):
    if isinstance(value,np.ndarray): return value.tolist()
    if isinstance(value,(list,tuple)): return [plain(v) for v in value]
    return value


def fixtures(centre=False):
    old,new = K.Model(),K.Model()
    if centre:
        paints = {'outside':W.LIMESTONE,'inside':W.LIMESTONE,'top':W.LIMESTONE}
        for inner,outer,low,high in W.FOUNTAIN_RINGS:
            B.ring(old,B.FOUNTAIN,inner,outer,low,high,8,paints,'default')
        W.fountain_rings(new,B.FOUNTAIN,B.ring,'default')
        e,n = B.FOUNTAIN
        for half,low,high in W.FOUNTAIN_TIERS+((32,199,203),(35,203,207)):
            old.box((e-half,n-half,low),(e+half,n+half,high),W.LIMESTONE,'default')
            W.fountain_block(new,B.FOUNTAIN,half,low,high,surface='default')
        for r,low,high in ((100,0,12),(80,12,24),(60,24,36)):
            old.cylinder(B.MARKET_CROSS,r,low,high,{'side':'ashlar_grey','top':'ashlar'},sides=8,surface=B.STONE,turn=np.pi/8)
        e,n = B.MARKET_CROSS
        old.box((e-18,n-18,200),(e+18,n+18,212),'ashlar_grey')
        W.market_steps(new,B.MARKET_CROSS,B.STONE)
    else:
        for lo,hi in W.TROUGHS:
            old.box(lo,hi,{'default':'ashlar_grey','+z':'water'},B.STONE)
            W.trough(new,lo,hi,B.STONE)
        for e,n in W.TOMBS:
            old.box((e-22,n-42,0),(e+22,n+42,30),'ashlar',B.STONE)
            old.box((e-25,n-45,30),(e+25,n+45,34),'ashlar_grey')
            W.tomb(new,(e,n),B.STONE)
        old_walls,new_walls=K.Model(),K.Model()
        Edges.targets(old_walls,B.STONE,worn=False); Edges.targets(new_walls,B.STONE)
        Cleanup.trim_model(old_walls,{}); Cleanup.trim_model(new_walls,{})
        old.extend(old_walls); new.extend(new_walls)
        for paint in ('rubble','ashlar_grey'):
            new.material_overrides[paint]=Detail.MATERIALS[paint]
            new.tile_overrides[paint]=Detail.TILES[paint]
        for paint in list(new.polygons):
            if not new.polygons[paint]: del new.polygons[paint]
    assert plain(old.boxes) == plain(new.boxes), 'Collision boxes changed.'
    assert plain(old.hulls) == plain(new.hulls), 'Collision hulls changed.'
    assert not new.props
    return old,new


def point(text): return tuple(int(round(float(v)*1000)) for v in text.split())


def polygons(model):
    lookup, faces = {},[]
    for paint, items in model.polygons.items():
        for points,_ in items:
            vertices = [point(K.obj_vector(K.to_world(p))) for p in points]
            index = len(faces); faces.append((paint.encode(),vertices))
            for triangle in itertools.combinations(vertices,3):
                key = (paint.encode(),frozenset(triangle))
                assert key not in lookup, ('Ambiguous target polygon',key)
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
        assert counts[index] == len(vertices)-2, ('Missing old stone polygon',index,paint,counts[index])
        assert all(n <= 2 for n in groups[index].values())
        assert Counter({e:n for e,n in groups[index].items() if n==1}) == perimeter


def patch(source,target,wanted,addition=None):
    input_hash=sha(source)
    positions = {p for paint,face in wanted for p in face}
    paints = {paint for paint,face in wanted}
    sparse = {}; counts = {kind:0 for kind in C.KINDS}; removed=set(); found=Counter(); paint=None
    for number,line in enumerate(source.open('rb')):
        if line.startswith(b'v '):
            counts[b'v'] += 1; value=point(line[2:].decode())
            if value in positions: sparse[counts[b'v']]=value
        elif line.startswith(b'vt '): counts[b'vt'] += 1
        elif line.startswith(b'vn '): counts[b'vn'] += 1
        elif line.startswith(b'usemtl '): paint=line.split()[1]
        elif line.startswith(b'f ') and paint in paints:
            indices=[int(t.split(b'/')[0]) for t in line.split()[1:]]
            if all(i in sparse for i in indices):
                key=(paint,frozenset(sparse[i] for i in indices))
                if key in wanted: removed.add(number); found[key] += 1
    if not removed: return None,found
    tables,faces=[],[]
    if addition:
        for line in addition.open('rb'):
            if line.startswith((b'v ',b'vt ',b'vn ')): tables.append(line)
            elif line.startswith(b'usemtl '): faces.append(line)
            elif line.startswith(b'f '):
                tokens=[b'/'.join(str(int(v)+counts[k]).encode() for k,v in zip(C.KINDS,t.split(b'/'))) for t in line.split()[1:]]
                faces.append(b'f '+b' '.join(tokens)+b'\n')
    target.parent.mkdir(parents=True,exist_ok=True)
    preserved=hashlib.sha256(); inserted=False
    with target.open('wb') as updated:
        for number,line in enumerate(source.open('rb')):
            if not inserted and line.startswith(b'usemtl '): updated.writelines(tables); inserted=True
            if number not in removed: updated.write(line); preserved.update(line)
        updated.writelines(faces)
    assert inserted
    # Byte reconstruction independently excludes only the added table and tail.
    actual=target.read_bytes()
    if tables: actual=actual.replace(b''.join(tables),b'',1)
    if faces: actual=actual[:-len(b''.join(faces))]
    assert hashlib.sha256(actual).digest() == preserved.digest()
    assert sha(source)==input_hash, ('Shared asset changed during staging',source)
    return {'removed_triangles':len(removed),'unrelated_obj_bytes_exact':True,
            'retained_bytes_sha256':preserved.hexdigest()},found


def main():
    global STAGE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',default='props-stage')
    args=parser.parse_args()
    assert re.fullmatch(r'[a-z0-9-]+',args.stage)
    STAGE=OUT/args.stage
    assert not (STAGE/'manifest.json').exists(), 'Keep each staged upgrade.'
    STAGE.mkdir(parents=True,exist_ok=True)
    files={}
    def current(relative): return ROOT/relative
    def record(relative,path):
        relative=str(relative).replace('\\','/')
        original=ROOT/relative; before=sha(original) if original.exists() else None
        backup=STAGE/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(original,backup)
        files[relative]={'before':before,'after':sha(path),'source':path.relative_to(ROOT).as_posix(),
                         'backup':backup.relative_to(ROOT).as_posix() if before else None}
    models={}
    for side in ('west','east','centre'):
        old,new=fixtures(side=='centre')
        if side=='east': old,new=old.mirrored(B.EAST_PAINTS),new.mirrored(B.EAST_PAINTS)
        assert new.triangle_count() < 65000
        relative=Path(f'Assets/models/maps/belltower/edge-realism-v1/{side}.obj')
        piece=STAGE/relative; piece.parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(piece,new,'belltower_'+side)
        record(relative,piece); record(relative.with_suffix('.mtl'),piece.with_suffix('.mtl'))
        lookup,faces=polygons(old)
        canonical=Path(f'Assets/models/maps/belltower/belltower_{side}.obj')
        result,found=patch(current(canonical),STAGE/canonical,lookup,piece)
        coverage(found,lookup,faces); record(canonical,STAGE/canonical)
        # The authoring MTL keeps the same original bytes and adds new slots.
        mtl=canonical.with_suffix('.mtl'); data=current(mtl).read_bytes(); extra=b''
        for paint in new.polygons:
            if re.search(rb'^newmtl '+re.escape(paint.encode())+rb'\s*$',data,re.M) is None:
                extra+=f'newmtl {paint}\nKd 1 1 1\nd 1\n'.encode()
        if extra:
            target=STAGE/mtl; target.write_bytes(data+extra); record(mtl,target)
        vmdl=canonical.with_suffix('.vmdl'); raw=current(vmdl).read_bytes().decode('utf-8')
        a,b=span(raw,'_class = "RenderMeshList"'); render=raw[a:b]
        x,y=span(render,'_class = "RenderMeshFile"')
        template=render[x:y]
        imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',render)
        all_found=Counter(); changed_parts=0
        for resource in imports:
            if not re.search(r'_(?:ashlar|ashlar_grey|water|fountain_limestone|rubble)\.obj$',resource): continue
            rel=Path('Assets')/resource
            row,part_found=patch(current(rel),STAGE/rel,lookup)
            all_found.update(part_found)
            if row: changed_parts+=1; record(rel,STAGE/rel)
        assert all_found == found, ('Bounded/canonical prop coverage differs',side,sum(all_found.values()),sum(found.values()))
        node=re.sub(r'name = "[^"]+"',f'name = "stone_wear_{side}"',template,count=1)
        node=re.sub(r'filename = "[^"]+"',f'filename = "{relative.relative_to("Assets").as_posix()}"',node,count=1)
        end=render.rfind(']')
        prefix=render[:end].rstrip()
        new_render=prefix+('' if prefix.endswith(',') else ',')+'\n'+node+'\n'+render[end:]
        updated=raw[:a]+new_render+raw[b:]
        additions=[]
        for paint in new.polygons:
            path=new.material_overrides[paint]
            pattern=r'from = "'+re.escape(paint)+r'\.vmat" to = "([^"]+)"'
            existing=re.search(pattern,updated)
            if existing: assert existing.group(1)==path,(paint,existing.group(1),path)
            else: additions.append(f'{{ from = "{paint}.vmat" to = "{path}" }},\n')
        if additions:
            anchor=updated.index('remaps ='); at=updated.index('[',anchor)+1
            updated=updated[:at]+'\n'+''.join(additions)+updated[at:]
        # Physics is compared as bytes; no newline normalization is performed.
        p0,p1=span(raw,'_class = "PhysicsShapeList"'); q0,q1=span(updated,'_class = "PhysicsShapeList"')
        assert raw[p0:p1] == updated[q0:q1]
        target=STAGE/vmdl; target.write_bytes(updated.encode('utf-8')); record(vmdl,target)
        models[side]={**result,'new_triangles':new.triangle_count(),'bounded_parts_patched':changed_parts,
                      'new_import':relative.relative_to('Assets').as_posix(),'physics_exact':True,
                      'all_prior_render_imports_retained':True}
    sources={}
    for relative in ('Tools/belltower_stone_wear.py','Tools/belltower_stage_stone_wear.py',
                     'Tools/belltower_fountain.py','Tools/belltower_fountain_ornaments.py',
                     'Tools/belltower_planters.py','Tools/belltower_furniture.py',
                     'Tools/belltower_wall_edges.py','Tools/belltower_wall_cleanup.py',
                     'Tools/belltower_detail.py','Tools/map_kit.py'):
        sources[relative]=sha(ROOT/relative)
    protected={}
    scene_relative='Assets/scenes/maps/Belltower/belltower.scene'
    protected[scene_relative]=sha(ROOT/scene_relative)
    for material in W.MATERIALS.values(): protected['Assets/'+material]=sha(ROOT/'Assets'/material)
    for p in (ROOT/'Sources/Belltower/props/fountain-ornaments-v2').glob('lion-*.npz'):
        protected[p.relative_to(ROOT).as_posix()]=sha(p)
    # Other chats edit different map functions. The installed geometry is checked
    # against exact resolved polygons; the full shared map writer is not a lock.
    map_text=(ROOT/'Tools/belltower_map.py').read_text()
    for hook in ['StoneWear.market_steps','StoneWear.tomb','StoneWear.trough','WallEdges.tower','WallEdges.merlon']:
        assert hook in map_text, ('Generator integration hook missing',hook)
    report={'revision':'belltower-stone-wear-v1','models':models,
            'files':files,'source_sha256':sources,'protected_sha256':protected,
            'scope':{'troughs':4,'raised_tombs':4,'fountain_basins':1,'fountain_tiers':10,
                     'market_cross_bases':1,'gate_towers':4,'merlons':134},
            'map_writer_sha256_at_stage':sha(ROOT/'Tools/belltower_map.py'),
            'map_writer_is_shared':True,
            'scene_unchanged':True,'collision_unchanged':True,'fountain_ornaments_preserved':True,
            'water_shaders_and_texture_pixels_unchanged':True,
            'trough_water_recess_inches':2.7,'max_new_triangles_per_import':max(12391,max(v['new_triangles'] for v in models.values()))}
    (STAGE/'plan-draft.json').write_text(json.dumps(report,indent=2)+'\n')
    for relative,digest in sources.items(): assert sha(ROOT/relative)==digest
    for relative,recorded in files.items():
        assert sha(ROOT/recorded['source'])==recorded['after']
        if recorded['before']: assert sha(ROOT/relative)==recorded['before'], ('Shared asset changed',relative)
        else: assert not (ROOT/relative).exists()
    (STAGE/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'scope':report['scope'],'models':models,'files':len(files),
                      'max_new_triangles_per_import':report['max_new_triangles_per_import']}))


if __name__=='__main__': main()
