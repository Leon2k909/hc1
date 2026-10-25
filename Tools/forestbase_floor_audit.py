"""Independent serialized-asset checks for the forest floor revision."""
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from forestbase_sheds_audit import mesh

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/forestbase'
STAGE=OUT/'floor-stage'
BEFORE=OUT/'floor-before'
RES='models/maps/forestbase'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry(path,material=None):
    vertices=[];faces=[];paint=None
    for line in path.read_text().splitlines():
        f=line.split()
        if not f:continue
        if f[0]=='v':vertices.append((-float(f[1]),float(f[3]),float(f[2])))
        elif f[0]=='usemtl':paint=f[1]
        elif f[0]=='f' and (material is None or paint==material):
            ids=[int(v.split('/')[0])-1 for v in f[1:]]
            faces.extend((ids[0],ids[i],ids[i+1]) for i in range(1,len(ids)-1))
    return np.asarray(vertices),np.asarray(faces)


class Soil:
    def __init__(self,path,material='mud'):
        v,f=geometry(path,material);self.tri=v[f]
        self.lo=self.tri[:,:,:2].min(axis=1);self.hi=self.tri[:,:,:2].max(axis=1)

    def height(self,e,n):
        mask=((self.lo-.002<=(e,n))&((e,n)<=self.hi+.002)).all(axis=1)
        hits=[]
        for tri in self.tri[mask]:
            basis=np.stack((tri[1,:2]-tri[0,:2],tri[2,:2]-tri[0,:2]),axis=1)
            if abs(np.linalg.det(basis))<1e-9:continue
            u,v=np.linalg.solve(basis,np.array((e,n))-tri[0,:2])
            if min(u,v)>-.00001 and u+v<1.00001:
                hits.append(float(tri[0,2]+u*(tri[1,2]-tri[0,2])+v*(tri[2,2]-tri[0,2])))
        return max(hits) if hits else None


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get('Children',[]))


