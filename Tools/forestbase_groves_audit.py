"""Inspect background-tree regrouping against saved scene and actual bounds."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import numpy as np
import forestbase_forest_audit as G
from forestbase_floor_audit import Soil

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/forestbase'
BEFORE=OUT/'groves-before';STAGE=OUT/'groves-stage'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def vector(s):return tuple(map(float,s.split(',')))


def plan(node):
    n,w,z=vector(node['Position']);return np.array((-w,n,z))


def main():
    before=json.loads((BEFORE/'Assets/scenes/maps/ForestBase/forestbase.scene').read_text())
    after=json.loads((STAGE/'forestbase.scene').read_text())
    old,new=G.nodes(before),G.nodes(after);assert old.keys()==new.keys() and len(old)==752
    moved=[];trees_before={};trees_after={};models={};horizon=[]
    soil=Soil(ROOT/'Assets/models/maps/forestbase/vista.obj');root_depth=[]
    for guid,(a,parent,children) in old.items():
        b,p,c=new[guid];assert p==parent and c==children
        if G.tree(a):trees_before[guid]=plan(a);trees_after[guid]=plan(b)
        if a==b:continue
        name=a.get('Name','')
        assert name.startswith(('Forest middle ','Far fir infill '))
        side=int(name.split()[2] if name.startswith('Forest middle ') else name.split()[3]);assert side>0
        aa=json.loads(json.dumps(a));bb=json.loads(json.dumps(b));aa.pop('Position');bb.pop('Position');assert aa==bb
        assert plan(a)[2]==plan(b)[2]==-120
        assert len(b['Components'])==1 and b['Components'][0]['__type']=='Sandbox.ModelRenderer'
        model=G.renderer(b)['Model'];geometry=G.geometry(model,False);models[model]=geometry['triangles']
        n,w,z=vector(b['Position']);sx,sy,sz=vector(b['Scale']);qx,qy,qz,qw=vector(b['Rotation'])
        assert abs(qx)+abs(qy)<.00001
        yaw=2*math.atan2(qz,qw);cc,ss=math.cos(yaw),math.sin(yaw);points=[]
        for mesh in geometry['meshes']:
            for x in (mesh['mins'][0],mesh['maxs'][0]):
                for y in (mesh['mins'][1],mesh['maxs'][1]):
                    points.append((n+cc*x*sx-ss*y*sy,w+ss*x*sx+cc*y*sy))
        px,py=zip(*points)
        assert max(px)<-1730 or min(px)>1450 or max(py)<-1550 or min(py)>1550,'Tree bounds enter AO'
        e,nn,zz=plan(b);top=soil.height(e,nn);assert top is not None
        root_depth.append(top-zz);assert -.01<=top-zz<=12.01
        moved.append(dict(guid=guid,name=name,before=plan(a).tolist(),after=plan(b).tolist()))
    assert len(moved)==112 and len(trees_before)==len(trees_after)==525
    assert {k:v for k,v in before.items() if k!='GameObjects'}=={k:v for k,v in after.items() if k!='GameObjects'}
    def nearest(tree_map,ids):
        return [min(np.linalg.norm(tree_map[guid][:2]-p[:2]) for k,p in tree_map.items() if k!=guid) for guid in ids]
    ids=[m['guid'] for m in moved]
    distances=nearest(trees_after,ids);assert min(distances)>=63.995
    middle=[m['guid'] for m in moved if m['name'].startswith('Forest middle ')]
    for guid,(node,parent,children) in new.items():
        r=G.renderer(node)
        if r and '/fir/' in r['Model'] and r['Model'].endswith('_horizon.vmdl'):
            e,n,z=plan(node);horizon.append(math.hypot(max(abs(e)-1550,0),max(n-1450,-1730-n,0)))
    assert len(horizon)==139 and min(horizon)>=3600
    unchanged={n:sha(ROOT/f'Assets/models/maps/forestbase/{n}.vmdl')==h for n,h in json.loads((BEFORE/'model-hashes.json').read_text()).items()}
    assert all(unchanged.values()) and sha(ROOT/'output/forestbase/layout.json')==sha(BEFORE/'output/forestbase/layout.json')
    import forestbase_map as M
    M.build(visual_chunks=[])
    saved_by_name={node.get('Name'):node for node,parent,children in new.values() if G.tree(node)}
    generator_errors=[]
    for name,path,pos,yaw,scale in M.INSTANCES:
        if name not in saved_by_name:continue
        node=saved_by_name[name]
        assert G.renderer(node)['Model']==path
        generator_errors.append(float(np.max(np.abs(np.array(vector(node['Position']))-M.K.to_world(pos)))))
    # Stored coordinates use K.vec's six significant digits. Regrouping a
    # saved baseline versus original floats can accumulate two roundings.
    assert len(generator_errors)==525 and max(generator_errors)<.02
    report=dict(scope='Offline scene identity, bounds, root separation and soil checks. Geometric root density does not measure needle-alpha coverage or native FPS.',
                existingObjectsPreserved=752,treeCount=525,movedTrees=moved,movedTreeCount=112,
                changedPositionsOnly=True,rootHeightsRotationsScalesModelsAndComponentsPreserved=True,
                unchangedMainModelDocs=unchanged,layoutUnchanged=True,additionalDeclaredTriangles=0,additionalRenderers=0,additionalTextures=0,
                movedTreeMinimumRootSeparationInches=min(distances),
                middleTreeMedianNearestRootDistanceBefore=statistics.median(nearest(trees_before,middle)),
                middleTreeMedianNearestRootDistanceAfter=statistics.median(nearest(trees_after,middle)),
                movedRootBurialRange=[min(root_depth),max(root_depth)],horizonTrees=139,minimumHorizonRootDistanceMetres=min(horizon)*.0254,
                generatorParity=dict(trees=525,maximumCoordinateDifferenceInches=max(generator_errors),toleranceInches=.02,
                                     scope='Equivalent tree positions within two text-coordinate roundings, with identical model references.'),
                sourceHashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'Tools/forestbase_forest.py',ROOT/'Tools/forestbase_groves_audit.py')},
                limitations=['Closer/grouped crowns can increase visible alpha/shadow/pixel cost despite identical instance and source-triangle counts.',
                             'Native multi-view coverage, LOD transitions, alpha stability, shadows and performance remain unverified.',
                             'This pass changes only noncolliding background renderer positions. Earlier cargo/bridge/hall changes still require native gameplay checks.'])
    (STAGE/'geometry-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('movedTrees','sourceHashes','limitations')}))


if __name__=='__main__':main()
