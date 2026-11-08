"""One cafe grinder: hopper/beans, burr body, chute and dosing forks."""
from pathlib import Path
import sys,math,json,hashlib,collections
import numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as P,cerroblanco_fitout as F
from cerroblanco_bollards_upgrade import split_obj,remap_faces
OUT=ROOT/'output/cerroblanco/cafe-grinder-v1';RESOURCE='models/maps/cerroblanco/cafe-grinder-v1';PROP='models/props/cerroblanco/cafe_grinder_v1'
SOURCE=ROOT/'Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj'
X=(1,0,0);Y=(0,1,0);Z=(0,0,1);AX=(X,Y,Z)

def build():
    m=K.Model()
    def lathe(profile,mat,centre=(0,0,0),sides=40):
        c=np.array(centre);ns=[]
        for j in range(len(profile)):
            dr,dz=np.array(profile[min(j+1,len(profile)-1)])-profile[max(j-1,0)];size=math.hypot(dr,dz);ns.append((dz/size,-dr/size))
        for j,((r0,z0),(r1,z1)) in enumerate(zip(profile,profile[1:])):
            dr,dz=r1-r0,z1-z0
            for k in range(sides):
                a,b=[2*math.pi*i/sides for i in (k,k+1)]
                pts=[c+(r0*math.cos(a),r0*math.sin(a),z0),c+(r0*math.cos(b),r0*math.sin(b),z0),c+(r1*math.cos(b),r1*math.sin(b),z1),c+(r1*math.cos(a),r1*math.sin(a),z1)]
                normals=[(ns[j][0]*math.cos(a),ns[j][0]*math.sin(a),ns[j][1]),(ns[j][0]*math.cos(b),ns[j][0]*math.sin(b),ns[j][1]),(ns[j+1][0]*math.cos(b),ns[j+1][0]*math.sin(b),ns[j+1][1]),(ns[j+1][0]*math.cos(a),ns[j+1][0]*math.sin(a),ns[j+1][1])]
                if r0==0:pts=pts[1:];normals=normals[1:]
                if r1==0:pts=pts[:3];normals=normals[:3]
                mid=(a+b)/2;P.card(m,mat,pts,(dz*math.cos(mid),dz*math.sin(mid),-dr),normals=normals)
    def box(c,size,mat,bevel=.12):P.bevel_box(m,c,AX,size,mat,bevel=bevel)
    # Stable feet, formed tray, eased motor casing and burr housing.
    for x in (-2.8,2.8):
        for y in (-3.4,2.6):lathe([(0,0),(.4,0),(.4,.35),(0,.35)],'cb_black',(x,y,0),16)
    box((0,-.4,.63),(7.2,8.2,.65),'cb_steel',.18)
    box((0,-1.7,1.0),(6.5,4.5,.18),'cbf_track',.06)
    box((0,.65,5.2),(5.8,4.6,8.5),'cbf_track',.48)
    lathe([(0,9.3),(2.7,9.3),(2.9,9.55),(2.9,10),(2.65,10.18),(0,10.18)],'cb_steel')
    for i in range(20):
        a=math.tau*i/20
        P.rod(m,(2.84*math.cos(a),2.84*math.sin(a),9.55),(2.84*math.cos(a),2.84*math.sin(a),9.98),.075,'cbf_track',8,True)
    lathe([(0,10.1),(1.8,10.1),(1.8,10.6),(0,10.6)],'cbf_track')
    # Transparent hopper has an actual wall thickness and overlaps the collar.
    lathe([(1.52,10.35),(3.4,14.45),(3.45,15.35),(3.32,15.35),(3.27,14.48),(1.39,10.35),(1.52,10.35)],'cb_glass')
    lathe([(0,15.3),(3.43,15.3),(3.65,15.47),(3.65,15.72),(3.35,15.98),(0,15.98)],'cbf_track')
    lathe([(0,10.5),(1.42,10.5),(2.96,13.95),(2.4,14.12),(0,14.25)],'grinder_beans')
    rng=np.random.default_rng(417)
    for k in range(24):
        a=rng.uniform(0,math.tau);r=math.sqrt(rng.uniform(0,1))*2.5;c=np.array((r*math.cos(a),r*math.sin(a),14.25-.12*(r/2.5)**2))
        yaw=rng.uniform(0,math.tau);rotation=np.array(((math.cos(yaw),-math.sin(yaw),0),(math.sin(yaw),math.cos(yaw),0),(0,0,1)))
        scale=np.array((.29,.17,.14))
        def point(t,p):
            unit=np.array((math.sin(t)*math.cos(p),math.sin(t)*math.sin(p),math.cos(t)))
            pos=unit*scale
            if pos[2]>0:pos[2]-=.025*math.exp(-(pos[1]/.035)**2)*(pos[2]/scale[2])
            return c+rotation@pos,P.unit(rotation@(unit/scale))
        for row in range(5):
            for column in range(10):
                uv=[(math.pi*row/5,math.tau*column/10),(math.pi*row/5,math.tau*(column+1)/10),(math.pi*(row+1)/5,math.tau*(column+1)/10),(math.pi*(row+1)/5,math.tau*column/10)]
                if row==0:uv=uv[1:]
                if row==4:uv=uv[:3]
                data=[point(t,p) for t,p in uv];pts,ns=zip(*data);P.card(m,'grinder_beans',pts,sum(ns),normals=ns)
    # Metal dosing chute is connected back into the motor casing.
    box((0,-2.35,7.0),(1.7,2.3,1.55),'cb_steel',.18)
    box((0,-3.42,6.8),(1.2,.18,.72),'cb_black',.035)
    box((0,-1.72,8.62),(2.3,.22,1.0),'cb_steel',.1)
    box((0,-1.86,8.62),(1.9,.08,.65),'cbf_screen',.035)
    P.rod(m,(1.85,-1.62,8.5),(1.85,-1.86,8.5),.27,'cb_steel',20,True)
    P.rod(m,(1.85,-1.86,8.5),(1.85,-1.9,8.5),.16,'cb_black',16,True)
    # Portafilter forks meet a crossbar that penetrates the casing.
    P.rod(m,(-1.6,-1.55,4.3),(1.6,-1.55,4.3),.17,'cb_steel',16,True)
    for x in (-1.05,1.05):P.rod(m,(x,-1.55,4.3),(x,-3.85,4.3),.15,'cb_steel',16,True)
    m.material_overrides.update({'cb_steel':'materials/cerroblanco/quality-v1/cb_steel.vmat','cb_black':'materials/cerroblanco/cb_black.vmat','cbf_track':'materials/cerroblanco/fitout/cbf_track.vmat','cbf_screen':'materials/cerroblanco/fitout/cbf_screen.vmat','cb_glass':'materials/cerroblanco/cb_glass.vmat','grinder_beans':PROP+'/beans.vmat'})
    m.tile_overrides.update({name:24. for name in m.polygons})
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
    old=K.Model();F.lathe(old,'cb_black',(600,616,42),[(0,0),(3.4,0),(3,9),(1.5,10)],sides=12);F.lathe(old,'cbf_screen',(600,616,52),[(1.5,0),(3.6,5.5),(3.8,6)],sides=12)
    old.tile_overrides.update({'cb_black':64.,'cbf_screen':64.});K.write_obj(OUT/'original.obj',old,'grinder_old')
    targets=collections.Counter(keys(OUT/'original.obj'));raw=SOURCE.read_bytes();lines,vs,uvs,ns=split_obj(raw.decode());it=iter(keys(SOURCE));kept=[];removed=0
    for l in lines:
        if l.startswith('f '):
            key=next(it)
            if targets[key]:targets[key]-=1;removed+=1;continue
        kept.append(l)
    assert removed==128 and not any(targets.values()),removed
    m=build();dest=OUT/'stage'/PROP;K.write_model(dest,PROP,'grinder',m)
    (dest/'beans.vmat').write_text('''"Layer0"\n{\n shader "shaders/complex.shader"\n F_SPECULAR "1"\n g_flMetalness "0"\n g_flRoughnessScaleFactor "1"\n TextureColor "materials/default/default_color.tga"\n TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "[0.64 0.64 0.64 0]"\n TextureAmbientOcclusion "materials/default/default_ao.tga"\n g_vColorTint "[0.12 0.048 0.022 1]"\n g_flModelTintAmount "1"\n}\n''')
    for mat,rows in m.polygons.items():
        for i,(pts,n) in enumerate(rows):rows[i]=([p+np.array((600,616,42)) for p in pts],n)
    path=OUT/'placed.obj';added=K.write_obj(path,m,'cafe_grinder');new,nv,nt,nn=split_obj(path.read_text())
    # This installed OBJ has later appended vertex blocks. Keep their declaration
    # order/indices intact; add all new declarations only after the old records.
    merged=kept+[s for s in new if s.startswith('v ')]+nt+nn
    merged.extend(remap_faces(new,len(vs),len(uvs),len(ns)))
    dest=OUT/'stage'/RESOURCE;dest.mkdir(parents=True,exist_ok=True)
    (dest/'fine.obj').write_text(('\n'.join(merged)+'\n').replace('mtllib cerroblanco_fitout_fine.mtl','mtllib fine.mtl'))
    (dest/'fine.mtl').write_text(SOURCE.with_suffix('.mtl').read_text()+'\nnewmtl grinder_beans\nKd 1 1 1\n')
    before=SOURCE.with_suffix('.vmdl').read_text();after=before.replace('models/maps/cerroblanco/cerroblanco_fitout_fine.obj',RESOURCE+'/fine.obj');assert before!=after
    marker='{ from = "soil.vmat" to = "materials/buildings/soil.vmat" }';assert marker in after
    after=after.replace(marker,marker+',\n{ from = "grinder_beans.vmat" to = "'+PROP+'/beans.vmat" }')
    (dest/'fine.vmdl').write_text(after)
    report={'source_sha256':hashlib.sha256(raw).hexdigest(),'removed_triangles':removed,'added_triangles':added,'unrelated_faces_preserved':sum(l.startswith('f ') for l in kept),'collision_unchanged':True,'review_only':True}
    (OUT/'checks.json').write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':main()
