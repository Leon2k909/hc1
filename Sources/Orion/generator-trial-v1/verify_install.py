"""Offline integrity checks against the approved export and actual pre-install map generator."""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,re,sys
import numpy as np
ROOT=Path.cwd();HERE=ROOT/'Sources/Orion/generator-trial-v1';OUT=ROOT/'output/orion-generator-installed-20261030'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OUT/'manifest.json').read_text());receipt=json.loads((OUT/'offline-install.json').read_text())
for rel,h in receipt['installedFiles'].items():assert sha(ROOT/'Assets'/rel)==h,rel
rel='models/maps/orion/orion_launch_deck.obj';old=(OUT/'before'/rel).read_bytes().splitlines(keepends=True);removed=set(manifest['removedFaceLines'])
assert len(removed)==12 and all(old[i-1].startswith(b'f ') for i in removed)
assert (ROOT/'Assets'/rel).read_bytes()==b''.join(line for i,line in enumerate(old,1) if i not in removed)
assert sha(ROOT/'Assets/models/maps/orion/orion_launch_deck.vmdl')==manifest['originalCollisionModelSHA256']
rel=manifest['sceneRelative'];before=json.loads((OUT/'before'/rel).read_text());after=json.loads((ROOT/'Assets'/rel).read_text())
parent=next(n for n in after['GameObjects'] if n.get('Name')=='Orion');nodes=[n for n in parent['Children'] if n.get('Name')=='ORION standby generator'];assert len(nodes)==1
instance=json.loads((HERE/'native-instance.json').read_text());assert nodes[0]==instance;parent['Children'].remove(nodes[0]);assert after==before
meta=json.loads((ROOT/'Assets'/(manifest['resource']+'.meta')).read_text());assert instance['Components'][0]['Model']=={'Id':meta['guid'],'Path':manifest['resource']}
assert len(instance['Components'])==1 and instance['Components'][0]['__type']=='Sandbox.ModelRenderer'
def obj(p):
    data={k:[] for k in ('v','vt','vn','f','usemtl')}
    for line in p.read_text().splitlines():
        s=line.split()
        if s and s[0] in data:data[s[0]].append(s[1:])
    return data
source=obj(HERE/'generator_after.obj');native=obj(ROOT/'Assets/models/props/orion/generator_v1/generator_lod0.obj')
v=np.array(source['v'],float);n=np.array(source['vn'],float)
assert np.allclose(np.array(native['v'],float),np.column_stack((-v[:,0],v[:,2],v[:,1]))/.0254,atol=1e-6)
assert np.allclose(np.array(native['vn'],float),np.column_stack((-n[:,0],n[:,2],n[:,1])),atol=1e-8)
assert source['vt']==native['vt'] and source['f']==native['f'] and len(native['f'])==51658
assert sha(HERE/'generator_after.glb')==manifest['sourcePreviewGLBSHA256']
resource=ROOT/'Assets'/manifest['resource'];doc=resource.read_text();assert 'PhysicsShape' not in doc
aliases=set(re.findall(r'from = "([^"]+)\.vmat"',doc));assert len(aliases)==12
assert doc.count('_class = "LODGroup"')==4
for filename in re.findall(r'filename = "([^"]+)"',doc):assert (ROOT/'Assets'/filename).exists(),filename
for path in re.findall(r'to = "([^"]+)"',doc):
    assert path.startswith('materials/orion/generator_v1/') and (ROOT/'Assets'/path).exists(),path
    text=(ROOT/'Assets'/path).read_text()
    for tex in re.findall(r'Texture\w+ "([^"\[]+)"',text):assert (ROOT/'Assets'/tex).exists(),tex
for lod,count in enumerate(manifest['lodTriangles']):
    data=obj(ROOT/f'Assets/models/props/orion/generator_v1/generator_lod{lod}.obj')
    assert len(data['f'])==count and set(s[0] for s in data['usemtl'])==aliases
    assert np.isfinite(np.array(data['v'],float)).all() and np.isfinite(np.array(data['vn'],float)).all()
# Compare the actual pre-install function with the updated generator, including attributes and collision.
sys.path.insert(0,str(ROOT/'Tools'));import orion_map as O;import orion_generator as OG
baseline=(OUT/'before/Tools/orion_map.py').read_text();function=next(n for n in ast.parse(baseline).body if isinstance(n,ast.FunctionDef) and n.name=='launch_deck')
namespace=vars(O).copy();exec(compile(ast.Module(body=[function],type_ignores=[]),'pre-install launch_deck','exec'),namespace)
old_model=O.K.Model();new_model=O.K.Model();namespace['launch_deck'](old_model);O.launch_deck(new_model)
def values(data):return tuple(np.asarray(data,float).round(8).ravel())
def polygons(m):return Counter((paint,values(points),values(normal),values(m.polygon_uvs.get((paint,i),[])),values(m.polygon_normals.get((paint,i),[]))) for paint,items in m.polygons.items() for i,(points,normal) in enumerate(items))
a=polygons(old_model);b=polygons(new_model);assert not b-a and sum((a-b).values())==6
def boxes(m):return Counter((values(c),values(axes),values(size),surface) for c,axes,size,surface in m.boxes)
assert boxes(old_model)==boxes(new_model)
assert [(values(p),s) for p,s in old_model.hulls]==[(values(p),s) for p,s in new_model.hulls]
assert OG.scene_object()==instance
# Preserve the accepted reel and all other files protected during the generator review.
guard=json.loads((HERE/'source-guard.json').read_text());allowed={'Assets/models/maps/orion/orion_launch_deck.obj','Assets/scenes/maps/Orion/orion.scene','Tools/orion_map.py'}
unchanged=[p for p in guard if p not in allowed]
for p in unchanged:assert sha(ROOT/p)==guard[p],p
settings=json.loads((ROOT/'.sbox/project.json').read_text());saved=json.loads((OUT/'editor-scene-preferences-before.json').read_text())
assert all(settings.get(k)==v for k,v in saved.items())
result={'installedAssetHashesVerified':len(receipt['installedFiles']),'removedOriginalTrianglesOnly':12,'packedCollisionByteIdentical':True,
 'sceneOnlyAddsGenerator':True,'modelGuidReferenceMatchesMeta':True,'approvedGeometryUVsNormalsPreserved':True,
 'all12MaterialsAndTexturePathsExist':True,'lodTriangles':manifest['lodTriangles'],'generatorOnlyRemovesSixOldBoxQuads':True,
 'generatorOtherGeometryUVsNormalsAndCollisionUnchanged':True,'otherProtectedFilesUnchanged':len(unchanged),'editorPreferencesRestored':True,
 'nativeCompilationAndRenderingPerformed':False}
(OUT/'install-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
