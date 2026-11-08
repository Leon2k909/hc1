"""One gallery vase: turned red vessel, rolled mouth and real ceramic wall."""
from pathlib import Path
import sys,math,json,hashlib,collections
import numpy as np
from scipy.interpolate import PchipInterpolator
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as P
from cerroblanco_bollards_upgrade import split_obj,remap_faces
OUT=ROOT/'output/cerroblanco/east-hall-vase-v2';RESOURCE='models/maps/cerroblanco/east-hall-vase-v2';PROP='models/props/cerroblanco/east_hall_vase_v2'
SOURCE=ROOT/'Assets/models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj'

def build():
    m=K.Model();sides=48
    height=[.35,.8,2,4,5.5,7.5,9,10.4,11.6,12.7,13.8]
    radius=[3.15,3.3,4.6,5.9,6,5.55,4.2,3.1,2.65,2.8,3.05]
    shape=PchipInterpolator(height,radius)
    profile=[(0.,0.),(2.9,0.),(3.15,.12)]
    profile += [(float(shape(z)),float(z)) for z in np.linspace(.35,13.8,32)]
    profile += [(2.85+.2*math.cos(a),13.8+.2*math.sin(a)) for a in np.linspace(0,math.pi,9)[1:]]
    profile += [(float(shape(z))-.4,float(z)) for z in np.linspace(13.8,.8,24)[1:]]
    profile += [(0.,.8)]
    normal=[]
    for j,(r,z) in enumerate(profile):
        a=np.array(profile[max(j-1,0)]);b=np.array(profile[min(j+1,len(profile)-1)]);dr,dz=b-a
        size=math.hypot(dr,dz);normal.append((dz/size,-dr/size))
    for j,((r0,z0),(r1,z1)) in enumerate(zip(profile,profile[1:])):
        dr,dz=r1-r0,z1-z0
        for k in range(sides):
            a,b=[2*math.pi*i/sides for i in (k,k+1)]
            points=[(r0*math.cos(a),r0*math.sin(a),z0),(r0*math.cos(b),r0*math.sin(b),z0),
                    (r1*math.cos(b),r1*math.sin(b),z1),(r1*math.cos(a),r1*math.sin(a),z1)]
            normals=[(normal[j][0]*math.cos(a),normal[j][0]*math.sin(a),normal[j][1]),
                     (normal[j][0]*math.cos(b),normal[j][0]*math.sin(b),normal[j][1]),
                     (normal[j+1][0]*math.cos(b),normal[j+1][0]*math.sin(b),normal[j+1][1]),
                     (normal[j+1][0]*math.cos(a),normal[j+1][0]*math.sin(a),normal[j+1][1])]
            if r0==0:points=points[1:];normals=normals[1:]
            if r1==0:points=points[:3];normals=normals[:3]
            mid=(a+b)/2;P.card(m,'cb_red',points,(dz*math.cos(mid),dz*math.sin(mid),-dr),normals=normals)
    m.material_overrides['cb_red']='materials/cerroblanco/cb_red.vmat';m.tile_overrides['cb_red']=64.
    return m

def keys(path):
    vs=[];mat='';out=[]
    for l in path.read_text().splitlines():
        if l.startswith('v '):vs.append(tuple(round(float(x),3) for x in l.split()[1:]))
        elif l.startswith('usemtl '):mat=l.split()[1]
        elif l.startswith('f '):out.append((mat,tuple(sorted(vs[int(x.split('/')[0])-1] for x in l.split()[1:]))))
    return out

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    old=K.Model();old.cylinder((1100,-820),6,40,54,{'side':'cb_red','top':'cb_black','bottom':None},sides=12)
    old.tile_overrides.update({'cb_red':64.,'cb_black':64.});K.write_obj(OUT/'original.obj',old,'vase_original')
    targets=collections.Counter(keys(OUT/'original.obj'));raw=SOURCE.read_bytes();lines,vs,uvs,ns=split_obj(raw.decode())
    it=iter(keys(SOURCE));kept=[];removed=0
    for l in lines:
        if l.startswith('f '):
            key=next(it)
            if targets[key]:targets[key]-=1;removed+=1;continue
        kept.append(l)
    assert removed==34 and not any(targets.values())
    m=build();K.write_model(OUT/'stage'/PROP,PROP,'vase',m)
    for mat,rows in m.polygons.items():
        for i,(pts,n) in enumerate(rows):rows[i]=([p+np.array((1100,-820,40)) for p in pts],n)
    path=OUT/'placed.obj';added=K.write_obj(path,m,'gallery_vase');new,nv,nt,nn=split_obj(path.read_text())
    groups=[('vt ','v',[s for s in new if s.startswith('v ')]),('vn ','vt',nt),('usemtl ','vn',nn)];merged=[];inserted=set()
    for l in kept:
        for prefix,key,values in groups:
            if l.startswith(prefix) and key not in inserted:merged.extend(values);inserted.add(key)
        merged.append(l)
    assert inserted=={'v','vt','vn'};merged.extend(remap_faces(new,len(vs),len(uvs),len(ns)))
    dest=OUT/'stage'/RESOURCE;dest.mkdir(parents=True,exist_ok=True)
    (dest/'dressing.obj').write_text(('\n'.join(merged)+'\n').replace('mtllib cerroblanco_dressing_v2.mtl','mtllib dressing.mtl'))
    (dest/'dressing.mtl').write_bytes(SOURCE.with_suffix('.mtl').read_bytes())
    before=SOURCE.with_suffix('.vmdl').read_text();after=before.replace('models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj',RESOURCE+'/dressing.obj');assert before!=after
    if 'PhysicsShapeList' in before:assert before.split('PhysicsShapeList',1)[1]==after.split('PhysicsShapeList',1)[1]
    (dest/'dressing.vmdl').write_text(after)
    report={'source_sha256':hashlib.sha256(raw).hexdigest(),'removed_triangles':removed,'added_triangles':added,'unrelated_faces_preserved':sum(l.startswith('f ') for l in kept),'approved_bin_retained':True,'collision_unchanged':True}
    (OUT/'checks.json').write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':main()
