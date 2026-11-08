import math
import numpy as np
import map_kit as K
import riverdale_parts as P
def build():
    m=K.Model()
    def lathe(profile,mat,c,sides=32):
        c=np.array((*c,0.));ns=[]
        for j in range(len(profile)):
            dr,dz=np.array(profile[min(j+1,len(profile)-1)])-profile[max(j-1,0)];size=math.hypot(dr,dz);ns.append((dz/size,-dr/size))
        for j,((r0,z0),(r1,z1)) in enumerate(zip(profile,profile[1:])):
            dr,dz=r1-r0,z1-z0
            face=P.unit((dz,-dr));ends=[]
            for neighbour in (j-1,j+1):
                blended=face
                if 0<=neighbour<len(profile)-1:
                    drr,dzz=np.array(profile[neighbour+1])-profile[neighbour]
                    other=P.unit((dzz,-drr))
                    if np.dot(face,other)>.5:blended=P.unit(face+other)
                ends.append(blended)
            n0,n1=ends
            for k in range(sides):
                a,b=math.tau*k/sides,math.tau*(k+1)/sides
                pts=[c+(r0*math.cos(a),r0*math.sin(a),z0),c+(r0*math.cos(b),r0*math.sin(b),z0),c+(r1*math.cos(b),r1*math.sin(b),z1),c+(r1*math.cos(a),r1*math.sin(a),z1)]
                normals=[(n0[0]*math.cos(a),n0[0]*math.sin(a),n0[1]),(n0[0]*math.cos(b),n0[0]*math.sin(b),n0[1]),(n1[0]*math.cos(b),n1[0]*math.sin(b),n1[1]),(n1[0]*math.cos(a),n1[0]*math.sin(a),n1[1])]
                if r0==0:pts=pts[1:];normals=normals[1:]
                if r1==0:pts=pts[:3];normals=normals[:3]
                mid=(a+b)/2;P.card(m,mat,pts,(dz*math.cos(mid),dz*math.sin(mid),-dr),normals=normals)
    lathe([(5.35,108.1),(6.1,108.1),(6.4,108.0),(6.52,108.18),(6.42,108.42),(6.05,109.1),(5.5,110.4),(4.9,111.9),(4.05,113.7),(3.2,115.2),(2.3,116.8),(1.4,118.2),(.65,119.2),(.6,120),(0,120)],'cbf_track',(620,615),48)
    lathe([(5.35,108.1),(5.9,108.4),(5.55,109.2),(5.0,110.6),(4.4,112.1),(3.55,113.9),(2.7,115.4),(1.8,117),(1.0,118.2),(.45,119.1),(0,119.1)],'cbf_plastic',(620,615),48)
    m.material_overrides.update({k:'materials/cerroblanco/fitout/'+k+'.vmat' for k in ('cbf_track','cbf_plastic')})
    m.tile_overrides.update({k:24. for k in m.polygons});return m
