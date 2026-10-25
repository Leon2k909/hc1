"""Independent scene/model checks and bounded surface-profile sampling.

Numerical sampling is not HLSL compilation or native appearance validation.
"""
import hashlib
import json
import math
import re
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/forestbase'
BEFORE=OUT/'rocks-before';STAGE=OUT/'rocks-stage'
OLD_MODEL='models/maps/forestbase/boulder/cliff.vmdl'
NEW_MODEL='models/maps/forestbase/forest_boulder.vmdl'
MAT='materials/forestbase/forest_rock.vmat'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get('Children',[]))


def profile_samples(material):
    def number(key):return float(re.search(r'\b'+key+r'\s+"([\d.]+)"',material)[1])
    def vector(key):return np.array(list(map(float,re.search(r'\b'+key+r'\s+"\[([^]]+)\]"',material)[1].split())))
    def fract(x):return x-np.floor(x)
    def smooth(a,b,x):
        t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
    def mix(a,b,t):return a*(1-t)+b*t
    def hashed(x,y):
        x=fract(x*.1031);y=fract(y*.1031);z=x
        d=x*(y+33.33)+y*(z+33.33)+z*(x+33.33)
        return fract((x+y+2*d)*(z+d))
    def noise(x,y):
        a,b=np.floor(x),np.floor(y);u,v=fract(x),fract(y)
        u=u*u*(3-2*u);v=v*v*(3-2*v)
        return mix(mix(hashed(a,b),hashed(a+1,b),u),mix(hashed(a,b+1),hashed(a+1,b+1),u),v)
    rng=np.random.default_rng(49016);p=rng.uniform((-7000,-7000,-350),(7000,7000,1600),(8192,3))
    coarse=noise(p[:,0]*.0075+p[:,2]*.002,p[:,1]*.0075+p[:,2]*.002)
    streak=noise(p[:,0]*.024+p[:,1]*.011,p[:,2]*.002)
    roughness=rng.uniform(.10,.99,len(p));color=rng.uniform(.01,.55,(len(p),3))
    cover=.65*coarse+.35*streak+.15*(1-roughness)
    wet=np.clip(number('RockWetness')+.24*(streak-.5)+.30*(1-smooth(-285,-155,p[:,2])),0,1)
    luminance=color@np.array((.2126,.7152,.0722))
    stone=mix(color,luminance[:,None],number('RockDesaturation'))*vector('RockTint')*mix(1,.62,wet[:,None])
    moss_color=vector('MossTint')*(.55+1.5*luminance[:,None])
    cases=[]
    for up in (0,.22,.5,1):
        moss=number('MossAmount')*smooth(.22,.78,up)*smooth(.30,.68,cover)
        albedo=mix(stone,moss_color,moss[:,None])
        rough=mix(mix(np.maximum(.48,roughness),.25,wet*.7),mix(.90,.75,wet),moss)
        assert np.isfinite(albedo).all() and np.isfinite(rough).all()
        assert albedo.min()>=0 and albedo.max()<=1 and rough.min()>=.25 and rough.max()<=1
        if up<=.22:assert not np.any(moss)
        cases.append(dict(up=up,mossMean=float(moss.mean()),mossRange=[float(moss.min()),float(moss.max())],
                          roughnessRange=[float(rough.min()),float(rough.max())]))
    assert cases[-1]['mossMean']>.05
    return dict(samplesPerSlope=len(p),slopeCases=cases,wetnessRange=[float(wet.min()),float(wet.max())],
                scope='CPU numeric evaluation of the shader formulas in double precision; GPU/compiler equivalence is not asserted.')


