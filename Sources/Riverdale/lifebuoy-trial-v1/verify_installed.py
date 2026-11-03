"""Verify current installed sources, generator hooks, scene placement and exact mesh surgery."""
from pathlib import Path
from collections import Counter
import ast,json,hashlib,sys
ROOT=Path.cwd();OUT=ROOT/'output/asset-improvement-20261031/riverdale-lifebuoy'
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S,riverdale_parts as P,riverdale_map as M,map_kit as K
plan=json.loads((OUT/'install-plan.json').read_text());installed=json.loads((OUT/'installed.json').read_text());assert installed['installed']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
changed=[]
for entry in installed['files']:
    p=ROOT/entry['relative'];assert p.exists()
    if digest(p)!=entry['afterSHA256']:changed.append(entry['relative'])
assert not [p for p in changed if '/lifebuoy_v2/' in p],changed
source=ROOT/'Assets/models/maps/riverdale/riverdale_hall.obj';have=Counter(S.read_obj(source)[1])
buoys=Counter(S.read_obj(OUT/'retired-buoys.obj')[1]);old=Counter(S.read_obj(OUT/'pipes-before.obj')[1]);new=Counter(S.read_obj(OUT/'pipes-after.obj')[1])
assert not (buoys & have),'Old lifebuoy geometry remains'
assert not new-have,'Installed bypass geometry is incomplete'
assert not ((old-new)&have),'Intersecting pipe faces remain'
backup=OUT/'before-install/Assets/models/maps/riverdale/riverdale_hall.obj'
before=Counter(S.read_obj(backup)[1]);removed=buoys+(old-new);added=new-old
unrelated_preserved=(have-added==before-removed)
assert unrelated_preserved or source.relative_to(ROOT).as_posix() in changed
scene=json.loads((ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene').read_text())
world=next(o for o in scene['GameObjects'] if o.get('Name')=='Riverdale');groups=[g for g in world['Children'] if g.get('Name')=='Lifebuoys'];assert len(groups)==1
assert groups[0]['Children']==plan['placements']
solids=next(o for o in scene['GameObjects'] if o.get('Name')=='Pipe Solids')
assert not set(plan['removedProxyGUIDs'])&{o['__guid'] for o in solids['Children']}
assert len([o for o in solids['Children'] if o.get('Name','').startswith('Pipe Riser Bypass ')])==20
parts=(ROOT/'Tools/riverdale_parts.py').read_text();hall=(ROOT/'Tools/riverdale_hall.py').read_text();maptext=(ROOT/'Tools/riverdale_map.py').read_text()
for text in (parts,hall,maptext):ast.parse(text)
assert 'lifebuoys.record( at, out )' in parts and 'riverdale_lifebuoys.PLACED.clear()' in parts
assert 'P.pipe( m, perimeter_path( n_off, r ), r, "rv_pipe", 10 )' in hall
assert maptext.count('world["Children"].append( LIFEBUOYS.scene_group( ids ) )')==1
# Riser context for the offline visual check, using the same exact source geometry.
risers=K.Model()
for k,(dx,r) in enumerate(((8,7.),(26,9.),(44,6.))):P.pipe(risers,[(-(1000-dx-4),220+k*22,40),(-(1000-dx-4),220+k*22,990)],r,'rv_pipe',12,caps=False)
M.configure(risers);K.write_obj(OUT/'checked-risers.obj',risers,'riverdale_hall')
assert not Counter(S.read_obj(OUT/'checked-risers.obj')[1])-have
compiled=ROOT/'Assets/models/maps/riverdale/lifebuoy_v2/lifebuoy.vmdl_c'
report={'installedLifebuoys':len(groups[0]['Children']),'oldBuoyTrianglesRemaining':0,'bypassMeshVerified':True,
        'oldProxiesRemoved':4,'newProxiesPresent':20,'unrelatedMeshFacesPreserved':unrelated_preserved,
        'generatorHooksVerified':True,'sourceFilesChangedByOtherWorkSinceInstall':changed,
        'compiledModelPresent':compiled.exists(),'nativeEngineVisualCheck':False}
(OUT/'installation-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
