"""Audit staged forest scenery and declared mesh costs without accessing S&box."""
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'Assets';OUT=ROOT/'output/forestbase';STAGE=OUT/'forest-stage'
CACHE={}


def nodes(scene):
    result={}
    def visit(items,parent=None):
        for item in items:
            fields={k:v for k,v in item.items() if k!='Children'}
            result[item['__guid']]=(fields,parent,[c['__guid'] for c in item.get('Children',[])])
            visit(item.get('Children',[]),item['__guid'])
    visit(scene['GameObjects']);return result


def geometry(model,staged):
    key=(model,staged)
    if key in CACHE:return CACHE[key]
    source=STAGE/model if staged and (STAGE/model).exists() else ASSETS/model
    assert source.is_file(),source
    files=set(re.findall(r'filename = "([^"]+\.obj)"',source.read_text()))
    meshes=[]
    for file in files:
        vertices=[];triangles=0;normals=[];uvs=[];faces=[]
        mesh_source=STAGE/file if staged and (STAGE/file).exists() else ASSETS/file
        for line in mesh_source.read_text().splitlines():
            fields=line.split()
            if fields and fields[0]=='v':
                x,z,n=map(float,fields[1:4]);vertices.append((n,x,z))
            elif fields and fields[0]=='vt':uvs.append(tuple(map(float,fields[1:3])))
            elif fields and fields[0]=='vn':normals.append(tuple(map(float,fields[1:4])))
            elif fields and fields[0]=='f':
                triangles+=len(fields)-3
                if file.endswith('_horizon.obj'):
                    assert len(fields)==4 and all(len(v.split('/'))==3 and '//' not in v for v in fields[1:])
                    faces.append([tuple(int(i)-1 for i in v.split('/')) for v in fields[1:]])
        assert vertices and triangles
        if file.endswith('_horizon.obj'):
            assert all(math.isfinite(v) for p in vertices+normals+uvs for v in p)
            assert normals and uvs and all(abs(math.sqrt(sum(v*v for v in n))-1)<.005 for n in normals)
            for face in faces:
                assert all(0<=v<len(vertices) and 0<=t<len(uvs) and 0<=n<len(normals) for v,t,n in face)
                a,b,c=(vertices[v] for v,t,n in face)
                ab=[v-u for u,v in zip(a,b)];ac=[v-u for u,v in zip(a,c)]
                cross=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
                assert sum(v*v for v in cross)>1e-12,'Degenerate reduced branch triangle'
        meshes.append(dict(file=file,triangles=triangles,
                           mins=[min(v[i] for v in vertices) for i in range(3)],
                           maxs=[max(v[i] for v in vertices) for i in range(3)]))
    result=dict(triangles=max(m['triangles'] for m in meshes),meshes=meshes)
    CACHE[key]=result;return result


def renderer(node):return next((c for c in node.get('Components',[]) if c['__type']=='Sandbox.ModelRenderer'),None)
def vector(text):return tuple(map(float,text.split(',')))
def tree(node):
    r=renderer(node)
    return r and ('/forestbase/fir/' in r['Model'] or '/forestbase/sapling/' in r['Model'])


