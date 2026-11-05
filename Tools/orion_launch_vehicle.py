"""Approved Orion launch vehicle. Pure geometry plus a standalone scene-instance adapter."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
import orion_parts as O
import orion_textures as OT
X=np.array((1.,0,0));Y=np.array((0.,1.,0));Z=np.array((0.,0.,1.))
def model(lod=0,height=1300.,radius=66.):
    H=float(height);r=float(radius)
    m=K.Model();n=(96,64,32)[lod];small=(32,20,12)[lod]
    def lathe(center,axis,profile,paint,sides=None):G.lathe_axis(m,np.asarray(center,float),np.asarray(axis,float),np.asarray(profile,float),paint,sides=sides or n)
    def tube(points,rad,paint='oa_nozzle',sides=None):G.tube(m,[np.asarray(p,float) for p in points],rad,paint,sides=sides or (8,6,4)[lod])
    def box(center,size,paint,bevel=.2,axes=(X,Y,Z)):
        if lod<2:G.bevel_box(m,np.asarray(center,float),axes,size,paint,bevel=bevel)
        else:m.oriented_box(np.asarray(center,float),axes,size,paint)
    def face(points,normal,paint):G._face(m,paint,[np.asarray(p,float) for p in points],towards=np.asarray(normal,float))
    def ring(z,rr,minor=.35,paint='oa_rocket_dark',segments=None):G.torus(m,(0,0,z),Z,rr,minor,paint,seg=segments or n,sides=(6,5,4)[lod])
    # Turned body and fairing keep the original stage proportions, height, livery and logo placement.
    lathe((0,0,0),Z,[(0,0),(r*1.06,0),(r*1.06,H*.02),(r,H*.05)],'oa_rocket_dark')
    for lo,hi,rr,paint in ((.05,.719,r,'oa_rocket'),(.719,.729,r,'oa_rocket_dark'),(.729,.770,r,'oa_rocket'),(.770,.788,r,'oa_gold'),(.788,.901,r*.98,'oa_rocket')):
        lathe((0,0,0),Z,[(rr,H*lo),(rr,H*hi)],paint)
    def nose(t):return r*math.sqrt(max(0,1-t*t))*(1-.04*t)
    ts=np.linspace(0,1,(29,19,11)[lod]);profile=[(r*.98,H*.901)]+[(nose(t),H*(.901+.099*t)) for t in ts[1:]]
    lathe((0,0,0),Z,profile,'oa_rocket')
    # Formed circumferential joints, flange edges and lower skirt stiffeners.
    for z in (.05,.18,.32,.48,.635,.719,.729,.77,.788,.901):
        rr=r*.98 if z>.788 else r;ring(H*z,rr+.2,.32,'oa_rocket_dark' if z<.77 else 'oa_rocket')
    for angle in np.linspace(0,math.tau,(32,24,16)[lod],endpoint=False):
        d=np.array((math.cos(angle),math.sin(angle),0));t=np.cross(Z,d)
        if lod<2:box(d*(r*1.035)+Z*(H*.023),(1.6,1.1,H*.032),'oa_nozzle',.15,(t,d,Z))
        # Interstage load-transfer ribs, with a recessed dark valley between each one.
        box(d*(r+.5)+Z*(H*.724),(2.0,1.1,H*.008),'oa_rocket_dark',.12,(t,d,Z))
    # Twin service raceways on the rear side, with curved end terminations and clamp shoes.
    for angle in (math.radians(60),math.radians(120)):
        d=np.array((math.cos(angle),math.sin(angle),0));t=np.cross(Z,d)
        box(d*(r+1.5)+Z*(H*.377),(5,3,H*.605),'oa_rocket',.6,(t,d,Z))
        if lod<2:
            for z in np.linspace(H*.085,H*.67,12):box(d*(r+3.1)+Z*z,(6.5,1.4,2.0),'oa_rocket_dark',.18,(t,d,Z))
        tube([d*(r+.3)+Z*(H*.06),d*(r+2.8)+Z*(H*.075),d*(r+2.8)+Z*(H*.09)],.75,'oa_nozzle')
    # Flush service access plates and umbilical connectors stay off the lettering face.
    for angle,z in ((0,H*.11),(math.pi,H*.13),(math.pi*.5,H*.69)):
        d=np.array((math.cos(angle),math.sin(angle),0));t=np.cross(Z,d)
        box(d*(r+.4)+Z*z,(15,1.1,22),'oa_rocket_dark',.65,(t,d,Z))
        box(d*(r+1.0)+Z*z,(13,.3,20),'oa_rocket',.5,(t,d,Z))
        if lod==0:
            for dx in (-5.6,5.6):
                for dz in (-8.6,8.6):lathe(d*(r+1.25)+t*dx+Z*(z+dz),d,[(0,0),(.4,0),(.4,.16),(0,.16)],'oa_nozzle',8)
    # Four airfoil fins: rounded root fillets, swept tips, tapered thickness and connected edge surfaces.
    for k in range(4):
        a=math.pi/4+k*math.pi/2;d=np.array((math.cos(a),math.sin(a),0));s=np.cross(Z,d)
        outline=[(r*.98,H*.012),(r*1.9,-H*.012),(r*1.75,H*.07),(r*.98,H*.2)]
        mid=np.mean(np.array(outline),axis=0)
        for sign in (-1,1):
            # The broad airfoil face has a raised ridge rather than the original flat rectangular sheet.
            ridge=d*mid[0]+Z*mid[1]+s*sign*4.2
            vertices=[d*rr+Z*zz+s*sign*(2.0 if i in (0,3) else .5) for i,(rr,zz) in enumerate(outline)]
            for i in range(4):face([vertices[i],vertices[(i+1)%4],ridge],s*sign,'oa_rocket')
        for i in range(4):
            j=(i+1)%4;aa,bb=outline[i],outline[j]
            ta=2 if i in (0,3) else .5;tb=2 if j in (0,3) else .5
            q=[d*aa[0]+Z*aa[1]-s*ta,d*bb[0]+Z*bb[1]-s*tb,d*bb[0]+Z*bb[1]+s*tb,d*aa[0]+Z*aa[1]+s*ta]
            out=d if i==1 else -Z if i==0 else Z+d*.4 if i==2 else -d;face(q,out,'oa_rocket_dark' if i in (0,1) else 'oa_rocket')
        for sign in (-1,1):tube([d*(r+.2)+Z*(H*.015)+s*sign*3,d*(r+2.5)+Z*(H*.07)+s*sign*3,d*(r+.2)+Z*(H*.19)+s*sign*3],1.2,'oa_rocket')
        if lod<2:
            for z in np.linspace(H*.035,H*.16,5):box(d*(r+1)+s*3.8+Z*z,(3,2,4),'oa_nozzle',.2,(s,d,Z))
    # Thick-walled curved nozzles, internal liners, rolled lips and engine gimbal/carrier hardware.
    for k in range(4):
        a=math.pi/4+k*math.pi/2;c=np.array((math.cos(a)*r*.45,math.sin(a)*r*.45,0))
        levels=np.linspace(0,1,(15,10,7)[lod])
        def bell(t):return r*(.12+.20*(1-t)**.72)
        outer=[(bell(t),-26+28*t) for t in levels]
        inner=[(max(1,rr-.8),z+.12) for rr,z in outer[::-1]]
        lathe(c,Z,outer+inner+[outer[0]],'oa_nozzle',small)
        G.torus(m,c+Z*-25.9,Z,r*.32-.25,.65,'oa_nozzle',seg=small,sides=6 if lod<2 else 4)
        if lod<2:
            for t in np.linspace(.12,.9,(10,4)[lod]):
                G.torus(m,c+Z*(-26+28*t),Z,bell(t)+.12,.28,'oa_nozzle',seg=(24,16)[lod],sides=4)
        lathe(c+Z*2,Z,[(0,0),(r*.13,0),(r*.14,4),(r*.10,8),(0,8)],'oa_rocket_dark',small)
        for j in range(3):
            angle=a+j*math.tau/3;side=np.array((math.cos(angle),math.sin(angle),0))
            tube([c+side*10+Z*8,c+side*14-Z*8],.8,'oa_nozzle')
            tube([c+side*12+Z*8,c+side*18+Z*17],1.1,'oa_rocket_dark')
        if lod==0:
            tube([c+np.array((8,0,7)),c+np.array((13,0,-2)),c+np.array((20,0,-14))],.6,'oa_gold')
    # Fairing split lines and lower retaining strips follow the actual ogive.
    if lod<2:
        for a in (math.radians(30),math.radians(210)):
            d=np.array((math.cos(a),math.sin(a),0));points=[d*(nose(t)+.16)+Z*(H*(.901+.099*t)) for t in np.linspace(.025,.975,(28,16)[lod])]
            tube(points,.20,'oa_rocket_dark',5)
    f=np.array((-.25,-1,0));f/=np.linalg.norm(f);right=np.cross(Z,f)
    O.letters(m,'mark',f*(r+.6)+Z*(H*.478),right,r*1.2,'dark',off=0)
    O.letters(m,'orn',f*(r+.6)+Z*(H*.342),right,r*2.6,'dark',off=0)
    for paint in m.polygons:
        m.material_overrides[paint]=f'materials/orion/{paint}.vmat'
        m.tile_overrides[paint]=OT.TILES.get(paint,64.)
    m.anchored_paints=set();m.decal_paints=set()
    return m

def objects(ids,placements):
    result=[]
    reference=math.atan2(-1.,-.25)
    for index,(position,height,radius,facing) in enumerate(placements):
        key='launch_vehicle' if index==0 else f'launch_vehicle/{index}'
        yaw=math.degrees(math.atan2(facing[1],facing[0])-reference)
        scale=K.vec((radius/66.,radius/66.,height/1300.))
        result.append(K.game_object(ids,'Orion Launch Vehicle',key,K.to_world(position),K.yaw_rotation(yaw),scale=scale,components=[
            K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',BodyGroups=18446744073709551615,Model='models/props/orion/launch_vehicle_v1/vehicle.vmdl',RenderType='On',Tint='1,1,1,1')]))
    return result
