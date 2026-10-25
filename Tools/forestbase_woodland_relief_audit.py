"""Inspect the saved terrain candidate and tree contact without an editor."""
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
import forestbase_map as M
import forestbase_forest_audit as G
from forestbase_cascade_width_audit import groups
from forestbase_floor_audit import Soil,geometry
from forestbase_sheds_audit import mesh

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/forestbase'
BEFORE=OUT/'woodland-relief-before';STAGE=OUT/'woodland-relief-stage'
RES='models/maps/forestbase'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def plan(node):
    n,w,z=map(float,node['Position'].split(','))
    return np.array((-w,n,z))


def main():
    old_path=BEFORE/'Assets'/RES/'vista.obj';new_path=STAGE/RES/'vista.obj'
    old_groups,new_groups=groups(old_path),groups(new_path)
    assert set(new_groups)==set(old_groups)|{'forest_soil'}
    preserved={key:old_groups[key]==new_groups[key] for key in old_groups if key!='mud'}
    assert all(preserved.values()),'Unrelated geometry, UVs or normals changed'
    old_mesh,new_mesh=mesh(old_path),mesh(new_path)
    assert old_mesh['triangles']==new_mesh['triangles']==111714

    hashes=json.loads((BEFORE/'model-hashes.json').read_text())
    assert all(sha(ROOT/'Assets'/RES/f'{name}.vmdl')==value for name,value in hashes.items())
    original=(BEFORE/'Assets'/RES/'vista.vmdl').read_text()
    candidate=(STAGE/RES/'vista.vmdl').read_text()
    # The only ModelDoc change is one extra surface remap. Physics is absent.
    stripped,count=re.subn(r'^.*\{ from = "forest_soil\.vmat" to = "materials/forestbase/forest_soil\.vmat" \},\n','',candidate,flags=re.M)
    assert count==1 and stripped==original
    assert 'PhysicsShape' not in candidate and 'PhysicsHull' not in candidate
    material=(STAGE/'materials/forestbase/forest_soil.vmat').read_text()
    scan=(ROOT/'Assets/materials/forestbase/scans/mud_forest.vmat').read_text()
    assert re.findall(r'\bTexture\w+\s+"[^"]+"',material)==re.findall(r'\bTexture\w+\s+"[^"]+"',scan)
    assert 'shader "shaders/complex.shader"' in material
    assert sha(ROOT/'output/forestbase/layout.json')==sha(BEFORE/'output/forestbase/layout.json')

    before=json.loads((BEFORE/'Assets/scenes/maps/ForestBase/forestbase.scene').read_text())
    after=json.loads((STAGE/'forestbase.scene').read_text())
    old,new=G.nodes(before),G.nodes(after)
    assert old.keys()==new.keys() and len(old)==752
    old_soil=Soil(old_path);new_soil=Soil(new_path,'forest_soil');new_banks=Soil(new_path)
    moved=[];depth_errors=[];roots=0
    tree_models=set()
    for guid,(a,parent,children) in old.items():
        b,p,c=new[guid];assert p==parent and c==children
        if a!=b:
            assert G.tree(a),'Only tree roots may move'
            aa=json.loads(json.dumps(a));bb=json.loads(json.dumps(b))
            assert aa.pop('Position').split(',')[:2]==bb.pop('Position').split(',')[:2]
            assert aa==bb,'Tree fields outside vertical position changed'
            rise=plan(b)[2]-plan(a)[2];assert rise>=0
            moved.append(dict(name=a['Name'],riseInches=float(rise)))
        if not G.tree(a):continue
        assert len(b['Components'])==1 and b['Components'][0]['__type']=='Sandbox.ModelRenderer'
        tree_models.add(b['Components'][0]['Model'])
        roots+=1;e,n,z=plan(a);zz=plan(b)[2]
        h0=old_soil.height(e,n)
        hits=[h for h in (new_soil.height(e,n),new_banks.height(e,n)) if h is not None]
        assert h0 is not None and hits
        h1=max(hits)
        depth_errors.append((h1-zz)-(h0-z))
    assert roots==525 and max(map(abs,depth_errors))<.03
    for model in tree_models:
        text=(ROOT/'Assets'/model).read_text()
        assert 'PhysicsShape' not in text and 'PhysicsHull' not in text

    # Protect the actual near-field surface and every grass root, using the
    # exported triangles rather than evaluating the author's noise function.
    near=[]
    for e,n in [(e,n) for e in range(-2300,2301,200) for n in range(-2200,2201,200)]:
        a=old_soil.height(e,n);hits=[h for h in (new_soil.height(e,n),new_banks.height(e,n)) if h is not None]
        if a is not None and hits:near.append(abs(a-max(hits)))
    assert near and max(near)<.002
    anchor_dir=OUT/'floor-stage'/RES/'floor'
    anchors=json.loads((anchor_dir/'placement-audit.json').read_text())
    for name in anchors:
        for suffix in ('.vmdl','_lod0.obj','_lod1.obj','_lod2.obj'):
            assert sha(ROOT/'Assets'/RES/'floor'/(name+suffix))==sha(anchor_dir/(name+suffix)), 'Stale grass evidence'
    grass_errors=[]
    for positions in anchors.values():
        for e,n,z in positions:
            a=old_soil.height(e,n);hits=[h for h in (new_soil.height(e,n),new_banks.height(e,n)) if h is not None]
            assert a is not None and hits;grass_errors.append(abs(a-max(hits)))
    assert len(grass_errors)==3072 and max(grass_errors)<.002

    v,f=geometry(new_path,'forest_soil');tris=v[f]
    norms=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0])
    slopes=np.degrees(np.arctan2(np.linalg.norm(norms[:,:2],axis=1),norms[:,2]))
    assert np.max(slopes)<45 and np.min(norms[:,2])>0
    M.build(visual_chunks=[])
    source={name:pos for name,path,pos,yaw,scale in M.INSTANCES}
    parity=[]
    for guid,(node,parent,children) in new.items():
        if G.tree(node):parity.append(float(np.max(np.abs(plan(node)-source[node['Name']]))))
    assert max(parity)<.02
    report=dict(scope='Offline exported terrain, exact preservation and tree-contact audit. No native import, engine appearance or performance acceptance.',
        sceneObjects=752,trees=525,movedRoots=len(moved),maximumRootRiseMetres=max(x['riseInches'] for x in moved)*.0254,
        sceneUnchangedOutsideTreeZ=True,treeHorizontalTransformsModelsScalesPreserved=True,
        oldGeometry=old_mesh,newGeometry=new_mesh,unchangedMaterialGeometry=preserved,
        otherEightModelDocsUnchanged=True,vistaOnlyAddsSoilMaterialRemap=True,physicsUnchanged=True,
        treeModelsWithoutPhysics=len(tree_models),
        layoutUnchanged=True,newSceneObjects=0,newTextures=0,newShaders=0,newMaterial=1,
        nearFieldSamples=len(near),nearFieldMaximumHeightErrorInches=max(near),
        grassRootSamples=len(grass_errors),grassMaximumTerrainChangeInches=max(grass_errors),
        maximumRootBurialChangeInches=max(map(abs,depth_errors)),
        maximumSlopeDegrees=float(np.max(slopes)),maximumSourceToSceneDifferenceInches=max(parity),
        sourceHashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'Tools/forestbase_floor.py',
            ROOT/'Tools/forestbase_forest.py',ROOT/'Tools/forestbase_map.py',ROOT/'Tools/forestbase_woodland_relief_audit.py')},
        limitations=['Terrain visibility, tree occlusion/LOD, shadow cost and native FPS are unmeasured.',
            'Geometry and texture counts stay fixed; the extra surface material can add rendering work.',
            'Full reference fidelity and earlier collision changes still require native verification.'])
    (STAGE/'geometry-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('oldGeometry','newGeometry','unchangedMaterialGeometry','sourceHashes','limitations')}))


if __name__=='__main__':main()
