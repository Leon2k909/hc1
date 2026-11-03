"""Stage/apply the approved buoy and service-pipe clearance fix without rebuilding the map.

Run from the canonical checkout. Default is staging and verification; --write
applies the verified plan with source hashes and per-file backups.
"""
from pathlib import Path
from collections import Counter
import ast,copy,hashlib,json,math,re,sys,os
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path.cwd();HERE=ROOT/'Sources/Riverdale/lifebuoy-trial-v1'
OUT=ROOT/'output/asset-improvement-20261031/riverdale-lifebuoy';STAGE=OUT/'install-stage';BACKUP=OUT/'before-install'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as P,riverdale_hall as H,riverdale_map as M
import riverdale_splice as S,riverdale_lifebuoys as L
from riverdale_pipe_clearance import perimeter_path
sha=lambda data:hashlib.sha256(data).hexdigest()
changes=[];sources={}
def stage(relative,data):
    source=ROOT/relative;old=source.read_bytes() if source.exists() else None
    target=STAGE/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    changes.append({'relative':relative,'beforeSHA256':sha(old) if old is not None else None,'afterSHA256':sha(data)})
    sources[relative]=old

assert not (OUT/'installed.json').exists(),'Already installed: use verify_installed.py instead.'
models=STAGE/'Assets/models/maps/riverdale/lifebuoy_v2';assert (models/'lifebuoy.vmdl').exists(),'Export native LODs first'
asset_files=list(models.glob('*'))+list((STAGE/'Assets/materials/riverdale/lifebuoy_v2').glob('*'))
for path in asset_files:
    if path.is_file():
        relative=path.relative_to(STAGE).as_posix();data=path.read_bytes();stage(relative,data)

# Match every original buoy, using the exact generator values and original UV phase.
walls=[]
for f in (-1,1):
    walls.extend([((f*H.BLOCK[1],H.BLOCK[2]+50,70),(f,0,0)),((f*H.E0,300,64),(f,0,0))])
walls.extend([((e,H.N1,64),(0,-1,0)) for e in (-260,260)])
old_buoys=K.Model()
legacy=getattr(P,'_legacy_life_ring',P.life_ring)
for at,out in walls:legacy(old_buoys,at,out)

old_pipes,new_pipes=K.Model(),K.Model();P.PIPE_SOLIDS.clear()
for n_off,r in ((10,4.),(22,5.5)):
    P.pipe(old_pipes,[(H.E0+n_off,H.N0+200,236+r),(H.E0+n_off,H.N1-n_off,236+r),
                      (H.E1-n_off,H.N1-n_off,236+r),(H.E1-n_off,H.N0+200,236+r)],r,'rv_pipe',10)
old_solids=list(P.PIPE_SOLIDS);P.PIPE_SOLIDS.clear()
for n_off,r in ((10,4.),(22,5.5)):P.pipe(new_pipes,perimeter_path(n_off,r),r,'rv_pipe',10)
new_solids=list(P.PIPE_SOLIDS)

def model_faces(model,name):
    M.configure(model);path=OUT/(name+'.obj');K.write_obj(path,model,'riverdale_hall');return Counter(S.read_obj(path)[1])
buoys=model_faces(old_buoys,'retired-buoys');old=model_faces(old_pipes,'pipes-before');new=model_faces(new_pipes,'pipes-after')
assert sum(buoys.values())==626*6
relative='Assets/models/maps/riverdale/riverdale_hall.obj';source=ROOT/relative;raw=source.read_bytes()
snapshot=OUT/'hall-source-at-install.obj';snapshot.write_bytes(raw);header,faces=S.read_obj(snapshot);have=Counter(faces)
removed=buoys+(old-new);added=new-old
assert not removed-have, f'Missing saved faces: {len(removed-have)} signatures'
replacement=list((have-removed).elements())+list(added.elements())
mesh=OUT/'hall-installed.obj';S.write_obj(mesh,header,replacement)
assert Counter(S.read_obj(mesh)[1])-added==have-removed
assert source.read_bytes()==raw,'Hall changed while staging; rerun.'
stage(relative,mesh.read_bytes())

