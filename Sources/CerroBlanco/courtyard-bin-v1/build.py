"""Stage one hooded courtyard bin; preserve every unrelated dressing record."""
from pathlib import Path
import sys,math,json,re,hashlib,collections
import numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as P,cerroblanco_parts as C
from cerroblanco_bollards_upgrade import split_obj,remap_faces
OUT=ROOT/'output/cerroblanco/courtyard-bin-v1'
RESOURCE='models/maps/cerroblanco/courtyard-bin-v1'
PROP='models/props/cerroblanco/hooded_bin_v1'
SOURCE=ROOT/'Assets/models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj'
STEEL='cb_steel';DARK='cb_black'

def build():
    m=K.Model()
    def lathe(profile,mat,start=0,end=360):
        segments=max(2,round(64*(end-start)/360))
        # Smooth only along a continuous profile; separate profiles retain seams.
        ns=[]
        for i in range(len(profile)):
            a=np.array(profile[max(i-1,0)]);b=np.array(profile[min(i+1,len(profile)-1)])
            dr,dz=b-a;l=math.hypot(dr,dz);ns.append((dz/l,-dr/l))
        for j,((r0,z0),(r1,z1)) in enumerate(zip(profile,profile[1:])):
            for i in range(segments):
                a,b=[math.radians(start+(end-start)*k/segments) for k in (i,i+1)]
                cs=[(math.cos(a),math.sin(a)),(math.cos(b),math.sin(b))]
                points=[(r0*cs[0][0],r0*cs[0][1],z0),(r0*cs[1][0],r0*cs[1][1],z0),
                        (r1*cs[1][0],r1*cs[1][1],z1),(r1*cs[0][0],r1*cs[0][1],z1)]
                normals=[(ns[j][0]*cs[0][0],ns[j][0]*cs[0][1],ns[j][1]),(ns[j][0]*cs[1][0],ns[j][0]*cs[1][1],ns[j][1]),
                         (ns[j+1][0]*cs[1][0],ns[j+1][0]*cs[1][1],ns[j+1][1]),(ns[j+1][0]*cs[0][0],ns[j+1][0]*cs[0][1],ns[j+1][1])]
                # Collapse the apex of a closed cap into one triangle.
                if r0==0:points=points[1:];normals=normals[1:]
                if r1==0:points=points[:3];normals=normals[:3]
                dr,dz=r1-r0,z1-z0;mid=(a+b)/2
                P.card(m,mat,points,(dz*math.cos(mid),dz*math.sin(mid),-dr),normals=normals)
    lathe([(7.7,0),(8.05,.25),(8.05,1.35),(8.4,1.6)],DARK)
    lathe([(8.4,1.6),(8.8,1.85),(8.98,2.2),(8.98,3.0)],STEEL)
    # A front access panel occupies a real sector of the shell, with two open seams.
    lathe([(8.98,3.0),(8.98,25.3)],STEEL,280.3,529.7)
    lathe([(8.91,3.12),(8.91,25.2)],STEEL,170.3,279.7)
    lathe([(8.98,25.3),(8.98,26.4),(8.91,26.7),(8.65,26.9),(8.35,26.9),(8.10,26.65),(8.1,26.3)],STEEL)
    # Recessed liner: inner wall, bottom and rolled black edge, with no top disk.
    lathe([(8.1,26.3),(7.96,26.0),(7.96,3.2),(0,3.2)],DARK)
    # Shallow crowned rain hood, closed underside and rolled lip.
    lathe([(9,32.4),(9,32.7),(8.87,32.95),(8.3,33.15),(6.5,33.6),(3.5,33.9),(0,34)],STEEL)
    lathe([(0,32.25),(8.65,32.25),(9,32.4)],DARK)
    # Posts sit on the rolled rim, rather than floating over the liner opening.
    # Both ends penetrate the receiving material; welded sockets make the
    # load path legible from player height and under the hood.
    for x in (-8.5,8.5):
        P.rod(m,(x,0,25.8),(x,0,32.55),.32,STEEL,24,True)
        P.rod(m,(x,0,26.35),(x,0,27.25),.47,STEEL,24,True)
        P.rod(m,(x,0,31.95),(x,0,32.6),.43,STEEL,24,True)
    # Service lock and hinge knuckles use the existing stainless/dark finishes.
    a=math.radians(220);out=np.array((math.cos(a),math.sin(a),0))
    P.rod(m,out*8.89+(0,0,21.8),out*9.07+(0,0,21.8),.43,STEEL,24,True)
    P.rod(m,out*9.075+(0,0,21.8),out*9.085+(0,0,21.8),.10,DARK,12,True)
    for z in (7.8,21.8):P.rod(m,(1.57,-8.82,z-.7),(1.57,-8.82,z+.7),.17,STEEL,12,True)
    m.material_overrides.update({STEEL:'materials/cerroblanco/quality-v1/cb_steel.vmat',DARK:'materials/cerroblanco/cb_black.vmat'})
    m.tile_overrides.update({STEEL:24.,DARK:64.})
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
    old=K.Model();old.cylinder((380,-650),9,0,34,{"side":STEEL,"top":DARK,"bottom":None},sides=16,surface=C.METAL);old.tile_overrides.update({STEEL:24.,DARK:64.});K.write_obj(OUT/'original.obj',old,'original')
    targets=collections.Counter(keys(OUT/'original.obj'));source=SOURCE.read_bytes()
    lines,vertices,uvs,normals=split_obj(source.decode());it=iter(keys(SOURCE));kept=[];removed=0
    for l in lines:
        if l.startswith('f '):
            key=next(it)
            if targets[key]:targets[key]-=1;removed+=1;continue
        kept.append(l)
    assert not any(targets.values()) and removed==46,(removed,targets)
    m=build();prop=OUT/'stage'/PROP;K.write_model(prop,PROP,'bin',m)
    for mat,rows in m.polygons.items():
        for i,(pts,n) in enumerate(rows):rows[i]=([p+np.array((380,-650,0)) for p in pts],n)
    fresh=OUT/'bin-placed.obj';added=K.write_obj(fresh,m,'courtyard_bin')
    new,nv,nt,nn=split_obj(fresh.read_text());merged=[];inserted=set()
    groups=[('vt ','v',[s for s in new if s.startswith('v ')]),('vn ','vt',nt),('usemtl ','vn',nn)]
    for line in kept:
        for prefix,key,values in groups:
            if line.startswith(prefix) and key not in inserted:merged.extend(values);inserted.add(key)
        merged.append(line)
    assert inserted=={'v','vt','vn'}
    merged.extend(remap_faces(new,len(vertices),len(uvs),len(normals)))
    dest=OUT/'stage'/RESOURCE;dest.mkdir(parents=True,exist_ok=True)
    (dest/'dressing.obj').write_text(('\n'.join(merged)+'\n').replace('mtllib cerroblanco_dressing_v2.mtl','mtllib dressing.mtl'))
    (dest/'dressing.mtl').write_bytes(SOURCE.with_suffix('.mtl').read_bytes())
    before=SOURCE.with_suffix('.vmdl').read_text();after=before.replace('models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj',RESOURCE+'/dressing.obj')
    assert before!=after
    if 'PhysicsShapeList' in before:assert before.split('PhysicsShapeList',1)[1]==after.split('PhysicsShapeList',1)[1]
    (dest/'dressing.vmdl').write_text(after)
    report={'source_sha256':hashlib.sha256(source).hexdigest(),'removed_triangles':removed,'added_triangles':added,'other_faces_preserved':sum(l.startswith('f ') for l in kept),'collision_unchanged':True,'standalone_asset':PROP+'/bin.vmdl'}
    (OUT/'geometry-checks.json').write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':main()
