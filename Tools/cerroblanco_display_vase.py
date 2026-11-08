"""Approved turned display vase; rolled mouth and continuous hollow wall."""
import math
import numpy as np
from scipy.interpolate import PchipInterpolator
import map_kit as K
import riverdale_parts as P

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

def build_into(model,e,n,z):
    local=build()
    for mat,rows in local.polygons.items():
        for i,(points,normal) in enumerate(rows):rows[i]=([p+np.array((e,n,z)) for p in points],normal)
    model.extend(local)
