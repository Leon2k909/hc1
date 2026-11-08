"""Approved Cerro Blanco hooded bin; rolled rim and connected hood sockets."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P
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

def build_into(model,e,n):
    local=build()
    for mat,rows in local.polygons.items():
        for i,(points,normal) in enumerate(rows):
            rows[i]=([p+np.array((e,n,0)) for p in points],normal)
    model.extend(local)
