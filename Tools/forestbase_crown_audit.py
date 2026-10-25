"""Independently inspect actual staged needle meshes and saved scene bounds."""
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
from forestbase_floor_audit import Soil

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/forestbase'
BEFORE=OUT/'crown-before';STAGE=OUT/'crown-stage';ASSETS=ROOT/'Assets'
RES=Path('models/maps/forestbase/fir');NEEDLE='fir_tree_01_twig'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path,strict=True):
    vs=[];ts=[];ns=[];faces=defaultdict(list);refs=[];paint=None
    for line in path.read_text().splitlines():
        p=line.split()
        if not p:continue
        if p[0]=='v':vs.append(tuple(map(float,p[1:])))
        elif p[0]=='vt':ts.append(tuple(map(float,p[1:])))
        elif p[0]=='vn':ns.append(tuple(map(float,p[1:])))
        elif p[0]=='usemtl':paint=p[1]
        elif p[0]=='f':
            assert len(p)==4 and all(len(v.split('/'))==3 and '//' not in v for v in p[1:])
            ids=[tuple(int(i)-1 for i in v.split('/')) for v in p[1:]]
            assert all(0<=v<len(vs) and 0<=t<len(ts) and 0<=n<len(ns) for v,t,n in ids)
            faces[paint].append(tuple((vs[v],ts[t],ns[n]) for v,t,n in ids))
            if paint==NEEDLE:refs.append([v for v,t,n in ids])
    assert np.isfinite(vs).all() and np.isfinite(ts).all() and np.isfinite(ns).all()
    invalid_normals=int((np.abs(np.linalg.norm(ns,axis=1)-1)>=.005).sum())
    if strict:assert invalid_normals==0
    a=np.array([tuple(v for v,t,n in row) for rows in faces.values() for row in rows])
    areas=np.linalg.norm(np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]),axis=1)
    if strict:assert areas.min()>1e-12,('Degenerate triangle',str(path),float(areas.min()))
    return dict(faces=faces,refs=refs,vertices=np.array(vs),triangles=len(a),
                invalidNormals=invalid_normals,minimumDoubleArea=float(areas.min()),mins=a.min(axis=(0,1)),maxs=a.max(axis=(0,1)))


def walk(nodes):
    for node in nodes:yield node;yield from walk(node.get('Children',[]))


