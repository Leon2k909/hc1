"""Visible civic-hall joinery within the original furniture bounds.

Collision stays in belltower_map. These parts use the already imported original
brown_planks_03 scan and its board-strip UVs; no texture pixels are altered.
"""
import math
import random

import belltower_furniture as F


def peg(model, p, point, normal=(0, -1, 0), radius=.34):
    direction=p.x*normal[0]+p.y*normal[1]+p.z*normal[2]
    tangent=p.x if abs(normal[0])<.9 else p.y
    F.turned(model,p.at(point),direction,tangent,
             [(radius,0),(radius,.08),(radius*.87,.13)],F.DARK,10)


def boards(model,p,length,width,bottom,top,seed=0,end_caps=False):
    """Separate, eased boards, with breadboard ends for the council tables."""
    cap=4.8 if end_caps else 0
    count=max(2,math.ceil(width/6.7))
    step=width/count
    for k in range(count):
        lo=-width/2+k*step+.055
        F.box(model,p,(-length/2+cap,lo,bottom),
              (length/2-cap,lo+step-.11,top),F.WOOD,.14,seed+k)
    if end_caps:
        for side in (-1,1):
            x=side*(length/2-cap/2)
            F.box(model,p,(x-cap/2+.025,-width/2,bottom),
                  (x+cap/2-.025,width/2,top),F.WOOD,.18,seed+31+side)
            for y in (-width*.32,0,width*.32):
                peg(model,p,(x,y,top-.14),(0,0,1),.30)


def trestle(model,p,x,width,height,seed=0):
    """A broad foot, splayed uprights, a bearing rail and pegged joints."""
    foot=width-3.0
    F.box(model,p,(x-2.8,-foot/2,0),(x+2.8,foot/2,2.1),F.DARK,.40,seed)
    for side in (-1,1):
        lower=p.at((x,side*(foot/2-2.6),2.0))
        upper=p.at((x,side*(width*.20),height-3.1))
        F.beam(model,lower,upper,(3.5,3.8),F.WOOD,.24,F.seed_at(p,seed+side+4),up=p.x)
        for sign in (-1,1):
            peg(model,p,(x+sign*1.76,side*width*.20,height-4.7),(sign,0,0),.35)
    F.box(model,p,(x-2.6,-width/2+1.0,height-4.0),
          (x+2.6,width/2-1.0,height-2.0),F.DARK,.23,seed+11)


def bench(model,p,length,width=20,height=18):
    boards(model,p,length,width,height-2.0,height,seed=710)
    positions=(-length/2+8,length/2-8)
    for k,x in enumerate(positions):
        trestle(model,p,x,width,height,720+k*17)
    F.box(model,p,(positions[0]-1.5,-1.25,5.8),
          (positions[1]+1.5,1.25,8.4),F.DARK,.18,755)
    for x in positions:
        for side in (-1,1):
            F.box(model,p,(x+side*2.1-.22,-1.6,5.2),
                  (x+side*2.1+.22,1.6,9.0),F.WOOD,.08,763)


def handle(model,p,x,front,z,span=2.8):
    """Small bronze pull kept inside the authored cabinet/desk footprint."""
    for side in (-1,1):
        F.turned(model,p.at((x+side*span/2,front,z)),-p.y,p.z,
                 [(.58,0),(.58,.12),(.32,.22)],"door_brass",12)
        F.beam(model,p.at((x+side*span/2,front-.12,z)),
               p.at((x+side*span/2,front-.55,z)),(.24,.24),"door_brass",.05)
    F.beam(model,p.at((x-span/2,front-.55,z)),p.at((x+span/2,front-.55,z)),
           (.30,.30),"door_brass",.08)


def table(model,p,length,width,height=30,drawers=False):
    boards(model,p,length,width,height-2.4,height,seed=810,end_caps=True)
    positions=(-length/2+12,length/2-12)
    for k,x in enumerate(positions):
        trestle(model,p,x,width-8,height,840+k*19)
    # Low central stretcher and braces make the bearing structure readable.
    F.box(model,p,(positions[0]-1.8,-2.0,7),(positions[1]+1.8,2.0,10),F.DARK,.23,875)
    for x in positions:
        direction=-1 if x>0 else 1
        F.beam(model,p.at((x,0,10)),p.at((x+direction*min(20,length*.18),0,height-4)),
               (2.5,2.8),F.WOOD,.22,F.seed_at(p,878+direction),up=p.y)
        for side in (-1,1):
            F.bolt(model,p.at((x,side*2.02,8.5)),p.y*side,.38)
    for side in (-1,1):
        y=side*(width/2-3)
        F.box(model,p,(-length/2+6,y-.85,height-7.5),
              (length/2-6,y+.85,height-2.5),F.DARK,.18,895+side)
    if drawers:
        span=(length-14)/3
        front=-width/2+1.1
        for k in range(3):
            x=-1.5*span+(k+.5)*span
            F.box(model,p,(x-span/2+.22,front,height-8),
                  (x+span/2-.22,front+1.4,height-3.0),F.WOOD,.14,900+k)
            handle(model,p,x,front,height-5.5,2.3)


