"""Verify the installed resource, surgical map edit and generator persistence."""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,re,subprocess,sys
import numpy as np
ROOT=Path.cwd();OUT=ROOT/'output/orion-cable-reel-installed-20261030';HERE=ROOT/'Sources/Orion/cable-reel-trial-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OUT/'manifest.json').read_text())
for f in manifest['files']:assert sha(ROOT/'Assets'/f['relative'])==f['after'],f['relative']
rel='models/maps/orion/orion_launch_deck.obj'
old=(OUT/'before'/rel).read_bytes().splitlines(keepends=True)
removed=set(sum(manifest['removedFaceLines'].values(),[]))
assert (ROOT/'Assets'/rel).read_bytes()==b''.join(line for i,line in enumerate(old,1) if i not in removed)
assert len(removed)==56 and all(old[i-1].startswith(b'f ') for i in removed)
rel='models/maps/orion/orion_launch_deck.vmdl'
original=(OUT/'before'/rel).read_bytes().decode();block=manifest['removedStairBox'];start=original.index(block)
a=original.rfind('\n',0,start)+1;b=original.index('\n',start+len(block))+1
assert (ROOT/'Assets'/rel).read_bytes().decode()==original[:a]+original[b:]
rel=manifest['sceneRelative'];before=json.loads((OUT/'before'/rel).read_text());after=json.loads((ROOT/'Assets'/rel).read_text())
parent=next(n for n in after['GameObjects'] if n.get('Name')=='Orion')
reels=[n for n in parent['Children'] if n.get('Name')=='ORION cable reel'];assert len(reels)==1
instance=json.loads((HERE/'native-instance.json').read_text());assert reels[0]==instance
parent['Children'].remove(reels[0]);assert after==before
assert sha(HERE/'cable_reel_after.obj')==sha(OUT/'raw/lod0.obj')
assert sha(HERE/'cable_reel_after.glb')==manifest['sourcePreviewGLBSHA256']
native=ROOT/'Assets/models/props/orion/cable_reel_v1/cable_reel_lod0.obj'
def obj(p):
    data={k:[] for k in ('v','vt','vn','f','usemtl')}
    for line in p.read_text().splitlines():
        s=line.split()
        if s and s[0] in data:data[s[0]].append(s[1:])
    return data
source=obj(HERE/'cable_reel_after.obj');target=obj(native)
v=np.array(source['v'],float);n=np.array(source['vn'],float)
assert np.allclose(np.array(target['v'],float),np.column_stack((-v[:,0],v[:,2],v[:,1]))/.0254,atol=1e-6)
assert np.allclose(np.array(target['vn'],float),np.column_stack((-n[:,0],n[:,2],n[:,1])),atol=1e-8)
assert source['vt']==target['vt'] and source['f']==target['f'] and len(source['f'])==81443
assert max(abs(v[:,:2]).max(),0)<=26*.0254+1e-6 and v[:,2].min()>=-1e-6 and v[:,2].max()<=46*.0254+1e-6
# Compare the changed generator against its actual pre-task implementation.
sys.path.insert(0,str(ROOT/'Tools'));import orion_map as O;import orion_cable_reel as OCR
baseline=subprocess.check_output(['rtk','proxy','git','show','HEAD:Tools/orion_map.py'],cwd=ROOT,text=True)
function=next(n for n in ast.parse(baseline).body if isinstance(n,ast.FunctionDef) and n.name=='launch_deck')
namespace=vars(O).copy();exec(compile(ast.Module(body=[function],type_ignores=[]),'original launch_deck','exec'),namespace)
old_model=O.K.Model();new_model=O.K.Model();namespace['launch_deck'](old_model);O.launch_deck(new_model)
def values(data):return tuple(np.asarray(data,float).round(8).ravel())
def polygons(m):
    return Counter((paint,values(points),values(normal),values(m.polygon_uvs.get((paint,i),[])),values(m.polygon_normals.get((paint,i),[])))
        for paint,items in m.polygons.items() for i,(points,normal) in enumerate(items))
polys_before=polygons(old_model);polys_after=polygons(new_model)
assert not polys_after-polys_before and sum((polys_before-polys_after).values())==28
def boxes(m):return Counter((values(c),values(axes),values(size),surface) for c,axes,size,surface in m.boxes)
boxes_before=boxes(old_model);boxes_after=boxes(new_model)
expected=(values((470,1300,263)),values(np.eye(3)),values((52,52,46)),'metal')
assert not boxes_after-boxes_before and boxes_before-boxes_after==Counter({expected:1})
assert [(values(p),s) for p,s in old_model.hulls]==[(values(p),s) for p,s in new_model.hulls]
assert OCR.scene_object()==instance
nav=json.loads((OUT/'navmesh-check.json').read_text());assert nav['Complete']==nav['Total']==95 and not nav['Problems'] and nav['Stair']['DirectUpperFlight']
result={'resourceHashesVerified':len(manifest['files']),'removedFacesOnly':56,'removedStairBoxOnly':True,
 'sceneOnlyAddsApprovedInstance':True,'approvedLOD0GeometryUVsNormalsPreserved':True,'lodTriangles':manifest['lodTriangles'],
 'generatorRemovesOnly28CylinderQuadsAndOneStairBox':True,'generatorOtherGeometryCollisionUVsNormalsPreserved':True,
 'nativeNavigationComplete':95,'directUpperStairRoute':True}
(OUT/'install-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
