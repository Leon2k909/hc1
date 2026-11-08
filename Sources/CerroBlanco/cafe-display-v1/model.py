import math
import numpy as np
import map_kit as K
import riverdale_parts as P
AX=((1,0,0),(0,1,0),(0,0,1))
def build():
    m=K.Model()
    P.bevel_box(m,(655,615,42.75),AX,(54,22,1.5),'cbf_track',bevel=.24)
    P.bevel_box(m,(655,615,43.48),AX,(52.5,20.5,.20),'cb_steel',bevel=.06)
    P.bevel_box(m,(655,615,43.57),AX,(51.8,19.8,.08),'cb_black',bevel=.025)
    profile=[(604.,43.5),(604.,48.)]+[(612-8*math.cos(t),48+8*math.sin(t)) for t in np.linspace(0,math.pi/2,25)[1:]]+[(626.,56.)]
    # Shared curved glazing rings, with smooth geometric normals.
    for i,((n0,z0),(n1,z1)) in enumerate(zip(profile,profile[1:])):
        dn,dz=n1-n0,z1-z0
        toward=np.array((0,-dz,dn));normal=[]
        for j in (i,i+1):
            a=np.array(profile[max(j-1,0)]);b=np.array(profile[min(j+1,len(profile)-1)]);v=b-a
            normal.append(P.unit((0,-v[1],v[0])))
        P.card(m,'cb_glass',[(628,n0,z0),(682,n0,z0),(682,n1,z1),(628,n1,z1)],toward,normals=[normal[0],normal[0],normal[1],normal[1]])
    # Glazed ends sit inside continuous swept frame tubes.
    for e,sign in ((628,-1),(682,1)):
        points=[(e,n,z) for n,z in profile]+[(e,626,43.5)]
        P.card(m,'cb_glass',points,(sign,0,0))
        path=[np.array(p) for p in points]+[np.array(points[0])]
        rings=[];normals=[]
        for i,c in enumerate(path[:-1]):
            tangent=P.unit(path[(i+1)%(len(path)-1)]-path[(i-1)%(len(path)-1)])
            across=np.cross(tangent,(1,0,0));dirs=[np.array((1,0,0))*math.cos(a)+across*math.sin(a) for a in np.linspace(0,math.tau,12,endpoint=False)]
            rings.append([c+d*.18 for d in dirs]);normals.append(dirs)
        for i in range(len(rings)):
            j=(i+1)%len(rings)
            for a in range(12):
                b=(a+1)%12;ns=[normals[i][a],normals[i][b],normals[j][b],normals[j][a]]
                P.card(m,'cb_steel',[rings[i][a],rings[i][b],rings[j][b],rings[j][a]],sum(ns),normals=ns)
    # Formed rear tracks and two overlapping glazed access sashes.
    for z in (43.7,55.8):P.bevel_box(m,(655,626,z),AX,(53.8,.6,.4),'cb_steel',bevel=.08)
    for e0,e1,n in ((628.3,655.6,625.9),(654.4,681.7,626.15)):
        P.card(m,'cb_glass',[(e0,n,43.9),(e1,n,43.9),(e1,n,55.6),(e0,n,55.6)],(0,1,0))
        for e in (e0,e1):P.rod(m,(e,n,43.9),(e,n,55.6),.10,'cb_steel',12,True)
        e=e1-2 if e0<650 else e0+2
        P.rod(m,(e,n,48.8),(e,n+.65,48.8),.12,'cb_steel',12,True)
        P.rod(m,(e,n+.65,48.8),(e,n+.65,51.2),.12,'cb_steel',12,True)
        P.rod(m,(e,n+.65,51.2),(e,n,51.2),.12,'cb_steel',12,True)
    m.material_overrides.update({'cb_glass':'materials/cerroblanco/cb_glass.vmat','cb_steel':'materials/cerroblanco/quality-v1/cb_steel.vmat','cb_black':'materials/cerroblanco/cb_black.vmat','cbf_track':'materials/cerroblanco/fitout/cbf_track.vmat'})
    m.tile_overrides.update({name:24. for name in m.polygons});return m
