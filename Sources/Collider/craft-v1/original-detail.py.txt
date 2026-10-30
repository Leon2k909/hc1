"""Fabricated steel stairs, guardrails and transport cases for Collider.

Plan axes match map_kit. Collision is authored separately from small hardware;
stairs use a thin inclined deck, so the space under the high end is accessible.
"""
import math
import numpy as np
import map_kit as K
import boxyard_map as B
import ares_map as A
from belltower_furniture import bevel_box, beam

UP=np.array((0.,0.,1.))
AXES=np.eye(3)


def plate(m,lo,hi,paint="co_trim",bevel=.25):
    lo,hi=np.minimum(lo,hi),np.maximum(lo,hi)
    bevel_box(m,(lo+hi)/2,AXES,hi-lo,paint,bevel)


def bolt(m,at,axis,r=.65,length=.45,paint="co_silver"):
    B.lathe(m,at,axis,[(r,0),(r,length)],paint,sides=6,cap=paint)


def rail(m,a,b,z,lamps=False,collide=True):
    # Preserve the established shoot-through top/kick collision envelopes.
    if collide:
        clip=K.Model();A.railing(clip,a,b,z,lamps=False,collide=True)
        m.boxes.extend(clip.boxes);m.hulls.extend(clip.hulls)
    a=np.array((*a,z),float);b=np.array((*b,z),float)
    length=np.linalg.norm(b-a)
    if length<4:return
    along=(b-a)/length;side=np.cross(UP,along)
    beam(m,a+UP*41,b+UP*41,(3.2,3.0),"co_case",bevel=.4)
    beam(m,a+UP*22,b+UP*22,(1.6,1.6),"co_trim",bevel=.2)
    beam(m,a+UP*3,b+UP*3,(.8,6),"co_steel",bevel=.12)
    posts=max(2,int(round(length/60))+1)
    for i in range(posts):
        p=a+(b-a)*i/(posts-1)
        bevel_box(m,p+UP*20.5,(along,side,UP),(2.6,2.6,41),"co_trim",.3)
        bevel_box(m,p+UP*.5,(along,side,UP),(7,6,1),"co_silver",.2)
        bevel_box(m,p+UP*36.5,(along,side,UP),(3.4,3.4,1.4),"co_silver",.2)
        for aa in (-2.3,2.3):
            for ss in (-1.8,1.8):bolt(m,p+along*aa+side*ss+UP*1.05,UP,r=.48,length=.4)
        if lamps and i%3==1:
            bevel_box(m,p+side*1.5+UP*31,(along,side,UP),(1.4,.8,3),"co_white",.1)


def slope_rail(m,a,b):
    a,b=np.asarray(a,float),np.asarray(b,float)
    beam(m,a+UP*38,b+UP*38,(3.2,3),"co_case",bevel=.4)
    beam(m,a+UP*20,b+UP*20,(1.6,1.6),"co_trim",bevel=.2)
    length=np.linalg.norm((b-a)[:2]);posts=max(2,round(length/60)+1)
    direction=K.normalise((b-a)*np.array((1,1,0)));side=np.cross(UP,direction)
    for i in range(posts):
        p=a+(b-a)*i/(posts-1)
        plate(m,p+(-1.3,-1.3,-2),p+(1.3,1.3,38),"co_trim",.3)
        bevel_box(m,p+UP*3,(direction,side,UP),(6,1.5,10),"co_silver",.2)
        for dz in (0,6):bolt(m,p+UP*dz+side*.8,side,r=.7,length=.5)
    m.beam(a+UP*40,b+UP*40,(3,10),None,"metal")


