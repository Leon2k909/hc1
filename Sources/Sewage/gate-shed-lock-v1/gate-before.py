"""Arched, locked maintenance gates at the two existing closed tunnel ends."""
import math
import numpy as np
import map_kit as K
from sewage_warning_sign import rod

PLACEMENTS=[(-1000,-1500,-230),(1000,1500,80)]
MATERIALS={
 'ww_gate_body':'materials/sewage/pipe-texture-v1/pipe.vmat',
 'ww_gate_hardware':'materials/sewage/crane-blocks-v1/steel.vmat',
 'ww_gate_recess':'materials/sewage/crane-blocks-v1/dark.vmat',
 'ww_gate_lock':'materials/sewage/crane-blocks-v1/paint.vmat',
}


def original_end(m,e0,e1,ncenter):
    # Frozen original render geometry; used for an exact, guarded splice.
    import sewage_map as R
    m.box((e1-10,ncenter-115,-10),(e1+10,ncenter+115,170),'concrete','default')
    for n in np.arange(ncenter-103,ncenter+115,15):
        R.tube(m,(e1-12,n,0),(e1-12,n,150),2,'steel',8)
    return m


def arch(m,r0,r1,d0,d1,paint,segments=40):
    for i in range(segments):
        a=math.pi*i/segments;b=math.pi*(i+1)/segments
        def p(d,r,t):return np.array((d,r*math.cos(t),48+r*math.sin(t)))
        near=[p(d0,r0,a),p(d0,r0,b),p(d0,r1,b),p(d0,r1,a)]
        far=[p(d1,r0,a),p(d1,r0,b),p(d1,r1,b),p(d1,r1,a)]
        m.polygon(paint,near);m.polygon(paint,list(reversed(far)))
        m.polygon(paint,[near[0],far[0],far[1],near[1]])
        m.polygon(paint,[near[3],near[2],far[2],far[3]])


def local_gate():
    m=K.Model();m.material_overrides.update(MATERIALS)
    m.tile_overrides.update({p:48 for p in MATERIALS})
    body='ww_gate_body';metal='ww_gate_hardware';dark='ww_gate_recess'
    # An opaque recessed end keeps the closed branch sealed, with real depth behind the bars.
    m.box((27,-115,-10),(30,115,170),dark)
    for q in (-115,112):m.box((1,q,-10),(28,q+3,170),dark)
    m.box((1,-115,-10),(28,115,0),dark)
    m.box((1,-115,163),(28,115,170),dark)
    # Outer cast jambs and arched head frame follow the existing 115-inch tunnel radius.
    for q in (-114,106):m.box((-2,q,0),(4,q+8,48),body)
    arch(m,106,114,-2,4,body)
    arch(m,107,113,-2.7,-2,metal)
    m.box((-2,-114,0),(4,114,3),body)
    # Two independently framed leaves, reinforced below the open grille.
    for low,high in ((-102,-1.4),(1.4,102)):
        m.box((0,low,4),(1.2,high,26),body)
        for q0,q1 in ((low,low+3),(high-3,high)):
            top=48+math.sqrt(max(0,104**2-max(abs(q0),abs(q1))**2))-1
            m.box((-.7,q0,3),(2.6,q1,top),body)
        for z in (4,26,65):m.box((-.9,low,z),(2.8,high,z+3),body)
        for q in np.arange(low+6,high-4,4.5):
            top=48+math.sqrt(max(0,101**2-q*q))-.4
            m.box((-.1,q,28),(1.45,q+1.05,top),body)
        for q in np.linspace(low+10,high-10,4):
            m.box((-1.05,q-.8,7),(-.05,q+.8,23),metal)
        # Welded diagonal flat strap braces each half below the latch rail.
        bottom,top=(low+4,high-4) if high<0 else (high-4,low+4)
        m.beam((-.6,bottom,31),(-.6,top,62),(1.1,2.2),body,up=(1,0,0))
    arch(m,100.5,104,-.7,2.6,body)
    # Three segmented barrel hinges per leaf, supported by welded straps.
    for side in (-1,1):
        q=side*106
        for z in (12,31,49):
            m.box((-1.4,min(side*99,side*112),z-2),(1.7,max(side*99,side*112),z+2),metal)
            for dz,length,paint in ((-3.7,2.8,body),(0,3.8,metal),(3.7,2.8,body)):
                rod(m,(-2.3,q,z+dz-length/2),(-2.3,q,z+dz+length/2),1.65,paint,16)
            rod(m,(-2.3,q,z-5.5),(-2.3,q,z+5.5),.55,metal,12)
    # Frame anchors have actual hex heads and broad washers.
    anchors=[(q,z) for q in (-110,110) for z in (10,34)]
    anchors += [(110*math.cos(t),48+110*math.sin(t)) for t in np.linspace(.22,math.pi-.22,9)]
    for q,z in anchors:
        rod(m,(-2.7,q,z),(-3.1,q,z),1.5,dark,20)
        rod(m,(-3.1,q,z),(-3.8,q,z),1.08,metal,6)
    # Central slide bolt, hasp and brass padlock visibly secure the closed leaves.
    for q in (-8,8):m.box((-2.4,q-3,58),(-1,q+3,69),metal)
    rod(m,(-3,-13,64),(-3,14,64),.7,metal,12)
    rod(m,(-3,-10,64),(-6,-10,68),.7,metal,12)
    m.box((-5.2,-1.4,56),(-2.5,1.4,65),body)
    for q in (-2.1,2.1):rod(m,(-5.8,q,60),(-5.8,q,65),.42,metal,10)
    curve=[(-5.8,2.1*math.cos(t),65+2.1*math.sin(t)) for t in np.linspace(0,math.pi,13)]
    for a,b in zip(curve,curve[1:]):rod(m,a,b,.42,metal,10)
    m.box((-7,-3.2,55),(-4.8,3.2,61.5),'ww_gate_lock')
    rod(m,(-7.1,0,58),(-7.3,0,58),.6,dark,12)
    return m


def emit(m,e0,e1,ncenter):
    direction=1 if e1>e0 else -1
    front=e1-direction*14
    local=local_gate()
    for paint,faces in local.polygons.items():
        for index,(pts,normal) in enumerate(faces):
            transformed=[np.array((front+direction*p[0],ncenter+p[1],p[2])) for p in pts]
            ns=local.polygon_normals.get((paint,index))
            ns=None if ns is None else [np.array((direction*n[0],n[1],n[2])) for n in ns]
            if direction<0:
                transformed.reverse()
                if ns is not None:ns.reverse()
            m.polygon(paint,transformed,normal=(direction*normal[0],normal[1],normal[2]),normals=ns)
    m.material_overrides.update(local.material_overrides);m.tile_overrides.update(local.tile_overrides)
    return m
