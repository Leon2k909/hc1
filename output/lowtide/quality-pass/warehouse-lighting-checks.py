"""Validate lighting integration, unchanged gameplay/geometry and baked texture persistence."""
import copy
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
FOLDER=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import lowtide_lighting as lighting
import lowtide_static as static

old=json.loads((FOLDER/'warehouse-lighting-before/lowtide.scene').read_text())
new=json.loads((ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene').read_text())
expected=copy.deepcopy(old)
lighting.apply_scene(expected)
static.apply_scene(expected)
assert expected==new, 'Only the reviewed lighting and static-flag patches may change the saved scene'
lighting.apply_scene(expected)
static.apply_scene(expected)
assert expected==new, 'Canonical lighting patch must be idempotent'
manifest=json.loads((FOLDER/'warehouse-lighting-before/manifest.json').read_text())
geometry={p:h for p,h in manifest.items() if not p.endswith('.scene')}
for path,digest in geometry.items():
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
children=next(o for o in new['GameObjects'] if o.get('Name')=='Lights')['Children']
active_points=[c for o in children for c in o.get('Components',[]) if c['__type']=='Sandbox.PointLight' and c.get('__enabled',True)]
spots=[c for o in children for c in o.get('Components',[]) if c['__type']=='Sandbox.SpotLight' and c.get('__enabled',True)]
volumes=[c for o in children for c in o.get('Components',[]) if c['__type']=='Sandbox.IndirectLightVolume']
assert len(active_points)==6 and len(spots)==18 and len(volumes)==2
assert all(c['Shadows'] and c['ConeOuter']==55 and c['ConeInner']==30 for c in spots)
textures=[]
for volume in volumes:
    assert volume['BakeVersion']==1 and volume['ProbeDensity']==12
    assert volume['RuntimeIntensity']==4 and volume['RuntimeContrast']==.85
    lo=list(map(float,volume['Bounds']['Mins'].split(',')))
    hi=list(map(float,volume['Bounds']['Maxs'].split(',')))
    assert lo[0] < -400 and hi[0]>1150 and lo[2]<0 and hi[2]>352
    assert (lo[1]<-1000 and hi[1]>-240) or (lo[1]<240 and hi[1]>1000)
    for field,width,height,fmt in [('IrradianceTexture',160,80,19),('DistanceTexture',320,160,19),('RelocationTexture',20,10,10)]:
        relative='Assets/'+volume[field]+'_c'
        path=ROOT/relative
        data=path.read_bytes()
        assert struct.unpack_from('<HHHB',data,48)==(width,height,6,fmt),(field,len(data))
        ignored=subprocess.run(['rtk','git','check-ignore','--no-index',relative],cwd=ROOT,capture_output=True,text=True)
        assert ignored.returncode==1,(relative,ignored.stdout,ignored.stderr)
        textures.append({'path':relative,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
captures=['east','west','mezzanine','doorway']
for suffix in captures:
    name='live-warehouse-lighting-saved-'+suffix
    assert (FOLDER/(name+'.png')).exists(),name
    diagnostic=(FOLDER/(name+'-diagnostics.txt')).read_text()
    assert 'Lights: points=6; spots=18' in diagnostic,name
    models=re.findall(r'modelError=(\w+); materialErrors=(\d+)',diagnostic)
    assert len(models)==15 and all(m==('False','0') for m in models),(name,models)
report={'status':'PASS','unchangedGeometryFiles':len(geometry),'unrelatedSceneDataUnchanged':True,
        'activePointLights':len(active_points),'activeSpotLights':len(spots),'probeVolumes':len(volumes),
        'probesPerWarehouse':1200,'bakedTextureBytes':sum(t['bytes'] for t in textures),
        'textures':textures,'captures':captures,'performanceBenchmark':'pending controlled run',
        'overallVisualTargetComplete':False}
(FOLDER/'warehouse-lighting-checks.json').write_text(json.dumps(report,indent=2)+'\n')
provenance={'engineVersion':'26.10.13','geometrySha256':geometry,
            'sceneBeforeLightingSha256':manifest['Assets/scenes/maps/Lowtide/lowtide.scene'],
            'lightingDataSha256':hashlib.sha256(lighting.SOURCE.read_bytes()).hexdigest(),
            'textures':textures,'rebakeWhen':'Static warehouse geometry, fixtures or daylight changes'}
(ROOT/'Sources/Lowtide/lighting/bake-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(f"PASS: {len(geometry)} geometry files unchanged; gameplay and unrelated scene data retained; six baked textures eligible for version control ({report['bakedTextureBytes']} bytes); four clean saved-scene views")
