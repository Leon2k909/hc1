"""Shed lock hardware, in the existing door frame; visual geometry only."""
import math
import numpy as np
import belltower_furniture as F

BRASS = 'door_brass'
STEEL = 'shed_lock_steel'
STEEL_MATERIAL = 'materials/belltower/shed_lock_steel.vmat'


def build(model, origin, axes, seed=0):
    origin, axes = np.asarray(origin, float), np.asarray(axes, float)
    run, out, up = axes
    model.material_overrides[STEEL] = STEEL_MATERIAL
    model.tile_overrides[STEEL] = 32

    def at(point):
        return origin + np.asarray(point) @ axes

    def emit(paint, points, normal, normals=None):
        F.face(model, paint, [at(p) for p in points], np.asarray(normal) @ axes,
               normals=[np.asarray(n) @ axes for n in normals] if normals else None)

    def outline(width, height, radius, cx=0, cz=0, steps=8):
        return [np.array((cx+sx*(width/2-radius)+radius*math.cos(a),
                          cz+sz*(height/2-radius)+radius*math.sin(a)))
                for sx, sz, start in ((1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270))
                for a in np.radians(np.linspace(start,start+90,steps+1))]

    def cap(contour, y, normal, paint, hole=None):
        if hole is None:
            contour=[p for i,p in enumerate(contour)
                     if abs(np.cross(p-contour[i-1],contour[(i+1)%len(contour)]-p))>1e-10]
            emit(paint, [(p[0],y,p[1]) for p in contour], (0,normal,0))
            return
        hx, hz, rx, rz = hole
        # Add uniform rays so a circular recess stays circular even where the
        # surrounding case has long straight edges and few contour vertices.
        centre=np.array((hx,hz))
        angles=[math.atan2(*(p-centre)[::-1])%math.tau for p in contour]
        angles+=list(np.linspace(0,math.tau,64,endpoint=False))
        if rz is not None:
            angles+=[math.atan2(sz*rz,sx*rx)%math.tau for sx in (-1,1) for sz in (-1,1)]
        angles=sorted(set(0.0 if min(a,math.tau-a)<1e-8 else round(a,8) for a in angles))
        def cross(a,b):return a[0]*b[1]-a[1]*b[0]
        boundary=[]
        for angle in angles:
            direction=np.array((math.cos(angle),math.sin(angle)));hits=[]
            for i,a in enumerate(contour):
                edge=contour[(i+1)%len(contour)]-a;denom=cross(direction,edge)
                if abs(denom)<1e-12:continue
                distance=cross(a-centre,edge)/denom;t=cross(a-centre,direction)/denom
                if distance>0 and -1e-7<=t<=1+1e-7:hits.append(distance)
            assert hits
            boundary.append(centre+direction*min(hits))
        contour=boundary
        inner=[]
        for p in contour:
            d=p-np.array((hx,hz));d/=np.linalg.norm(d)
            if rz is None:
                q=np.array((hx,hz))+d*rx
            else:
                q=np.array((hx,hz))+d/max(abs(d[0])/rx,abs(d[1])/rz)
            inner.append(q)
        for i,p in enumerate(contour):
            j=(i+1)%len(contour)
            emit(paint, [(p[0],y,p[1]),(contour[j][0],y,contour[j][1]),
                         (inner[j][0],y,inner[j][1]),(inner[i][0],y,inner[i][1])], (0,normal,0))
        return inner

    def extrusion(cx, cy, cz, width, height, depth, radius, paint, bevel=.08, hole=None, blind=False):
        profiles=[(-depth/2,bevel),(-depth/2+bevel,0),
                  (depth/2-bevel,0),(depth/2,bevel)]
        loops=[outline(width-2*s,height-2*s,max(.04,radius-s),cx,cz) for y,s in profiles]
        for k,((ya,sa),(yb,sb)) in enumerate(zip(profiles,profiles[1:])):
            for i,a in enumerate(loops[k]):
                j=(i+1)%len(loops[k]);b=loops[k][j];c=loops[k+1][j];d=loops[k+1][i]
                mid=(a+b)/2-np.array((cx,cz))
                normal=(mid[0]*(yb-ya), (sb-sa)*max(width,height), mid[1]*(yb-ya))
                emit(paint,[(a[0],cy+ya,a[1]),(b[0],cy+ya,b[1]),
                            (c[0],cy+yb,c[1]),(d[0],cy+yb,d[1])],normal)
        cap(loops[0],cy-depth/2,-1,paint,None if blind else hole)
        inner=cap(loops[-1],cy+depth/2,1,paint,hole)
        if hole:
            bottom=cy+depth/2-.28 if blind else cy-depth/2
            for i,a in enumerate(inner):
                b=inner[(i+1)%len(inner)]
                emit(paint,[(a[0],bottom,a[1]),(b[0],bottom,b[1]),
                            (b[0],cy+depth/2,b[1]),(a[0],cy+depth/2,a[1])],
                     (hole[0]-(a[0]+b[0])/2,0,hole[1]-(a[1]+b[1])/2))
            if blind:
                cap(inner,bottom,1,F.IRON)

    def tube(points, radius, paint, frame, sides=12):
        points=[np.asarray(p,float) for p in points];rings=[];normals=[]
        frame=np.asarray(frame,float)
        for i,p in enumerate(points):
            tangent=points[min(i+1,len(points)-1)]-points[max(i-1,0)]
            tangent/=np.linalg.norm(tangent)
            u=frame-tangent*np.dot(frame,tangent);u/=np.linalg.norm(u)
            v=np.cross(tangent,u)
            ns=[u*math.cos(k*math.tau/sides)+v*math.sin(k*math.tau/sides) for k in range(sides)]
            rings.append([p+radius*n for n in ns]);normals.append(ns)
        for i in range(len(points)-1):
            for k in range(sides):
                j=(k+1)%sides
                ns=[normals[i][k],normals[i][j],normals[i+1][j],normals[i+1][k]]
                emit(paint,[rings[i][k],rings[i][j],rings[i+1][j],rings[i+1][k]],sum(ns),ns)
        for i,sign in ((0,-1),(-1,1)):
            tangent=points[1]-points[0] if i==0 else points[-1]-points[-2]
            emit(paint,rings[i],tangent*sign)

    # Fix the hasp to the door's middle brace; a real slot receives the staple.
    extrusion(-.5,2.12,2.2,2.7,2.4,.20,.26,F.IRON,.045)
    extrusion(3.8,2.32,2.2,8.1,2.25,.22,.32,F.IRON,.05,hole=(6.4,2.2,.38,.80))
    for x in (-1.25,.25):
        for z in (1.48,2.92):
            F.bolt(model,at((x,2.26,z)),out,.16,True)
    # The pin and rolled hinge knuckles are separate from the strap.
    for z0,z1 in ((1.1,1.65),(1.82,2.55),(2.72,3.3)):
        F.turned(model,at((.45,2.36,(z0+z1)/2)),up,run,
                 [(.25,-(z1-z0)/2),(.25,(z1-z0)/2)],STEEL,12,True)
    F.turned(model,at((.45,2.36,2.2)),up,run,[(.12,-1.28),(.12,1.28)],STEEL,12,True)

    # The staple stands off the jamb. The shackle crosses its open eye.
    extrusion(6.4,1.42,2.2,1.35,3.6,.28,.22,F.IRON,.06)
    staple=[(6.4,1.55,1.35),(6.4,3.03,1.35)]
    staple += [(6.4,3.03+.85*math.cos(a),2.2+.85*math.sin(a))
               for a in np.linspace(-math.pi/2,math.pi/2,17)[1:]]
    staple += [(6.4,1.55,3.05)]
    tube(staple,.16,STEEL,(1,0,0),10)

    # Rounded brass case: body thickness and two bevels catch light from an angle.
    cx,cy,cz=6.4,3.18,-1.9
    extrusion(cx,cy,cz,3.25,3.8,1.26,.55,BRASS,.15,
              hole=(cx,cz-.65,.29,None),blind=True)
    shackle=[(cx-1.05,cy,-.14),(cx-1.05,cy,1.25)]
    shackle += [(cx+1.05*math.cos(a),cy,1.25+1.05*math.sin(a))
                for a in np.linspace(math.pi,0,25)[1:]]
    shackle += [(cx+1.05,cy,-.14)]
    tube(shackle,.19,STEEL,(0,1,0))
    # A recessed cylinder with a cut keyway and a dark back, not a painted dot.
    front=cy+1.26/2-.11;keyz=cz-.65
    circle=[np.array((cx+.25*math.cos(a),keyz+.25*math.sin(a))) for a in np.linspace(0,math.tau,33)[:-1]]
    slot=cap(circle,front,1,STEEL,(cx,keyz,.052,.145))
    for i,a in enumerate(slot):
        b=slot[(i+1)%len(slot)]
        emit(STEEL,[(a[0],front,a[1]),(b[0],front,b[1]),
                    (b[0],front-.13,b[1]),(a[0],front-.13,a[1])],
             (cx-(a[0]+b[0])/2,0,keyz-(a[1]+b[1])/2))
    cap(slot,front-.135,1,F.IRON)


def old_handle(model, origin, axes, seed):
    """Exact previous two solids, used only to locate the installed OBJ faces."""
    origin,axes=np.asarray(origin,float),np.asarray(axes,float)
    def at(q):return origin+np.asarray(q)@axes
    F.bevel_box(model,at((0,1.63,0)),axes,(3.3,.30,7),F.IRON,.2,seed)
    F.beam(model,at((0,2.20,-2.2)),at((0,2.20,2.2)),(.65,.65),F.IRON,.19,seed+2,up=axes[1])
