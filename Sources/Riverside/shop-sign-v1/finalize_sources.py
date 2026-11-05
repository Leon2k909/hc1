from pathlib import Path
import collections,json,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;REVIEW=HERE.parents[2];OUT=REVIEW/'output/riverside/shop-sign-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=(HERE/'build.py').read_text(encoding='utf-8');s=s[s.index('X=np.array'):s.index('triangles=[]')]
helper='''"""Approved formed Lucky Stop sign; local coordinates retain original roof contacts."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT='materials/riverside/shop-sign-v1'
'''+s+'''
def append_to(target,position):
    m=model(0);offset=np.asarray(position,float)
    for paint,faces in m.polygons.items():
        alias='shopsignv1_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
    target.oriented_box(offset+np.array((0.,0.,50.)),(X,np.array((0.,1.,0.)),Z),(168,8,48),{'default':None},'metal')
'''
(ROOT/'Tools/riverside_shop_sign.py').write_text(helper,encoding='utf-8')
p=ROOT/'Tools/riverside_map.py';s=p.read_text(encoding='utf-8');start=s.index('    # The LUCKY STOP sign');end=s.index('    # The front: windows',start)
replacement='''    # Approved formed lightbox with open gooseneck reflectors; keep the existing sign floodlight subdued.
    r = P.right_for( ( 0, -1 ) )
    sw = 160.0
    sh = sw / RM.aspect( RM.LIT, "lucky_stop" )
    sc = v( ( e0 + e1 ) / 2, PORCH_N0 - 6, eave + 30 + sh / 2 )
    from riverside_shop_sign import append_to as append_approved_shop_sign
    append_approved_shop_sign( m, v( ( e0 + e1 ) / 2, PORCH_N0 - 6, eave ) )
    P.light( "store sign", sc + v( 0, -60, 10 ), P.WARM, 420, shadows=True, scale=0.44 )
'''
assert 'append_approved_shop_sign' not in s
p.write_text(s[:start]+replacement+s[end:],encoding='utf-8')
def records(path):
    lines=path.read_text(encoding='utf-8').splitlines(keepends=True);vertices=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';faces=[]
    for i,line in enumerate(lines):
        if line.startswith('usemtl '):paint=line.split()[1]
        if line.startswith('f '):faces.append((i,(paint,tuple(sorted(vertices[int(t.split('/')[0])-1] for t in line.split()[1:])))))
    return lines,faces
_,old=records(OUT/'legacy-absolute.obj');wanted=collections.Counter(key for _,key in old);assert sum(wanted.values())==136
stage=OUT/'cleanup-stage';stage.mkdir(exist_ok=True);files={};before={}
for source in (ROOT/'Assets/models/maps/riverside').rglob('*.obj'):
    lines,faces=records(source);available=collections.Counter(key for _,key in faces)
    if wanted-available:continue
    removed=[i for i,key in faces if key in wanted];assert len(removed)==136
    relative=source.relative_to(ROOT).as_posix();target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(''.join(line for i,line in enumerate(lines) if i not in set(removed)),encoding='utf-8');files[relative]=sha(target);before[relative]=sha(source)
delete=[]
for folder,stems in [('Assets/models/maps/riverside/shop-sign-v1',('legacy_shop_sign','bright_reference')),('Assets/materials/riverside/shop-sign-v1',('face_bright',))]:
    for p in (ROOT/folder).iterdir():
        if p.is_file() and any(p.name==stem or p.name.startswith(stem+'.') for stem in stems):delete.append(p.relative_to(ROOT).as_posix())
plan=dict(before=before,files=files,delete={p:sha(ROOT/p) for p in delete},removed_triangles_per_source=136)
(OUT/'cleanup-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
script=(ROOT/'Sources/Riverside/shelving-v1/cleanup.cs.txt').read_text(encoding='utf-8').replace('shelving-review','shop-sign-review').replace('shelving-v1','shop-sign-v1').replace('legacy_shelving','legacy_shop_sign').replace('OldShelvingDeleted','OldSignDeleted')
script=script.replace('if(!p.Key.StartsWith("Assets/models/maps/riverside/shop-sign-v1/legacy_shop_sign") || p.Key.Contains(".."))', 'if(!(p.Key.StartsWith("Assets/models/maps/riverside/shop-sign-v1/legacy_shop_sign.") || p.Key.StartsWith("Assets/models/maps/riverside/shop-sign-v1/bright_reference.") || p.Key.StartsWith("Assets/materials/riverside/shop-sign-v1/face_bright.")) || p.Key.Contains(".."))')
script=script.replace('"models/maps/riverside/shop-sign-v1/legacy_shop_sign.obj"}', '"models/maps/riverside/shop-sign-v1/legacy_shop_sign.obj","models/maps/riverside/shop-sign-v1/bright_reference.vmdl","materials/riverside/shop-sign-v1/face_bright.vmat"}')
script=script.replace('"Assets/models/maps/riverside/shop-sign-v1"));','p.Key.StartsWith("Assets/materials/")?"Assets/materials/riverside/shop-sign-v1":"Assets/models/maps/riverside/shop-sign-v1"));')
(HERE/'cleanup.cs.txt').write_text(script,encoding='utf-8')
print(json.dumps({'patched_sources':list(files),'delete':delete},indent=2))