def main():
    old_scene=json.loads((BEFORE/'Assets/scenes/maps/ForestBase/forestbase.scene').read_text())
    new_scene=json.loads((STAGE/'forestbase.scene').read_text())
    added=[n for n in walk(new_scene['GameObjects']) if n.get('Name','').startswith('Forest floor grass ')]
    assert len(added)==8
    preserved=json.loads(json.dumps(new_scene))
    backdrop=next(n for n in walk(preserved['GameObjects']) if n.get('Name')=='Forest Backdrop')
    backdrop['Children']=[n for n in backdrop['Children'] if not n.get('Name','').startswith('Forest floor grass ')]
    assert preserved==old_scene, 'Existing scene objects or properties changed'
    old_vista=BEFORE/'Assets'/RES/'vista.obj';new_vista=STAGE/RES/'vista.obj'
    for path in (BEFORE/'Assets'/RES/'vista.vmdl',STAGE/RES/'vista.vmdl'):
        assert 'PhysicsShapeBox' not in path.read_text() and 'PhysicsHullFile' not in path.read_text()
    before_soil,after_soil=Soil(old_vista),Soil(new_vista)
    anchors=json.loads((STAGE/RES/'floor/placement-audit.json').read_text())
    groups=[];root_errors=[]
    for node in added:
        assert len(node['Components'])==1 and node['Components'][0]['__type']=='Sandbox.ModelRenderer'
        assert node['Scale']=='1,1,1'
        origin=np.array(tuple(map(float,node['Position'].split(','))))
        origin=np.array((-origin[1],origin[0],origin[2]))
        model=node['Components'][0]['Model'];name=Path(model).stem
        text=(STAGE/model).read_text()
        assert 'PhysicsShape' not in text and 'PhysicsHull' not in text
        meshes=re.findall(r'name = "lod([012])" filename = "([^"]+)"',text)
        assert len(meshes)==3
        lods=[]
        for lod,file in meshes:
            path=STAGE/file;stats=mesh(path);lods.append(stats['triangles'])
            verts,faces=geometry(path);placed=verts+origin
            outside=(np.abs(placed[:,0])>1550)|(placed[:,1]<-1730)|(placed[:,1]>1450)
            assert outside.all(), 'Vegetation enters conservative playable AO bounds'
            if lod=='0':
                coords={tuple(np.round(v,3)) for v in placed}
                for root in anchors[name]:
                    assert tuple(np.round(root,3)) in coords, 'Root probe not found in exported mesh'
                    z=after_soil.height(*root[:2]);assert z is not None
                    root_errors.append(float(root[2]-z))
        assert lods[0]>lods[1]>lods[2]>0
        groups.append(dict(name=name,lodTriangles=lods,rendererOnly=True))
    assert min(root_errors)>-2.5 and max(root_errors)<2.5, 'Excessive floating/buried grass roots'
    trees=[]
    for node in walk(old_scene['GameObjects']):
        if not node.get('Name','').startswith(('Fir ','Far fir ','Forest middle ','Forest understory ','Young fir ')):continue
        n,minus_e,z=map(float,node['Position'].split(','));e=-minus_e
        a,b=before_soil.height(e,n),after_soil.height(e,n)
        assert a is not None and b is not None
        trees.append(b-a)
    assert len(trees)==525 and min(trees)>-.01 and max(trees)<12.01
    hashes=json.loads((BEFORE/'model-hashes.json').read_text())
    unchanged={n:sha(ROOT/'Assets'/RES/f'{n}.vmdl')==h for n,h in hashes.items() if n!='vista'}
    assert all(unchanged.values())
    material=(STAGE/'forest_grass.vmat').read_text()
    assert 'shaders/hc1grass.shader' in material
    for key,value in (('g_flSwayAmount',0),('g_flGustAmount',0),('g_flRiseStart',0),('g_flRiseEnd',0),
                      ('g_flFadeStart',40000),('g_flFadeEnd',50000)):
        assert float(re.search(r'\b'+key+r'\s+"([^\"]+)"',material)[1])==value
    before_layout=json.loads((BEFORE/'output/forestbase/layout.json').read_text())
    layout=json.loads((STAGE/'layout.json').read_text())
    copy=json.loads(json.dumps(layout));copy.pop('forestFloor');copy['stats']['vista']=before_layout['stats']['vista'];copy['sceneryInstances']=before_layout['sceneryInstances']
    assert copy==before_layout
    report=dict(scope='Offline scene, mesh, soil and geometry-LOD audit. No native renderer/controller/navmesh/performance verification.',
                existingObjectsPreserved=sum(1 for n in walk(old_scene['GameObjects'])),addedRendererObjects=len(added),
                scenePropertiesAndExistingObjectsUnchanged=True,unrelatedModelDocsUnchanged=unchanged,
                vista=mesh(new_vista),vistaPhysicsShapes=0,grass=groups,grassTufts=sum(v['tufts'] for v in layout['forestFloor'].values()),
                rootSamples=len(root_errors),rootHeightErrorRange=[min(root_errors),max(root_errors)],
                existingTreeSoilSamples=len(trees),soilRiseAtTreeRootsRange=[min(trees),max(trees)],
                grassLodTriangleSums=[sum(g['lodTriangles'][i] for g in groups) for i in range(3)],
                sourceHashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'Tools/forestbase_floor.py',ROOT/'Tools/forestbase_map.py',ROOT/'Tools/forestbase_floor_audit.py',ROOT/'Assets/shaders/hc1grass.shader')},
                limitations=['Grass roots are sampled on exported soil, with up to 2.5-inch tolerance for local slope approximation.',
                             'Tree root transforms are unchanged. Soil rises by at most 12 inches, burying their bases rather than moving the trees.',
                             'LOD switch thresholds reuse the existing short-grass model values; native switching and visibility are unverified.',
                             'Added scene renderers and geometry require new native performance and multi-view acceptance.'])
    (STAGE/'geometry-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('grass','sourceHashes','limitations','vista')}))


if __name__=='__main__':main()
