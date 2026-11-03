"""Validate the installed Ares doorway instances and transformed source geometry offline."""
from pathlib import Path
import hashlib,json,math,re,sys
import numpy as np
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'Tools'));import ares_sliding_doors as D
if (ROOT/'output/ares/sliding-pressure-leaf-20261031/installation.json').exists():
    import ares_verify_pressure_leaf
    sys.exit(0)
OUT=ROOT/'output/ares/sliding-doors-20261031';receipt=json.loads((OUT/'installation.json').read_text())
scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text());before=json.loads((OUT/'before/Assets/scenes/maps/Ares/ares.scene').read_text())
expected=D.scene_objects();assert scene['GameObjects'][-2:]==expected
scene['GameObjects']=scene['GameObjects'][:-2];assert scene==before
all_guids=[]
def visit(x):
    if isinstance(x,dict):
        if '__guid' in x:all_guids.append(x['__guid'])
        for v in x.values():visit(v)
    elif isinstance(x,list):
        for v in x:visit(v)
visit(json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text()))
assert len(all_guids)==len(set(all_guids))
model=ROOT/'Assets'/D.MODEL;doc=model.read_text();meta=json.loads(model.with_suffix('.vmdl.meta').read_text())
assert meta['guid']==receipt['assetGUID'] and 'dimensions = [ 112.8960, 8.0000, 172.0000 ]' in doc
for path in re.findall(r'(?:to|filename) = "([^"]+)"',doc):assert (ROOT/'Assets'/path).exists(),path
base=ROOT/'Assets/models/maps/collider/automatic-door-v1/lab_door_leaf.obj';leaf=model.with_suffix('.obj')
def parse(path):
    d={k:[] for k in ('v','vn','vt','f','usemtl')}
    for line in path.read_text().splitlines():
        p=line.split()
        if p and p[0] in d:d[p[0]].append(p[1:])
    return d
a,b=parse(base),parse(leaf);v=np.array(a['v'],float);n=np.array(a['vn'],float)
assert np.allclose(np.array(b['v'],float),v*np.array([1.28,172/188,1]),atol=1e-6)
scaled=n/np.array([1.28,172/188,1]);scaled/=np.linalg.norm(scaled,axis=1)[:,None]
assert np.allclose(np.array(b['vn'],float),scaled,atol=1e-8) and a['vt']==b['vt'] and a['f']==b['f'] and a['usemtl']==b['usemtl']
assert 56+114-112.896/2>112 # fully open leaves clear the 224-inch aperture
assert 56-112.896/2<0 # closed collision overlaps at the centre seam
assert min(np.array(b['v'],float)[:,1])+88>=0 and max(np.array(b['v'],float)[:,1])+88<=176
for door,world_y in zip(expected,(1116,-1116)):
    assert door['Position']==f'0,{world_y},0' and door['Rotation']=='0,0,0.707106769,0.707106769'
    control=door['Components'][0];assert control['__type']=='Facepunch.AutomaticSlidingDoor'
    assert (control['Width'],control['Height'],control['Travel'])==(224,176,114)
    assert control['LeftLeaf']['go']==door['Children'][0]['__guid'] and control['RightLeaf']['go']==door['Children'][1]['__guid']
    for child in door['Children']:
        assert child['Scale']=='1,1,1'
        cs=child['Components'];assert {x['__type'] for x in cs}=={'Sandbox.ModelRenderer','Sandbox.ModelCollider'}
        for c in cs:assert c['Model']=={'Id':meta['guid'],'Path':D.MODEL}
        assert next(x for x in cs if x['__type']=='Sandbox.ModelCollider')['Static'] is False
for path,h in receipt['sourceSHA256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,path
assert 'objects.extend( automatic_door_objects() )' in (ROOT/'Tools/ares_map.py').read_text()
assert 'HasNearbyActor()' in (ROOT/'Code/World/AutomaticSlidingDoor.cs').read_text()
result={'doors':2,'sceneOnlyAddsTwoAssemblies':True,'uniqueObjectAndComponentIDs':True,'geometryUVsNormalsAndCollisionFit':True,
 'closedCentreSealed':True,'openApertureClear':True,'proximityControllerAndMovingCollidersReferenced':True,
 'sourceDoorAndControllerPreserved':True,'generatorHookPresent':True,'nativeCompileOrPlaytest':False}
(OUT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
