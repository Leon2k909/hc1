"""Reference-led wall extinguisher: smooth steel, separate hardware and UV labels.

Plan inches and a supplied railhead_dress_detail.Frame. No collisions, scene
placements, random global state, or asset writes are introduced by this helper.
"""
import math
import numpy as np

PREFIX = 'ext_v2_'
MATERIALS = {PREFIX+name:f'materials/props/extinguisher-v2/{name}.vmat'
             for name in ('red','label','sign','gauge','rubber','steel','brass','dark','seal')}


def unit(v):
    v = np.asarray(v,float)
    return v/max(np.linalg.norm(v),1e-12)


def bezier(points, count=20):
    a,b,c,d = np.asarray(points,float)
    return np.asarray([(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
                       for t in np.linspace(0,1,count)])


class Build:
    def __init__(self,model,frame):
        self.model,self.frame = model,frame
        model.material_overrides.update(MATERIALS)
        model.tile_overrides.update({paint:16 for paint in MATERIALS})

    def vector(self,v):
        return self.frame.x*v[0]+self.frame.y*v[1]+self.frame.z*v[2]

    def face(self,paint,points,normals,uv=None):
        points = np.asarray(points,float)
        normals = np.asarray(normals,float)
        if normals.ndim == 1: normals = np.tile(normals,(len(points),1))
        pts = [self.frame.p(*p) for p in points]
        ns = [unit(self.vector(n)) for n in normals]
        cross = np.zeros(3)
        for i in range(1,len(pts)-1): cross += np.cross(pts[i]-pts[0],pts[i+1]-pts[0])
        if np.linalg.norm(cross) < 1e-9: return
        if np.dot(cross,np.sum(ns,axis=0)) < 0:
            pts.reverse(); ns.reverse()
            if uv is not None: uv = list(reversed(uv))
        self.model.polygon(PREFIX+paint,pts,normals=ns,uv=uv)

    def box(self,paint,lo,hi):
        x0,y0,z0 = lo; x1,y1,z1 = hi
        for points,n in (
            ([(x0,y0,z0),(x0,y1,z0),(x0,y1,z1),(x0,y0,z1)],(-1,0,0)),
            ([(x1,y0,z0),(x1,y0,z1),(x1,y1,z1),(x1,y1,z0)],(1,0,0)),
            ([(x0,y0,z0),(x0,y0,z1),(x1,y0,z1),(x1,y0,z0)],(0,-1,0)),
            ([(x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)],(0,1,0)),
            ([(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0)],(0,0,-1)),
            ([(x0,y0,z1),(x0,y1,z1),(x1,y1,z1),(x1,y0,z1)],(0,0,1))):
            uv = [(0.06,.1),(0.12,.1),(0.12,.3),(0.06,.3)] if paint in ('red','seal') else None
            self.face(paint,points,n,uv)

    def tube(self,paint,path,radius,sides=12,flatten=1.0,caps=True):
        path = np.asarray(path,float)
        rings,ns = [],[]
        for i,p in enumerate(path):
            tangent = unit(path[min(i+1,len(path)-1)]-path[max(0,i-1)])
            reference = np.array((0.,1.,0.)) if abs(tangent[1]) < .9 else np.array((1.,0.,0.))
            u = unit(np.cross(tangent,reference)); v = unit(np.cross(tangent,u))
            normals = [unit(math.cos(t)*u+math.sin(t)/flatten*v) for t in np.linspace(0,2*math.pi,sides,endpoint=False)]
            ring = [p+radius*(math.cos(t)*u+flatten*math.sin(t)*v) for t in np.linspace(0,2*math.pi,sides,endpoint=False)]
            rings.append(ring); ns.append(normals)
        for i in range(len(path)-1):
            for k in range(sides):
                j = (k+1)%sides
                self.face(paint,[rings[i][k],rings[i][j],rings[i+1][j],rings[i+1][k]],
                          [ns[i][k],ns[i][j],ns[i+1][j],ns[i+1][k]])
        if caps:
            self.face(paint,rings[0],unit(path[0]-path[1]))
            self.face(paint,rings[-1],unit(path[-1]-path[-2]))

    def lathe(self,paint,profile,centre=(0,3.9),sides=64):
        profile = np.asarray(profile,float)
        normals = []
        for i,(radius,z) in enumerate(profile):
            tangent = unit(profile[min(i+1,len(profile)-1)]-profile[max(0,i-1)])
            normals.append((tangent[1],-tangent[0]))
        for i,((r0,z0),(r1,z1)) in enumerate(zip(profile,profile[1:])):
            for k in range(sides):
                t0,t1 = -math.pi+2*math.pi*k/sides,-math.pi+2*math.pi*(k+1)/sides
                direction = lambda t: np.array((math.sin(t),math.cos(t),0))
                a,b = direction(t0),direction(t1)
                c0,c1 = np.array((*centre,z0)),np.array((*centre,z1))
                pts = [c0+r0*a,c0+r0*b,c1+r1*b,c1+r1*a]
                ns = [normals[i][0]*a+(0,0,normals[i][1]),normals[i][0]*b+(0,0,normals[i][1]),
                      normals[i+1][0]*b+(0,0,normals[i+1][1]),normals[i+1][0]*a+(0,0,normals[i+1][1])]
                uv = [(.012+.475*k/sides,.02+.96*(z0-18)/21.2),
                      (.012+.475*(k+1)/sides,.02+.96*(z0-18)/21.2),
                      (.012+.475*(k+1)/sides,.02+.96*(z1-18)/21.2),
                      (.012+.475*k/sides,.02+.96*(z1-18)/21.2)] if paint == 'red' else None
                if r0 < 1e-6:
                    self.face(paint,pts[1:],ns[1:],uv[1:] if uv else None)
                elif r1 < 1e-6:
                    self.face(paint,pts[:3],ns[:3],uv[:3] if uv else None)
                else:
                    self.face(paint,pts,ns,uv)

    def disc(self,paint,centre,radius,normal=(0,1,0),sides=40,atlas=None):
        centre = np.asarray(centre,float); normal = unit(normal)
        u = np.array((1.,0.,0.)); v = unit(np.cross(normal,u))
        # In the front frame, positive U is screen right and positive V is up.
        if v[2] < 0: v = -v
        for k in range(sides):
            t0,t1 = 2*math.pi*k/sides,2*math.pi*(k+1)/sides
            a,b = math.cos(t0)*u+math.sin(t0)*v,math.cos(t1)*u+math.sin(t1)*v
            uv = None
            if atlas:
                x0,y0,x1,y1 = atlas
                uv = [((x0+x1)/2,1-(y0+y1)/2),
                      ((x0+x1)/2+(x1-x0)*math.cos(t0)/2,1-(y0+y1)/2+(y1-y0)*math.sin(t0)/2),
                      ((x0+x1)/2+(x1-x0)*math.cos(t1)/2,1-(y0+y1)/2+(y1-y0)*math.sin(t1)/2)]
            self.face(paint,[centre,centre+radius*a,centre+radius*b],normal,uv)


def build_into(model,frame):
    b = Build(model,frame)
    # Folded backplate, cradle and actual fasteners connect the vessel to the wall.
    b.box('red',(-2.45,.03,18.8),(2.15,.25,35.0))
    b.box('dark',(-1.9,.24,19.0),(1.9,1.3,19.28))
    for x,z in ((-1.95,19.45),(1.65,19.45),(-1.95,34.45),(1.65,34.45)):
        b.tube('steel',[(x,.25,z),(x,.39,z)],.18,16)
        b.box('dark',(x-.11,.395,z-.018),(x+.11,.412,z+.018))
    profile = [(0,18.12),(1.8,18.12),(2.5,18.18),(2.88,18.42),(3.06,18.78),
               (3.15,19.2),(3.15,19.42),(3.19,19.48),(3.19,19.57),(3.15,19.64),
               (3.15,35.9),(3.12,36.5),(2.99,37.10),(2.72,37.62),(2.2,38.03),
               (1.58,38.32),(.94,38.5),(.89,38.85),(.89,39.10),(0,39.10)]
    b.lathe('red',profile)
    # A curved paper label, not a blank band all the way around the vessel.
    for k in range(48):
        t0,t1 = -1.18+2.36*k/48,-1.18+2.36*(k+1)/48
        a,bn = np.array((math.sin(t0),math.cos(t0),0)),np.array((math.sin(t1),math.cos(t1),0))
        c0,c1 = np.array((0,3.9,22.1)),np.array((0,3.9,33.8))
        u0,u1 = .507+.486*k/48,.507+.486*(k+1)/48
        b.face('label',[c0+3.195*a,c0+3.195*bn,c1+3.195*bn,c1+3.195*a],
               [a,bn,bn,a],[(u0,.268),(u1,.268),(u1,.995),(u0,.995)])
    b.lathe('brass',[(0,39.08),(.84,39.08),(.84,39.45),(.66,39.5),(.66,40.55),(.50,40.8),(0,40.8)],sides=32)
    b.lathe('brass',[(.82,39.15),(.97,39.2),(.97,39.55),(.82,39.6)],sides=6)
    for z in (39.75,39.88,40.01):
        b.lathe('steel',[(.65,z),(.70,z+.025),(.70,z+.06),(.65,z+.08)],sides=32)
    # Two stamped, rounded levers with space between them and a shared pivot.
    upper = bezier([(0.35,3.9,40.95),(.05,3.9,42.05),(-2.0,3.9,42.45),(-3.85,3.9,42.2)],18)
    lower = bezier([(.35,3.9,40.78),(-.4,3.9,40.65),(-2.3,3.9,40.0),(-3.72,3.9,39.35)],18)
    b.tube('dark',upper,.13,12,flatten=3.0)
    b.tube('steel',lower,.115,12,flatten=2.9)
    b.box('dark',(-.35,3.48,40.45),(.60,4.32,41.35))
    b.tube('steel',[(.12,3.35,40.98),(.12,4.45,40.98)],.19,24)
    b.box('dark',(-.01,4.455,40.957),(.25,4.47,41.003))
    # Front-facing gauge: brass connection, metal case, printed recessed dial.
    b.tube('brass',[(.62,4.1,40.15),(.62,5.06,40.15)],.22,24)
    b.tube('steel',[(.62,4.87,40.15),(.62,5.17,40.15)],.71,40)
    b.disc('dark',(.62,5.178,40.15),.65)
    b.disc('gauge',(.62,5.19,40.15),.605,atlas=(.52,.76,.734,.985))
    # Curved hose and crimped nozzle are separate, shaded rubber/metal meshes.
    hose = np.vstack((bezier([(.70,3.95,40.25),(4.65,3.95,40.9),(4.50,4.0,36.3),(4.35,4.08,32.5)],24),
                      bezier([(4.35,4.08,32.5),(4.25,4.12,28),(4.03,4.2,24.0),(4.08,4.25,22.35)],20)[1:]))
    b.tube('steel',[(.65,3.95,40.25),(1.25,3.95,40.25)],.42,24)
    b.tube('rubber',hose,.32,14)
    b.tube('steel',[(4.08,4.25,22.8),(4.08,4.25,22.25)],.43,24)
    b.tube('rubber',[(4.08,4.25,22.25),(4.08,4.25,19.4)],.49,24)
    b.tube('dark',[(4.08,4.25,19.4),(4.08,4.25,19.10)],.56,24)
    b.box('dark',(3.20,3.70,23.55),(4.52,4.62,23.8))
    # Safety pin and intact tamper seal, sized to survive a normal player view.
    b.tube('steel',[(-.35,3.28,41.17),(-.35,4.68,41.17)],.055,10)
    pin = [(-.35+.34*math.cos(t),4.70,41.52+.34*math.sin(t)) for t in np.linspace(0,2*math.pi,33)]
    b.tube('steel',pin,.055,8,caps=False)
    b.tube('seal',[(-.30,4.76,41.25),(-.65,4.82,40.9),(-.95,4.85,40.0)],.035,8)
    b.box('seal',(-1.18,4.78,39.95),(-.77,4.9,40.65))
    # Retain the mounting height and sign footprint of every existing placement.
    b.box('red',(-4.7,.03,52.0),(4.7,.25,61.4))
    b.face('sign',[(-4.7,.27,52),(4.7,.27,52),(4.7,.27,61.4),(-4.7,.27,61.4)],
           (0,1,0),[(.754,.006),(.994,.006),(.994,.254),(.754,.254)])
    for x in (-4.13,4.13):
        for z in (52.57,60.83):
            b.tube('steel',[(x,.27,z),(x,.39,z)],.15,16)
            b.box('dark',(x-.09,.395,z-.017),(x+.09,.405,z+.017))
    return model