# Future regeneration records the approved instanced model and the corrected paths.
relative='Tools/riverdale_parts.py';text=(ROOT/relative).read_bytes().decode()
assert text.count('def life_ring( m, at, out, sign=False ):')==1
text=text.replace('def life_ring( m, at, out, sign=False ):','def _legacy_life_ring( m, at, out, sign=False ):')
where=text.index('\ndef truss(',text.index('def _legacy_life_ring'))
function='''
def life_ring( m, at, out, sign=False ):
    """Approved lifebuoy is an instanced renderer; retain its original wall anchor and optional sign."""
    import riverdale_lifebuoys as lifebuoys
    at = v( *at )
    out, _ = _facing( m, at, unit( ( out[0], out[1], 0 ) ) )
    lifebuoys.record( at, out )
    if sign:
        plate( m, "lifering_sign", at + UP * 27, np.cross( UP, out ), 10.0, off=0.3 )

'''
text=text[:where]+function+text[where:]
text=text.replace('    PIPE_SOLIDS.clear()','    PIPE_SOLIDS.clear()\n    import riverdale_lifebuoys\n    riverdale_lifebuoys.PLACED.clear()',1)
ast.parse(text);stage(relative,text.encode())
relative='Tools/riverdale_hall.py';text=(ROOT/relative).read_bytes().decode()
old_code='''        P.pipe( m, [ ( E0 + n_off, N0 + 200, 236 + r ), ( E0 + n_off, N1 - n_off, 236 + r ), ( E1 - n_off, N1 - n_off, 236 + r ),
                     ( E1 - n_off, N0 + 200, 236 + r ) ], r, "rv_pipe", 10 )'''
assert text.count(old_code)==1
text=text.replace(old_code,'''        from riverdale_pipe_clearance import perimeter_path
        P.pipe( m, perimeter_path( n_off, r ), r, "rv_pipe", 10 )''');ast.parse(text);stage(relative,text.encode())
relative='Tools/riverdale_map.py';text=(ROOT/relative).read_bytes().decode()
assert 'import riverdale_lifebuoys' not in text
text=text.replace('import riverdale_parts as P','import riverdale_lifebuoys as LIFEBUOYS\nimport riverdale_parts as P',1)
needle='    world["Children"].append( EYEWASHES.scene_group( ids ) )';assert text.count(needle)==1
text=text.replace(needle,needle+'\n    world["Children"].append( LIFEBUOYS.scene_group( ids ) )');ast.parse(text);stage(relative,text.encode())

# Scene surgery changes only the added buoy group and the four rerouted pipe proxies.
relative='Assets/scenes/maps/Riverdale/riverdale.scene';raw=(ROOT/relative).read_bytes();text=raw.decode();scene=json.loads(text);expected=copy.deepcopy(scene)
ids=K.SceneIds('5f1c9a72-8e34-4b6d-a2c7-91e0d4b36f85')
world=next(g for g in expected['GameObjects'] if g.get('Name')=='Riverdale')
assert not any(c.get('Name')=='Lifebuoys' for c in world['Children'])
group=L.scene_group(ids,[L.placement(at,out) for at,out in walls]);world['Children'].append(group)
solid_group=next(g for g in expected['GameObjects'] if g.get('Name')=='Pipe Solids')
def solid_key(s):return tuple(round(float(v),4) for row in s for v in (row if isinstance(row,(list,tuple)) else (row,)))
old_set={solid_key(s):s for s in old_solids};new_set={solid_key(s):s for s in new_solids}
drop=[s for k,s in old_set.items() if k not in new_set];insert=[s for k,s in new_set.items() if k not in old_set]
assert len(drop)==4 and len(insert)==20
removed_ids=[]
for centre,direction,r in drop:
    world_pos=K.to_world(centre);length=np.linalg.norm(direction)
    matches=[o for o in solid_group['Children'] if np.allclose([float(x) for x in o['Position'].split(',')],world_pos,atol=.001)
             and any(c.get('__type')=='Sandbox.BoxCollider' and np.allclose([float(x) for x in c['Scale'].split(',')],(length+.4,r*1.8,r*1.8),atol=.001) for c in o['Components'])]
    assert len(matches)==1,(centre,matches);removed_ids.append(matches[0]['__guid']);solid_group['Children'].remove(matches[0])