def cabinet(model,p,width,depth,height):
    """A closed civic archive cabinet with framed recessed panels and hardware."""
    half=width/2
    # Carcase: back, side boards, recessed bottom and a moulded cornice.
    F.box(model,p,(-half+.9,depth/2-1.2,2),(half-.9,depth/2,height-2),F.DARK,.12,950)
    for side in (-1,1):
        x=side*(half-1.2)
        F.box(model,p,(x-1.2,-depth/2+1,1.8),(x+1.2,depth/2,height-1.8),F.WOOD,.20,952+side)
    for z0,z1,inset in ((0,2.3,.0),(2.3,4.1,.45),(height-4.3,height-2.5,.45),(height-2.5,height,0)):
        F.box(model,p,(-half+inset,-depth/2+inset,z0),
              (half-inset,depth/2-inset,z1),F.DARK,.18,957+round(z0))
    front=-depth/2+.8
    rail=2.6
    usable=width-5.8
    leaf=usable/2
    z0,z1=4.2,height-4.4
    for side in (-1,1):
        cx=side*(leaf/2+.13)
        left,right=cx-leaf/2+.10,cx+leaf/2-.10
        for x in (left+rail/2,right-rail/2):
            F.box(model,p,(x-rail/2,front,z0),(x+rail/2,front+1.35,z1),F.WOOD,.14,970+side)
        mid=z0+(z1-z0)*.43
        for z in (z0+rail/2,mid,z1-rail/2):
            F.box(model,p,(left+rail,front,z-rail/2),
                  (right-rail,front+1.35,z+rail/2),F.WOOD,.13,976+round(z))
        for low,high in ((z0+rail+.18,mid-rail/2-.18),(mid+rail/2+.18,z1-rail-.18)):
            # Recessed panel, then a narrow raised bead inside each frame.
            F.box(model,p,(left+rail+.10,front+.64,low),
                  (right-rail-.10,front+1.6,high),F.DARK,.14,985+round(low))
            for x in (left+rail+.30,right-rail-.30):
                F.box(model,p,(x-.20,front+.30,low),(x+.20,front+.78,high),F.WOOD,.10,991)
            for z in (low+.20,high-.20):
                F.box(model,p,(left+rail+.30,front+.30,z-.20),
                      (right-rail-.30,front+.78,z+.20),F.WOOD,.10,992)
        handle(model,p,-side*2.6,front,mid+5,1.5)
        for z in (z0+8,z1-8):
            x=left+.85 if side<0 else right-.85
            F.box(model,p,(x-.48,front-.18,z-2.4),(x+.48,front+.14,z+2.4),"door_brass",.08,999)
            for dz in (-1.65,1.65):
                F.bolt(model,p.at((x,front-.20,z+dz)),-p.y,.16,False)


def wall_rail(model,p,length):
    F.box(model,p,(-length/2,0,0),(length/2,1.0,2.7),F.DARK,.20,1020)
    F.box(model,p,(-length/2,.15,2.7),(length/2,1.25,3.3),F.WOOD,.16,1021)


def deck(model,p,e0,e1,n0,n1,z,holes=(),underside=False):
    """Staggered oak boards with shallow eased joints, clipped around stairwells.

    The visible face stays exactly on the original floor/ceiling plane. All of
    the board thickness lies inside the existing slab; no collision is added.
    """
    count=math.ceil((e1-e0)/7.4)
    width=(e1-e0)/count
    seed=1220 if underside else 1110

    def subtract(rect,hole):
        a,b,c,d=rect
        l,r=max(a,hole[0]),min(b,hole[1])
        low,high=max(c,hole[2]),min(d,hole[3])
        if l>=r or low>=high:
            return [rect]
        return [v for v in ((a,l,c,d),(r,b,c,d),(l,r,c,low),(l,r,high,d))
                if v[1]-v[0]>.2 and v[3]-v[2]>.2]

    for row in range(count):
        rng=random.Random(seed+row*37)
        a,b=e0+row*width,e0+(row+1)*width
        start=n0-rng.uniform(0,100)
        joint=0
        while start<n1:
            end=min(n1,start+rng.uniform(88,136))
            parts=[(a,b,max(n0,start),end)]
            for hole in holes:
                parts=[piece for part in parts for piece in subtract(part,hole)]
            for left,right,near,far in parts:
                if right-left<=.2 or far-near<=.2:
                    continue
                lo=z if underside else z-1.0
                hi=z+1.0 if underside else z
                F.box(model,p,(left+.045,near+.045,lo),(right-.045,far-.045,hi),
                      F.WOOD,.065,seed+row*23+joint*101)
            start=end
            joint+=1
