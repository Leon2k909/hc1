"""Approved Lucky Stop checkout counter, retaining the original wood box collision."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT="materials/riverside/counter-v1"
X=np.array((1.,0,0));Y=np.array((0.,-1,0));Z=np.array((0.,0,1.))
def p(x,d,z):return X*x+Y*d+Z*z
def model(lod=0):
    m=K.Model();sides=(20,12,8)[lod]
    def box(c,sz,paint,b=.08):G.bevel_box(m,p(*c),(X,Y,Z),sz,paint,bevel=b if lod<2 else min(b,.025))
    def cyl(c,axis,length,r,paint):G.lathe_axis(m,p(*c),axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides=sides)
    # Original outer footprint and 40-inch top: the installed register stays seated at exactly the same height.
    box((0,-.7,2.3),(106,24.2,4.6),'trim',.15)
    box((0,-.4,20.5),(106,26.2,33.6),'wood',.16)
    box((0,0,38.8),(110,30,2.0),'trim',.22)
    box((0,0,39.76),(109.5,29.5,.48),{'default':'trim','+z':'laminate'},.12)
    # Front recessed oak panels, rails and stiles. Their physical offsets catch the existing store lighting.
    for x in (-34.,0.,34.):
        box((x,12.82,21.4),(31.3,.12,25.3),'recess',.08)
        box((x,12.96,21.4),(30.4,.18,24.4),'wood',.12)
    for x in (-52.,-17.,17.,52.):box((x,13.28,21.0),(1.5,1.15,31.9),'wood',.11)
    for z in (5.6,36.2):box((0,13.18,z),(105.4,.95,1.7),'wood',.10)
    # The operator side has four separate storage doors, narrow reveal lines, hinges and pulls.
    for x in (-39.,-13.,13.,39.):
        box((x,-13.66,20.8),(25.5,.18,30.4),'recess',.07)
        box((x,-13.83,20.8),(24.6,.40,29.5),'wood',.14)
        if lod<2:
            for z in (29.,32.5):cyl((x+7.6,-14.06,z),-Y,.57,.18,'steel')
            G.tube(m,[p(x+7.6,-14.63,29),p(x+7.6,-14.63,32.5)],.18,'steel',sides=sides)
            for z in (11.,30.):
                box((x-11.9,-14.08,z),(.76,.13,1.82),'steel',.06)
                cyl((x-12.15,-14.15,z-.7),Z,1.4,.14,'steel')
        else:box((x+7.6,-14.25,30.75),(.25,.28,3.7),'steel',.04)
    # End panel reveals and a lower skirt: no paper-thin open bottom.
    for x in (-53.07,53.07):
        box((x,-.4,21.0),(.14,22.6,28.0),'recess',.10)
        box((x+(-.10 if x<0 else .10),-.4,21.0),(.16,21.9,27.3),'wood',.10)
    # Tubular steel foot rail sits inside the old collision footprint.
    if lod<2:
        path=[p(-49,12.0,8)]
        path += [p(-46.6-2.4*math.cos(t),12.0+2.4*math.sin(t),8) for t in np.linspace(0,math.pi/2,5)[1:]]
        path += [p(46.6,14.4,8)]
        path += [p(46.6+2.4*math.sin(t),12.0+2.4*math.cos(t),8) for t in np.linspace(0,math.pi/2,5)[1:]]
        G.tube(m,path,.52,'steel',sides=sides)
    else:G.tube(m,[p(-48,14.4,8),p(48,14.4,8)],.52,'steel',sides=sides)
    for x in (-37.,0.,37.):
        cyl((x,12.85,8),Y,.24,1.02,'steel')
        cyl((x,12.99,8),Y,1.0,.29,'steel')
        if lod==0:
            for z in (7.36,8.64):cyl((x,13.12,z),Y,.055,.105,'trim')
    if lod==0:
        # Small edge losses expose the chipboard core without covering every edge in rust.
        for x,length,z in [(-41.,1.8,39.03),(19.,1.15,39.34),(44.,.65,38.7)]:
            box((x,15.005,z),(length,.03,.10),'core',.015)
    for paint,polys in m.polygons.items():
        for index,(points,normal) in enumerate(polys):
            uv=[]
            for q in points:
                x,d,z=q[0],-q[1],q[2]
                if paint=='laminate':u=(x+55)/110;v=(d+15)/30
                elif abs(normal[2])>.6:u=x/30;v=d/24
                elif abs(normal[0])>.7:u=d/24;v=z/36
                else:u=x/30;v=z/36
                uv.append((float(u),float(v)))
            m.polygon_uvs[(paint,index)]=uv
    m.material_overrides={paint:MAT+'/'+paint+'.vmat' for paint in m.polygons}
    m.tile_overrides={paint:36 for paint in m.polygons}
    return m
def append_to(target,position):
    m=model(0);offset=np.asarray(position,float)
    for paint,faces in m.polygons.items():
        alias="ctrv1_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
    target.oriented_box(offset+np.array((0.,0.,20.)),(X,np.array((0.,1.,0.)),Z),(110,30,40),{"default":None},"wood")