def main():
    for variant in 'abc':
        relative=f'models/maps/forestbase/fir/fir_{variant}.vmdl'
        original=(OUT/'forest-before/Assets'/relative).read_text()
        expected=original.replace(f'filename = "models/maps/forestbase/fir/fir_{variant}_lod2.obj"',
                                  f'filename = "models/maps/forestbase/fir/fir_{variant}_horizon.obj"')
        assert (STAGE/relative).read_text()==expected,'Unexpected regular fir ModelDoc change'
    before=json.loads((OUT/'forest-before/Assets/scenes/maps/ForestBase/forestbase.scene').read_text())
    after=json.loads((STAGE/'forestbase.scene').read_text())
    old,new=nodes(before),nodes(after);changed=[]
    assert old.keys()<=new.keys(),'Existing object removed'
    for guid,(a,parent,children) in old.items():
        b,new_parent,new_children=new[guid]
        assert parent==new_parent and children==[c for c in new_children if c in old]
        if a==b:continue
        assert a['Name'].startswith(('Fir ','Forest middle ','Far fir ')),a['Name']
        aa=json.loads(json.dumps(a));bb=json.loads(json.dumps(b))
        aa.pop('Scale');bb.pop('Scale')
        if a['Name'].startswith('Far fir '):
            ra,rb=renderer(aa),renderer(bb)
            assert rb['Model'] in (ra['Model'],ra['Model'].replace('_far.vmdl','_horizon.vmdl'))
            ra.pop('Model');rb.pop('Model')
        assert aa==bb,a['Name']
        assert max(abs(v) for v in vector(a['Rotation'])[:2])<1e-6,'Tilted tree needs separate bounds check'
        sx,sy,sz=vector(a['Scale']);tx,ty,tz=vector(b['Scale'])
        assert 0<tx<=sx and 0<ty<=sy and tz>=sz
        changed.append(a['Name'])
    assert {k:v for k,v in before.items() if k!='GameObjects'}=={k:v for k,v in after.items() if k!='GameObjects'}
    added=[data[0] for guid,data in new.items() if guid not in old]
    horizon_distances=[];new_understory=0
    for node in added:
        assert node['Name'].startswith(('Far fir infill ','Forest understory '))
        assert [c['__type'] for c in node['Components']]==['Sandbox.ModelRenderer']
        n,west,z=vector(node['Position']);e=-west
        sx,sy,sz=vector(node['Scale']);qx,qy,qz,qw=vector(node['Rotation'])
        model=geometry(renderer(node)['Model'],True)
        yaw=2*math.atan2(qz,qw);c,s=math.cos(yaw),math.sin(yaw)
        points=[]
        for mesh in model['meshes']:
            for x in (mesh['mins'][0],mesh['maxs'][0]):
                for y in (mesh['mins'][1],mesh['maxs'][1]):
                    points.append((n+c*x*sx-s*y*sy,west+s*x*sx+c*y*sy))
        # Entire horizontal tree bounds must remain beyond the playable AO.
        assert (min(x for x,y in points)>1450 or max(x for x,y in points)<-1730 or
                min(y for x,y in points)>1550 or max(y for x,y in points)<-1550),node['Name']
        if node['Name'].startswith('Far fir infill '):
            assert z==-120
        else:
            side=int(node['Name'].split()[2]);depth=(n-1450,-e-1550,e-1550,-n-1450)[side]
            assert abs(z-(-8-min(depth,300)*112/300))<.01
            new_understory+=1
    budget={};counts={};aspects={}
    for label,state,staged in (('before',old,False),('after',new,True)):
        total=0;count=0;ratios=[]
        for fields,parent,children in state.values():
            if not tree(fields):continue
            model=geometry(renderer(fields)['Model'],staged);total+=model['triangles'];count+=1
            if fields['Name'].startswith('Fir '):
                sx,sy,sz=vector(fields['Scale']);mesh=max(model['meshes'],key=lambda m:m['triangles'])
                dims=[b-a for a,b in zip(mesh['mins'],mesh['maxs'])]
                ratios.append(max(dims[0]*sx,dims[1]*sy)/(dims[2]*sz))
            if label=='after' and renderer(fields)['Model'].endswith('_horizon.vmdl'):
                n,west,z=vector(fields['Position']);e=-west
                distance=math.hypot(max(abs(e)-1550,0),max(n-1450,-1730-n,0))
                assert distance>=3600 and 0<model['triangles']<=5000
                horizon_distances.append(distance)
        budget[label]=total;counts[label]=count;aspects[label]=statistics.median(ratios)
    assert budget['after']<budget['before'] and aspects['after']<aspects['before']
    assert len(added)==88 and new_understory==24
    report=dict(scope='Offline scene/asset checks; maximum declared LOD triangle sum is not active GPU cost or FPS.',
                existingObjects=len(old),removedObjects=0,changedExistingTrees=len(changed),
                nonForestObjectsUnchanged=True,existingRootsRotationsParentsAndOrderUnchanged=True,
                addedRenderOnlyObjects=len(added),addedUnderstory=new_understory,
                forestTreeCounts=counts,maximumDeclaredLodTriangleSum=budget,
                declaredTriangleReduction=budget['before']-budget['after'],
                matureMedianWidthHeightRatio=aspects,horizonTrees=len(horizon_distances),
                regularFirLod2UsesDimensionalBranches=True,
                minimumHorizonRootDistanceMetres=min(horizon_distances)*.0254,
                treeAssets=[dict(model=p,staged=s,**v) for (p,s),v in CACHE.items()],
                sceneSha256=hashlib.sha256((STAGE/'forestbase.scene').read_bytes()).hexdigest(),
                limitations=['Native model compilation, alpha/LOD transitions, shadows, camera motion and performance remain unverified.'])
    (STAGE/'forest-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('treeAssets','limitations')}))


if __name__=='__main__':main()