def main():
    preservation=json.loads((BEFORE/'preservation-hashes.json').read_text())
    for files in preservation.values():
        for rel,value in files.items():assert sha(ROOT/rel)==value,rel
    results={};cache={}
    for variant in 'abc':
        near=read(ASSETS/RES/f'fir_{variant}_lod0.obj',strict=False)
        for suffix in ('.vmdl','_far.vmdl','_horizon.vmdl','_lod0.obj'):
            file=RES/f'fir_{variant}{suffix}'
            assert sha(ASSETS/file)==sha(BEFORE/'Assets'/file)
        source_faces=Counter(near['faces'][NEEDLE])
        med=read(STAGE/RES/f'fir_{variant}_lod1.obj')
        med_wood={p:Counter(f) for p,f in med['faces'].items() if p!=NEEDLE}
        for level in ('lod1','distant','horizon'):
            file=f'fir_{variant}_{level}.obj';old=read(BEFORE/'Assets'/RES/file,strict=False);new=read(STAGE/RES/file)
            assert set(new['faces'])==set(old['faces'])
            lo=np.minimum(near['mins'],old['mins']);hi=np.maximum(near['maxs'],old['maxs'])
            excess=np.maximum(lo-new['mins'],new['maxs']-hi)
            # Existing legacy envelopes remain valid. Opaque collapse moves the
            # root extremity by less than half a millimetre; canopy XY stays in
            # the source envelope at the OBJ precision tolerance.
            assert excess[[0,2]].max()<.002 and excess[1]<.02
            needles=Counter(new['faces'][NEEDLE])
            if level=='lod1':assert needles==source_faces,'Intermediate needles differ from near source'
            elif level=='distant':
                assert not needles-source_faces,'Far needle charts are not intact source faces'
                assert med_wood=={p:Counter(f) for p,f in new['faces'].items() if p!=NEEDLE}
                assert new['triangles']<=old['triangles']
            else:
                assert {p:Counter(f) for p,f in old['faces'].items() if p!=NEEDLE}=={
                    p:Counter(f) for p,f in new['faces'].items() if p!=NEEDLE}
                assert new['triangles']<=old['triangles']
                if Counter(old['faces'][NEEDLE])==needles:
                    assert sha(STAGE/RES/file)==sha(BEFORE/'Assets'/RES/file), 'Retained legacy asset differs'
                else:assert not needles-source_faces,'Horizon needle faces differ from near source'
            cache[(variant,level)]=new
            results[file]=dict(trianglesBefore=old['triangles'],trianglesAfter=new['triangles'],
                needleTrianglesBefore=len(old['faces'][NEEDLE]),needleTrianglesAfter=len(new['faces'][NEEDLE]),
                invalidNormalsBefore=old['invalidNormals'],invalidNormalsAfter=new['invalidNormals'],
                maximumEnvelopeExcessInches=float(max(0,excess.max())),
                minimumDoubleTriangleArea=new['minimumDoubleArea'],sha256=sha(STAGE/RES/file))
        assert near['triangles']>med['triangles']>cache[(variant,'horizon')]['triangles']

    scene=json.loads((ASSETS/'scenes/maps/ForestBase/forestbase.scene').read_text())
    old_scene=json.loads((BEFORE/'Assets/scenes/maps/ForestBase/forestbase.scene').read_text());assert scene==old_scene
    soil=[Soil(ASSETS/'models/maps/forestbase/vista.obj',p) for p in ('mud','forest_soil')]
    model_cache={};budgets={'before':dict(maximum=0,lod1=0),'after':dict(maximum=0,lod1=0)}
    root_errors=[];tree_count=0;fir_count=0
    def model_info(model,after):
        key=(model,after)
        if key in model_cache:return model_cache[key]
        doc=ASSETS/model;assert 'PhysicsShape' not in doc.read_text() and 'PhysicsHull' not in doc.read_text()
        files=re.findall(r'name = "([^"]+)"\s+filename = "([^"]+\.obj)"',doc.read_text())
        meshes={}
        for lod,file in files:
            path=(STAGE/file if after else BEFORE/'Assets'/file)
            if not path.exists():path=ASSETS/file
            meshes[lod]=read(path,strict=path.is_relative_to(STAGE))
        model_cache[key]=meshes;return meshes
    for node in walk(scene['GameObjects']):
        components=node.get('Components',[])
        model=next((c.get('Model','') for c in components if c['__type']=='Sandbox.ModelRenderer'),'')
        if '/forestbase/fir/' not in model and '/forestbase/sapling/' not in model:continue
        tree_count+=1
        for label,after in (('before',False),('after',True)):
            ms=model_info(model,after);budgets[label]['maximum']+=max(m['triangles'] for m in ms.values())
            budgets[label]['lod1']+=ms['lod1']['triangles']
        if '/forestbase/fir/' not in model:continue
        fir_count+=1;assert len(components)==1
        n,w,z=map(float,node['Position'].split(','));sx,sy,sz=map(float,node['Scale'].split(','))
        qx,qy,qz,qw=map(float,node['Rotation'].split(','));assert abs(qx)+abs(qy)<1e-6
        angle=2*math.atan2(qz,qw);c,s=math.cos(angle),math.sin(angle);bounds=[]
        for m in ms.values():
            for x in (m['mins'][2],m['maxs'][2]):
                for y in (m['mins'][0],m['maxs'][0]):bounds.append((n+c*x*sx-s*y*sy,w+s*x*sx+c*y*sy))
        xx,yy=zip(*bounds)
        assert max(xx)<-1730 or min(xx)>1450 or max(yy)<-1550 or min(yy)>1550,('Canopy enters AO',node['Name'])
        heights=[h.height(-w,n) for h in soil];height=max(h for h in heights if h is not None)
        root_errors.append(z+ms['lod1']['mins'][1]*sz-height)
    assert tree_count==525 and fir_count==444 and max(root_errors)<1
    assert budgets['after']['maximum']<budgets['before']['maximum'] and budgets['after']['lod1']<budgets['before']['lod1']
    coverage=json.loads((STAGE/RES/'coverage-analysis.json').read_text());scores=[]
    for r in coverage['results']:
        assert sha(STAGE/RES/f"fir_{r['variant']}_{r['level']}.obj")==r['outputSha256']
        a=np.mean([v['intersectionOverUnion'] for v in r['before']]);b=np.mean([v['intersectionOverUnion'] for v in r['after']])
        assert b>=a-1e-10,('Sampled silhouette regression',r['variant'],r['level'],a,b)
        scores.append(dict(variant=r['variant'],level=r['level'],meanIouBefore=float(a),meanIouAfter=float(b)))
    report=dict(scope='Offline exported geometry/chart/bounds/contact and sampled-alpha audit. No native render, import, LOD-transition or performance acceptance.',
        sceneUnchanged=True,coreMapMaterialsAndTexturesUnchanged=True,treeModelDocsUnchanged=True,
        trees=tree_count,firs=fir_count,newObjects=0,newTextures=0,newShaders=0,physicsUnchanged=True,
        allCanopyBoundsOutsideAO=True,maximumBaseAboveSoilInches=float(max(root_errors)),
        needleFacesFromNearOrRetainedLegacy=True,geometry=results,
        declaredSceneGeometry=budgets,sampledSilhouette=scores,
        sourceHashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'Tools/forestbase_crown_lods_blender.py',
            ROOT/'Tools/forestbase_crown_obj.py',ROOT/'Tools/forestbase_crown_coverage.py',ROOT/'Tools/forestbase_crown_audit.py')},
        limitations=['Declared triangle savings do not establish native GPU savings; increased alpha coverage can increase pixel/shadow work.',
            'The 16 bilinear atlas-mask views do not reproduce native mips, anisotropy, lighting or transitions.',
            'Full reference fidelity and current engine verification remain unfinished.'])
    (STAGE/'geometry-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('geometry','sourceHashes','limitations')}))


if __name__=='__main__':main()
