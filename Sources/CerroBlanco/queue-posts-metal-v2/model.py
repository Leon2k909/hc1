import math
import numpy as np
import map_kit as K
import riverdale_parts as P
LANES=[[(183+30*k,1108) for k in range(4)]+[(273,1060)],[(183+30*k,1060) for k in range(3)]]
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
                mid=(a+b)/2;P.card(m,mat,pts,(dz*math.cos(mid),dz*math.sin(mid),-dr),normals=normals,uv=[(math.atan2(v[1]-c[1],v[0]-c[0])/math.tau,(v[2])/8) for v in pts])
    for lane in LANES:
        for p in lane:
            lathe([(0,0),(5.85,0),(5.97,.12),(5.97,.30),(0,.30)],'cbf_track',p)
            lathe([(0,.22),(5.72,.22),(5.95,.42),(5.86,.75),(5.45,1.06),(4.2,1.38),(2.2,1.72),(1.35,2.2),(1.25,2.65),(0,2.65)],'queue_metal',p)
            lathe([(0,2.35),(1.35,2.35),(1.35,2.75),(1.1,3.0),(0,3.0)],'queue_metal',p)
            lathe([(0,2.65),(1.1,2.65),(1.1,35.8),(0,35.8)],'queue_shaft',p)
            lathe([(0,35.45),(1.35,35.45),(1.55,35.7),(0,35.7)],'queue_metal',p)
            lathe([(0,35.6),(1.4,35.6),(1.58,35.82),(1.58,38.55),(1.48,38.83),(1.15,39),(0,39)],'cbf_track',p)
        for a,b in zip(lane,lane[1:]):
            a=np.array((*a,37.));b=np.array((*b,37.));d=P.unit(b-a);s=np.cross((0,0,1),d)
            start=a+d*1.5;end=b-d*1.5
            m.oriented_box((start+end)/2,(d,s,(0,0,1)),(np.linalg.norm(end-start),.12,2.),'cbf_belt')
            # Both connector housings intersect the cassette and webbing.
            for c in (a+d*1.35,b-d*1.35):P.bevel_box(m,c,(d,s,(0,0,1)),(.65,.48,2.25),'queue_metal',bevel=.08)
    m.material_overrides.update({k:'materials/cerroblanco/fitout/'+k+'.vmat' for k in ('queue_metal','cbf_track','cbf_belt')})
    m.material_overrides.update({k:'models/props/cerroblanco/queue_posts_metal_v2/'+k+'.vmat' for k in ('queue_metal','queue_shaft')})
    m.tile_overrides.update({k:24. for k in m.polygons});return m
