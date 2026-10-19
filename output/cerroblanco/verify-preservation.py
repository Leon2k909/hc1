from pathlib import Path
import collections
import copy
import json
import math
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Tools'))
import cerroblanco_quality_state as Q

KINDS={'TeamSpawnPoint','ObjectiveSpot','ModelCollider','BoxCollider','CashPoint','ExtractionPoint'}
before=json.loads((ROOT/'output/cerroblanco/before/cerroblanco.scene').read_text())
after=json.loads((ROOT/'Assets/scenes/maps/CerroBlanco/cerroblanco.scene').read_text())

def equivalent(a,b):
    if isinstance(a,dict) and set(a)=={'Id','Path'}:a=a['Path']
    if isinstance(b,dict) and set(b)=={'Id','Path'}:b=b['Path']
    if isinstance(a,dict) and isinstance(b,dict):
        a={k:v for k,v in a.items() if v is not None}
        b={k:v for k,v in b.items() if v is not None}
        # Native serialization writes these collider defaults explicitly.
        for value in (a,b):
            if value.get('ColliderFlags')==0:value.pop('ColliderFlags')
            if value.get('SurfaceVelocity')=='0,0,0':value.pop('SurfaceVelocity')
        return a.keys()==b.keys() and all(equivalent(v,b[k]) for k,v in a.items())
    if isinstance(a,list) and isinstance(b,list):
        return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    if isinstance(a,str) and isinstance(b,str) and ',' in a and ',' in b:
        try:
            av,bv=[float(x) for x in a.split(',')],[float(x) for x in b.split(',')]
        except ValueError:return a==b
        return len(av)==len(bv) and all(math.isclose(x,y,rel_tol=1e-6,abs_tol=1e-5) for x,y in zip(av,bv))
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        return math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-5)
    return a==b

def collect(scene):
    return {c['__guid']:(o,c) for o in Q.objects(scene) for c in o.get('Components',[])
            if c.get('__type','').split('.')[-1] in KINDS}

b,a=collect(before),collect(after)
assert b.keys()==a.keys()
for guid,(obj,component) in b.items():
    current,current_component=a[guid]
    assert equivalent(component,current_component),(guid,component,current_component)
    for key in ('Position','Rotation','Scale','__enabled','Tags'):
        assert equivalent(obj.get(key),current.get(key)),(guid,key,obj.get(key),current.get(key))

generated=copy.deepcopy(before)
Q.apply_saved_quality(generated)
first=copy.deepcopy(generated)
Q.apply_saved_quality(generated)
assert generated==first
regenerated=collect(generated)
assert regenerated.keys()==b.keys()
for guid,(obj,component) in b.items():
    current,current_component=regenerated[guid]
    assert equivalent(component,current_component)
    assert all(equivalent(obj.get(k),current.get(k)) for k in ('Position','Rotation','Scale','__enabled','Tags'))
textures=[c['Texture']['Path'] for o in Q.objects(after) for c in o.get('Components',[])
          if c.get('__type')=='Sandbox.EnvmapProbe']
assert len(textures)==11 and len(set(textures))==11
assert all((ROOT/'Assets'/(p+'_c')).is_file() for p in textures)
report={'preserved_components':len(b),'counts':dict(collections.Counter(c['__type'].split('.')[-1] for _,c in b.values())),
        'object_transforms_preserved':True,'idempotent':True,'reflection_textures':textures,
        'comparison':'Resource paths and float32 serialization tolerance; explicit zero collider defaults normalized'}
(ROOT/'output/cerroblanco/quality-preservation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'preserved_components':len(b),'idempotent':True,'saved_reflections':len(textures)}))
