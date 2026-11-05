"""Approved Boxyard RTG crane geometry; instance models share these LOD inputs."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT='materials/boxyard/gantry_crane_v1'
X=np.array((1.,0,0));Y=np.array((0.,1.,0));Z=np.array((0.,0.,1.))
def model(lod=0,paint='yellow'):
    m=K.Model();n=(24,16,8)[lod]
    def box(c,size,p=paint,b=.5,axes=(X,Y,Z)):
        if lod<2 and b:G.bevel_box(m,np.asarray(c,float),axes,size,p,bevel=b)
        else:m.oriented_box(np.asarray(c,float),axes,size,p)
    def rod(a,b,r,p='steel',sides=None):G.tube(m,[np.asarray(a,float),np.asarray(b,float)],r,p,sides=sides or (8,6,4)[lod])
    def cyl(c,axis,r,h,p='steel',sides=None):G.lathe_axis(m,np.asarray(c,float),np.asarray(axis,float),[(0.,0.),(float(r),0.),(float(r),float(h)),(0.,float(h))],p,sides=sides or n)
    def beam(a,b,w,h,p=paint):
        a,b=np.array(a,float),np.array(b,float);axis=b-a;length=np.linalg.norm(axis);axis/=length
        side=np.cross(axis,Z if abs(axis[2])<.9 else Y);side/=np.linalg.norm(side);up=np.cross(axis,side)
        box((a+b)/2,(length,w,h),p,.45,(axis,side,up))
    def plate(pts,out,p=paint,uv=None):G._face(m,p,[np.array(q,float) for q in pts],towards=np.array(out,float),uv=uv)
    def label(c,right,up,w,h,region):
        c=np.array(c,float);right=np.array(right)*w/2;up=np.array(up)*h/2
        lo,hi=(.5,1) if region=='badge' else (0,.5)
        plate([c-right-up,c+right-up,c+right+up,c-right+up],np.cross(right,up),'markings',[(0,lo),(1,lo),(1,hi),(0,hi)])
    # Four articulated bogies replace the original rectangular rubber blocks.
    for sx in (-1,1):
        for sy in (-1,1):
            cx,cy=sx*140,sy*462
            box((cx,cy,34),(92,27,17),'steel',2)
            cyl((cx,cy,43),Z,11,12,'steel');box((cx,cy,56),(45,34,8),paint,1)
            for ax in (-27,27):
                rod((cx+ax,cy-24,22),(cx+ax,cy+24,22),3,'steel')
                for side in (-1,1):
                    at=np.array((cx+ax,cy+side*20,22),float)
                    G.lathe_axis(m,at,Y,np.array([(11,-6),(16,-6.8),(20,-5.6),(22,-3.7),(22,3.7),(20,5.6),(16,6.8),(11,6),(11,-6)],float),'rubber',sides=n)
                    cyl(at+Y*side*6.1,Y*side,11,1.1,'steel');cyl(at+Y*side*7.2,Y*side,4,2,paint)
                    if lod<2:
                        for angle in np.linspace(0,math.tau,8,endpoint=False):cyl(at+Y*side*7.3+np.array((7*math.cos(angle),0,7*math.sin(angle))),Y*side,.8,.5,'steel',6)
                    if lod==0:
                        for angle in np.linspace(0,math.tau,32,endpoint=False):
                            radial=np.array((math.cos(angle),0,math.sin(angle)));tangent=np.cross(Y,radial)
                            box(at+radial*21.9,(1.2,8.2,.35),'rubber',0,(tangent,Y,radial))
            for side in (-1,1):box((cx,cy+side*15,37),(85,2,6),paint,.8)
            label((cx,cy+sy*16.1,37),X,Z,76,5,'stripe')
    # Braced tapered portals with real cap plates, stiffeners and lower cross-girders.
    for sy in (-1,1):
        yy=sy*462
        box((0,yy,62),(365,34,24),paint,2)
        for sx in (-1,1):
            base=np.array((sx*140,yy,68));top=np.array((sx*128,yy,710))
            beam(base,top,25,29)
            box((sx*140,yy,72),(40,46,3),'steel',.6)
            box((sx*128,yy,709),(44,48,4),'steel',.6)
            for zz in (90,340,670):
                box((sx*(140-12*(zz-68)/642),yy,zz),(28,32,5),paint,.4)
            # Long flange strips and gusset knees create scale rather than surface noise.
            for dx in (-12.8,12.8):beam(base+X*dx,top+X*dx,3,31)
            beam((sx*140,yy,570),(sx*68,yy,712),12,12)
        box((0,yy,733),(348,38,46),paint,2)
        if lod<2:
            for sx in (-1,1):
                plate([(sx*140,yy-17,677),(sx*140,yy-17,710),(sx*80,yy-17,710)],-Y,paint)
                for zz in (100,650):
                    for dx in (-8,8):cyl((sx*140+dx,yy-18,zz),-Y,1,1,'steel',6)
    # Twin bridge girders, inset panel joints and top-mounted trolley running rails.
    for sx in (-1,1):
        xx=sx*128
        box((xx,0,748),(33,1000,54),paint,1.8)
        for zz in (722,774):box((xx,0,zz),(43,1002,3),'steel',.35)
        box((xx,0,779),(4,1000,7),'steel',.3)
        if lod<2:
            for yy in np.arange(-438,450,88):box((xx+sx*17.2,float(yy),748),(1.4,2,48),paint,.2)
        label((xx+sx*17.9,0,750),Y*sx,Z,128,22,'badge')
    for yy in (-462,462):box((0,yy,775),(244,12,8),'steel',.5)
    # Maintenance catwalk with open handrails, kick plates and a real access ladder.
    walkx=-162
    box((walkx,0,774),(31,980,3),'steel',.35)
    for yy in np.linspace(-480,480,(17,13,9)[lod]):
        rod((walkx-15,yy,776),(walkx-15,yy,816),.9)
    for zz in (797,816):rod((walkx-15,-488,zz),(walkx-15,488,zz),.9)
    box((walkx-15,0,779),(1.2,980,6),paint,.2)
    for yy in (-488,488):
        rod((walkx-15,yy,816),(walkx+15,yy,816),.9)
        rod((walkx+15,yy,776),(walkx+15,yy,816),.9)
    # Ladder lives on the outside of one portal. Cage hoops project clear of its rungs.
    lx,ly=-145,-488
    for dx in (-10,10):rod((lx+dx,ly,68),(lx+dx,ly,816),1.1)
    for zz in np.arange(80,812,(12,18,30)[lod]):rod((lx-10,ly,float(zz)),(lx+10,ly,float(zz)),.75)
    for zz in np.arange(150,800,96):
        G.torus(m,(lx,ly-3,float(zz)),Z,18,.75,'steel',seg=(20,14,8)[lod],sides=5,a0=math.pi,a1=math.tau)
    if lod<2:
        for angle in np.linspace(math.pi,math.tau,5):rod((lx+18*math.cos(angle),ly-3+18*math.sin(angle),150),(lx+18*math.cos(angle),ly-3+18*math.sin(angle),726),.6)
    # Hoist trolley: cross carriage, winch drums, motor and service house.
    box((0,-30,789),(260,140,18),'steel',1.2)
    for xx in (-128,128):
        for yy in (-80,20):cyl((xx-3,yy,785),X,7,6,'steel',n)
    for xx in (-65,65):
        cyl((xx-18,-30,810),X,16,36,'steel',n)
        for cap in (-20,20):cyl((xx+cap,-30,810),X,20,2,paint,n)
        if lod<2:
            for offset in np.arange(-15,16,3):G.torus(m,(xx+offset,-30,810),X,16,.55,'cable',seg=n,sides=4)
    box((0,53,804),(100,31,33),'white',2)
    if lod<2:
        for xx in np.arange(-38,40,8):box((xx,69,805),(3,.3,21),'cable',0)
    # Suspended operator cab: individual frame members surround inset glazing.
    # Every panel has an actual window opening; glass is not pasted over a solid box.
    cabx,caby=-34,-18
    box((cabx,caby,600),(78,74,8),'white',2)
    box((cabx,caby,683),(82,78,6),'white',2)
    for dx in (-36,36):
        for dy in (-34,34):box((cabx+dx,caby+dy,642),(4,4,80),'white',.6)
    for zz in (617,670):
        for side in (-1,1):
            box((cabx,caby+side*34,zz),(70,3,3),'white',.4)
            box((cabx+side*36,caby,zz),(3,66,3),'white',.4)
    for side in (-1,1):
        box((cabx,caby+side*34,609),(70,3,12),'white',.4)
        plate([(cabx-34,caby+side*33,619),(cabx+34,caby+side*33,619),(cabx+34,caby+side*33,669),(cabx-34,caby+side*33,669)],Y*side,'glass')
        plate([(cabx+side*35,caby-32,619),(cabx+side*35,caby+32,619),(cabx+side*35,caby+32,669),(cabx+side*35,caby-32,669)],X*side,'glass')
        box((cabx+side*36,caby,609),(3,66,12),'white',.4)
    for xx in (cabx-26,cabx+26):beam((xx,caby,687),(xx,-30,780),5,5,'steel')
    rod((cabx-20,caby-36,630),(cabx+16,caby-36,649),.55,'steel')
    box((cabx,caby-37,675),(84,7,3),'white',.5)
    # Four-part reeving and a recognisable telescopic ISO container spreader.
    for xx in (-75,75):
        for yy in (-36,4):rod((xx,yy,787),(xx,yy,337),.9,'cable',6 if lod<2 else 4)
    box((0,-16,333),(190,36,14),'steel',1.5)
    for xx in (-113,113):
        box((xx,-16,328),(60,26,12),paint,1)
        box((xx,-16,315),(16,100,15),paint,1)
        for yy in (-60,28):
            box((xx,yy,304),(19,18,10),'steel',.7)
            cyl((xx,yy,299),Z,3,6,'steel',8)
        label((xx,-67.1,316),X,Z,14,12,'stripe')
    # Long-scale floodlight housings and corner beacons; no new light components.
    for sy in (-1,1):
        for sx in (-1,1):
            box((sx*128,sy*481,716),(20,10,15),'steel',1.2)
            box((sx*128,sy*487,716),(16,1,11),'lamp',.6)
    for paintname in m.polygons:
        m.material_overrides[paintname]=f'{MAT}/{paintname}.vmat'
        m.tile_overrides[paintname]=96 if paintname in ('yellow','red','white') else 64
    return m

