import math
import numpy as np
import map_kit as K
import riverdale_parts as P
PROP='models/props/cerroblanco/pan_dulce_v1'
def positions():
    rng=np.random.default_rng(5)
    return [(628+6+42*(k%5)/4+rng.uniform(-1.5,1.5),609+8*(k//5)+rng.uniform(-1,1)) for k in range(9)]
def build():
    m=K.Model();sides=48;rings=16
    for index,(e,n) in enumerate(positions()):
        phase=index*1.713
        def point(t,p):
            r=2.55*math.sin(t)*(1+.018*math.sin(3*p+phase)+.012*math.sin(7*p-phase))
            x=r*math.cos(p);y=r*math.sin(p)*.96
            u=math.hypot(x+3.2,y*.94)
            groove=math.exp(-(math.sin(math.pi*u/.86)/.22)**2)
            z=.95+1.75*math.cos(t)-.095*groove*max(math.sin(t)*math.cos(t),0)**.5
            return np.array((x,y,z))
        def normal(t,p):
            if t<1e-5:return np.array((0.,0.,1.))
            dt=point(t+.0001,p)-point(t-.0001,p);dp=point(t,p+.0001)-point(t,p-.0001)
            v=P.unit(np.cross(dt,dp))
            return v
        c=np.array((e,n,43.6))
        for row in range(rings):
            for k in range(sides):
                coords=[(math.pi/2*row/rings,math.tau*k/sides),(math.pi/2*row/rings,math.tau*(k+1)/sides),(math.pi/2*(row+1)/rings,math.tau*(k+1)/sides),(math.pi/2*(row+1)/rings,math.tau*k/sides)]
                if row==0:coords=coords[1:]
                pts=[point(t,p) for t,p in coords];ns=[normal(t,p) for t,p in coords];avg=np.mean(pts,axis=0)
                u=math.hypot(avg[0]+3.2,avg[1]*.94)
                material='cbf_pastry' if abs(math.sin(math.pi*u/.86))<.24 else 'concha_crust'
                P.card(m,material,[c+p for p in pts],sum(ns),normals=ns)
        # Rounded baked lower edge and closed flat underside.
        profile=[(0,0),(2.1,0),(2.35,.18),(2.5,.55),(2.55,.95)]
        for (r0,z0),(r1,z1) in zip(profile,profile[1:]):
            for k in range(sides):
                a,b=math.tau*k/sides,math.tau*(k+1)/sides
                fa=1+.018*math.sin(3*a+phase)+.012*math.sin(7*a-phase);fb=1+.018*math.sin(3*b+phase)+.012*math.sin(7*b-phase)
                pts=[c+(r0*fa*math.cos(a),r0*fa*math.sin(a)*.96,z0),c+(r0*fb*math.cos(b),r0*fb*math.sin(b)*.96,z0),c+(r1*fb*math.cos(b),r1*fb*math.sin(b)*.96,z1),c+(r1*fa*math.cos(a),r1*fa*math.sin(a)*.96,z1)]
                if r0==0:pts=pts[1:]
                P.card(m,'cbf_pastry',pts,((z1-z0)*math.cos((a+b)/2),(z1-z0)*math.sin((a+b)/2),r0-r1))
    m.material_overrides.update({'cbf_pastry':'materials/cerroblanco/fitout/cbf_pastry.vmat','concha_crust':PROP+'/crust.vmat'})
    m.tile_overrides.update({'cbf_pastry':8.,'concha_crust':8.});return m