def main():
    original=json.loads((BEFORE/'Assets/scenes/maps/ForestBase/forestbase.scene').read_text())
    candidate=json.loads((STAGE/'forestbase.scene').read_text())
    old=list(walk(original['GameObjects']));new=list(walk(candidate['GameObjects']))
    assert len(old)==len(new)==752
    restored=json.loads(json.dumps(candidate));restored_nodes=list(walk(restored['GameObjects']))
    remapped=[];lowered=[];tops=[]
    # The scan's OBJ +Y is native world +Z. Check the actual source bounds.
    source=ROOT/'Assets/models/maps/forestbase/boulder/cliff_lod0.obj'
    verts=[tuple(map(float,l.split()[1:4])) for l in source.read_text().splitlines() if l.startswith('v ')]
    zmax=max(v[1] for v in verts)
    for a,b,c in zip(old,new,restored_nodes):
        name=a.get('Name','')
        if not name.startswith('Rock '):continue
        i=next((i for i,v in enumerate(a.get('Components',[])) if v.get('__type')=='Sandbox.ModelRenderer'),None)
        if i is None or a['Components'][i].get('Model')!=OLD_MODEL:continue
        assert b['Components'][i]['Model']==NEW_MODEL
        assert len(a['Components'])==len(b['Components'])==1
        c['Components'][i]['Model']=OLD_MODEL;remapped.append(name)
        seed=int(name.split()[1]);before=list(map(float,a['Scale'].split(',')));after=list(map(float,b['Scale'].split(',')))
        expected=min(before[2],math.sqrt(before[0]*before[1])) if 80<=seed<118 and seed!=87 else before[2]
        assert before[:2]==after[:2] and abs(after[2]-expected)<.0011
        rotation=list(map(float,a['Rotation'].split(',')));assert abs(rotation[0])+abs(rotation[1])<.00001
        c['Scale']=a['Scale']
        if after[2]<before[2]-.001:
            lowered.append(dict(name=name,before=before[2],after=after[2]))
        if 80<=seed<118 and seed!=87:
            z=float(a['Position'].split(',')[2]);tops.append((z+zmax*before[2],z+zmax*after[2]))
    assert len(remapped)==49 and len(lowered)==30
    assert restored==original, 'Unexpected scene/transform/component change'
    template=(BEFORE/'Assets'/OLD_MODEL).read_text();wrapper=(STAGE/NEW_MODEL).read_text()
    assert wrapper.replace(MAT,'models/maps/forestbase/boulder/cliff.vmat')==template
    assert 'PhysicsShape' not in wrapper and 'PhysicsHull' not in wrapper
    hashes=json.loads((BEFORE/'model-hashes.json').read_text())
    unchanged={n:sha(ROOT/f'Assets/models/maps/forestbase/{n}.vmdl')==h for n,h in hashes.items()}
    assert all(unchanged.values())
    for path in (OLD_MODEL,'models/maps/forestbase/boulder/cliff.vmat'):
        assert sha(ROOT/'Assets'/path)==sha(BEFORE/'Assets'/path)
    material=(STAGE/MAT).read_text();shader=(STAGE/'shaders/forestbase_rock.shader').read_text()
    for key in ('RockDesaturation','RockWetness','MossAmount','RockTint','MossTint'):
        assert re.search(r'\b'+key+r'\s+"',material) and re.search(r'float3?\s+'+key+r'\s*<',shader)
    assert shader.count('RockNoise(')==3 and 'Material::From(i)' in shader and 'm.Metalness=0;' in shader and 'm.Opacity=1;' in shader
    report=dict(scope='Offline serialized scene/model checks and numerical surface-profile sampling; no native gameplay/render/performance acceptance.',
                existingObjectsPreserved=len(old),newObjects=0,materialRemaps=len(remapped),loweredRocks=lowered,
                existingPositionsRotationsAndHorizontalScalesUnchanged=True,nonRockObjectsAndScenePropertiesUnchanged=True,
                coreMapModelDocsUnchanged=unchanged,originalScanModelAndMaterialUnchanged=True,wrapperChangesOnlyMaterial=True,
                physicalShapesAdded=0,maximumRimTopHeightMetresBefore=max(a for a,b in tops)*.0254,
                maximumRimTopHeightMetresAfter=max(b for a,b in tops)*.0254,
                profile=profile_samples(material),additionalTextures=0,additionalDeclaredTriangles=0,
                sourceHashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'Tools/forestbase_rocks.py',ROOT/'Tools/forestbase_map.py',
                    ROOT/'Tools/forestbase_rocks_audit.py',ROOT/'Assets/shaders/forestbase_rock.shader')},
                limitations=['Shader complexity changes although texture and geometry counts do not. Current native performance is unmeasured.',
                    'Lower rocks reveal more forest/ground; complete dense-forest coverage and full reference composition remain unfinished.',
                    'No engine movement, roof-access, spawn visibility or escape verification is supplied by this audit.'])
    (STAGE/'geometry-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('loweredRocks','profile','sourceHashes','limitations')}))


if __name__=='__main__':main()