for i,(centre,direction,r) in enumerate(insert):
    de,dn,dz=direction;pitch=-math.degrees(math.atan2(dz,math.hypot(de,dn)));yaw=math.degrees(math.atan2(-de,dn))
    key=f'pipe/riser-bypass/{i}'
    solid_group['Children'].append(K.game_object(ids,f'Pipe Riser Bypass {i}',key,K.to_world(centre),K.angles_rotation(pitch,yaw),tags='solid',components=[
        K.component(ids,'Sandbox.BoxCollider',key+'/box',Center='0,0,0',Scale=K.vec((np.linalg.norm(direction)+.4,r*1.8,r*1.8)),Static=True,IsTrigger=False)]))
decoder=json.JSONDecoder()
def span(text,guid):
    match=re.search(r'\{\s*"__guid"\s*:\s*"'+re.escape(guid)+'"',text);assert match,guid
    obj,end=decoder.raw_decode(text,match.start());return match.start(),end
start,end=span(text,solid_group['__guid']);indent=text[text.rfind('\n',0,start)+1:start]
text=text[:start]+json.dumps(solid_group,indent=2).replace('\n','\n'+indent)+text[end:]
start,end=span(text,world['__guid']);children=text.index('"Children"',start);opening=text.index('[',children);_,closing=decoder.raw_decode(text,opening)
prefix=text[:closing-1].rstrip();indent='      ';body=json.dumps(group,indent=2).replace('\n','\n'+indent)
text=prefix+',\n'+indent+body+'\n    '+text[closing-1:]
assert json.loads(text)==expected,'Scene changes exceeded the requested two changes'
stage(relative,text.encode())
report={'lifebuoys':6,'removedBuoyTriangles':sum(buoys.values()),'removedPipeTriangles':sum((old-new).values()),'addedPipeTriangles':sum(added.values()),
        'unrelatedMeshFacesPreserved':True,'onlyRequestedSceneChanges':True,'oldPipeProxiesRemoved':len(drop),'newPipeProxies':len(insert),'removedProxyGUIDs':removed_ids,
        'placements':group['Children'],'nativeEngineValidation':False,'files':changes}
(OUT/'install-plan.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('files','placements','removedProxyGUIDs')},indent=2),flush=True)
if '--write' not in sys.argv:print('Staged only. Pass --write to install.');sys.exit(0)
# Check the entire transaction before the first mutation, then recheck each file
# immediately before atomic replacement. Never overwrite another task's changes.
for entry in changes:
    p=ROOT/entry['relative'];current=p.read_bytes() if p.exists() else None
    assert current==sources[entry['relative']],f'Concurrent edit: {p}; rerun staging'
for entry in changes:
    relative=entry['relative'];p=ROOT/relative;data=(STAGE/relative).read_bytes();old=sources[relative]
    assert (p.read_bytes() if p.exists() else None)==old,f'Concurrent edit: {p}'
    if old is not None:
        backup=BACKUP/relative;backup.parent.mkdir(parents=True,exist_ok=True);assert not backup.exists(),backup;backup.write_bytes(old)
    p.parent.mkdir(parents=True,exist_ok=True);temporary=p.with_name(p.name+'.lifebuoy-incoming');temporary.write_bytes(data);os.replace(temporary,p)
(OUT/'installed.json').write_text(json.dumps({'installed':True,'lifebuoys':6,'pipeBypasses':4,'nativeEngineValidation':False,'files':changes},indent=2));print('Installed.',flush=True)
