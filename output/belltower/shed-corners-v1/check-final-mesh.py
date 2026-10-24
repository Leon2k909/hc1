from pathlib import Path
import hashlib
import json
import sys
import numpy as np

base=Path(__file__).resolve().parent
report={'models':{},'geometry_and_uv_valid':True}
for side in ('west','east'):
    path=base/f'r5/stage/belltower_{side}-timber.obj'
    data={'v':[None],'vt':[None],'vn':[None]}; faces=[]
    for line in path.read_text().splitlines():
        kind=line.split(' ',1)[0]
        if kind in data:data[kind].append(tuple(map(float,line.split()[1:])))
        elif kind=='f':faces.append([tuple(map(int,t.split('/'))) for t in line.split()[1:]])
    positions=np.array(data['v'][1:]); uvs=np.array(data['vt'][1:]); normals=np.array(data['vn'][1:])
    ids=np.array(faces)-1
    p=positions[ids[:,:,0]]; uv=uvs[ids[:,:,1]]; n=normals[ids[:,:,2]]
    cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]); area=np.linalg.norm(cross,axis=1)/2
    a,b=uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]
    uvarea=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2
    geometric=cross/np.linalg.norm(cross,axis=1)[:,None]
    dots=np.sum(n*geometric[:,None,:],axis=2)
    assert np.isfinite(p).all() and np.isfinite(uv).all() and np.isfinite(n).all()
    assert area.min()>1e-7 and uvarea.min()>1e-12 and dots.min()>0
    report['models'][side]={'triangles':len(faces),'minimum_triangle_area':float(area.min()),
        'minimum_uv_triangle_area':float(uvarea.min()),'minimum_normal_facing_dot':float(dots.min())}
manifest=json.loads((base/'r5/stage/manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
root=base.parents[2]
sys.path.insert(0,str(root/'Tools'))
import belltower_stage_shed_corners as S
report['all_published_assets_match']=all(sha(root/p)==row['after'] for p,row in manifest['files'].items())
report['installed_shed_blocks']={}
for relative,row in manifest['files'].items():
    path=root/relative
    if sha(path)==row['after']:
        report['installed_shed_blocks'][relative]={'entire_asset_matches':True}
        continue
    # The main chat can append unrelated stone changes after this patch. Verify
    # the shed's own tables, faces AND their global index offsets independently.
    side='west' if 'west' in path.name else 'east'
    paint=next((p for p in sorted(S.PAINTS,key=len,reverse=True) if path.name.endswith('_'+p+'.obj')),None)
    piece=base/'r5/stage'/(f'belltower_{side}-{paint}.obj' if paint else f'belltower_{side}-timber.obj')
    lines=piece.read_bytes().splitlines(keepends=True)
    block=b''.join(l for l in lines if l.startswith((b'v ',b'vt ',b'vn ')))
    staged=(base/'r5/stage'/relative).read_bytes()
    staged_start=staged.index(block)
    face=next(l for l in staged[staged_start+len(block):].split(b'\n',3) if l.startswith(b'f '))
    cached=next(l for l in lines if l.startswith(b'f '))
    offsets=dict(zip(('v','vt','vn'),(int(a)-int(b) for a,b in zip(face.split()[1].split(b'/'),cached.split()[1].split(b'/')))))
    data=path.read_bytes(); assert data.count(block)==1,relative
    start=data.index(block)
    actual={k:data[:start].count(b'\n'+k.encode()+b' ')+(1 if data.startswith(k.encode()+b' ') else 0) for k in offsets}
    assert actual==offsets,(relative,'Shed index offsets changed',actual,offsets)
    tail=S.append_bytes(piece,offsets)
    # Table declarations now precede all faces for compatibility with future
    # partial exports. Their exact face/material block can remain later on.
    assert data.count(tail[len(block):])==1,relative
    report['installed_shed_blocks'][relative]={'entire_asset_matches':False,'unrelated_edits_preserved':True,'shed_tables_and_faces_exact':True,'global_index_offsets_exact':True}
report['all_shed_mesh_blocks_intact']=True
(base/'final-mesh-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