def stair(m,axis,c0,c1,s0,s1,z0,z1):
    count=max(1,round((z1-z0)/7.4));rise=(z1-z0)/count;run=(s1-s0)/count
    sign=1 if run>0 else -1
    def p(c,s,z):return np.array((s,c,z) if axis=="e" else (c,s,z),float)
    for i in range(count):
        sa,sb=s0+run*i,s0+run*(i+1);top=z0+rise*(i+1)
        # Galvanized tread pan and a narrow unstriped safety nosing.
        lo,hi=p(c0,min(sa,sb),top-2),p(c1,max(sa,sb),top)
        m.box(lo,hi,{"+z":"co_grating","default":"co_trim"})
        a,b=p(c0,sa,top-.7),p(c1,sa,top-.7)
        beam(m,a,b,(2.4,2.1),"co_silver",bevel=.2)
        lo,hi=p(c0+7,sa+sign*.1,top+.02),p(c1-7,sa+sign*.8,top+.12)
        m.box(np.minimum(lo,hi),np.maximum(lo,hi),"co_amber")
        for c in (c0+5,c1-5):bolt(m,p(c,(sa+sb)/2,top+.05),UP,r=.6,length=.5)
    # The collision deck is thin and agrees with the visible inclined soffit.
    vertices=[p(c,s,z) for c in (c0,c1) for s,z in
              ((s0,z0-10),(s1,z1-14),(s1,z1),(s0,z0+rise*.5))]
    m.hull(vertices,"metal")
    B.card(m,"co_steel",[p(c0,s0,z0-10),p(c1,s0,z0-10),p(c1,s1,z1-14),p(c0,s1,z1-14)],(0,0,-1))
    for c in (c0+2,c1-2):
        beam(m,p(c,s0,z0+1),p(c,s1,z1-4),(3.6,13),"co_trim",bevel=.6)
        beam(m,p(c,s0,z0+7),p(c,s1,z1+2),(5,1.5),"co_silver",bevel=.2)
        slope_rail(m,p(c,s0,z0+rise),p(c,s1,z1))
        # Two slender posts and foot plates carry the raised end.
        for t in (.55,.94):
            s=s0+(s1-s0)*t;top=z0+(z1-z0)*t-10
            m.box(p(c-2,s-2,z0),p(c+2,s+2,top),None,"metal")
            plate(m,p(c-2,s-2,z0),p(c+2,s+2,top),"co_trim",.4)
            plate(m,p(c-6,s-6,z0),p(c+6,s+6,z0+1.2),"co_silver",.2)


def hardcase(m,e,n,z,w,d,h,heading,label):
    f=B.Frame(e,n,heading,z)
    axes=(f.x,f.y,UP)
    def part(x0,x1,y0,y1,z0,z1,paint="co_trim",bevel=.4):
        bevel_box(m,f.p((x0+x1)/2,(y0+y1)/2,(z0+z1)/2),axes,(x1-x0,y1-y0,z1-z0),paint,bevel)
    f.box(m,-w/2,w/2,-d/2,d/2,3,h,None,surface="plastic")
    # Separate molded body, rubber seal and lid, with broad radiused edges.
    part(-w/2,w/2,-d/2,d/2,3,h-11,"co_case",3.8)
    part(-w/2+.5,w/2-.5,-d/2+.5,d/2-.5,h-11.3,h-9.5,"co_rubber",.6)
    part(-w/2,w/2,-d/2,d/2,h-9.5,h,"co_case",3.2)
    # Corner bumpers, wrap-around pressed plates and their recessed bolts.
    for x in (-w/2+4,w/2-4):
        for y in (-d/2+3,d/2-3):
            part(x-4,x+4,y-3,y+3,0,8,"co_rubber",1)
            part(x-3.2,x+3.2,y-3.5,y+3.5,h-7,h+1.5,"co_trim",.8)
            part(x-2.5,x+2.5,y-3.5,y+3.5,8,h-13,"co_trim",.5)
    # Reinforced lid ribs and stack-registration pads.
    for x in (-w*.32,0,w*.32):part(x-2,x+2,-d/2+5,d/2-5,h-.3,h+1.3,"co_trim",.5)
    for sy in (-1,1):
        y=sy*d/2
        for x in (-w*.32,w*.32):
            part(x-4.2,x+4.2,y-1.2,y+1.2,h-21,h-6,"co_silver",.65)
            part(x-2.2,x+2.2,y-1.9,y+1.9,h-18,h-9,"co_trim",.45)
            part(x-3,x+3,y-2.2,y+2.2,h-20,h-18,"co_amber",.3)
            bolt(m,f.p(x,y+sy*2,h-8),f.y*sy,r=.65,length=.45)
        for x in (-w*.39,w*.39):
            part(x-1.6,x+1.6,y-.8,y+.8,10,h-24,"co_trim",.5)
        # Deep handle well, hinge ears and a bowed grip along the long face.
        part(-14,14,y-.6,y+.6,h*.35,h*.35+13,"co_rubber",1)
        for x in (-11,11):part(x-2,x+2,y-1.4,y+1.4,h*.35+2,h*.35+11,"co_silver",.5)
        part(-11,11,y-2.5,y+2.5,h*.35+3,h*.35+6,"co_trim",.8)
        for x in (-w/2+4,w/2-4):
            for zz in (11,h-16):bolt(m,f.p(x,y+sy*.7,zz),f.y*sy,r=.7,length=.5)
        label(m,"case",f.p(-w*.22,y+sy*1.3,19),f.y[:2]*sy,w*.26,9)
    for sx in (-1,1):
        x=sx*w/2
        part(x-.7,x+.7,-12,12,h*.37,h*.37+14,"co_rubber",.9)
        for yy in (-10,10):part(x-1.6,x+1.6,yy-1.7,yy+1.7,h*.37+2,h*.37+12,"co_silver",.4)
        part(x-2.4,x+2.4,-10,10,h*.37+3,h*.37+6,"co_trim",.6)
