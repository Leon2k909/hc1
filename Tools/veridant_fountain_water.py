"""Shallow water and stone liner inside the existing forecourt fountain."""
import math
import numpy as np

def ring(m,paint,z):
    for a,b in zip(np.linspace(0,math.tau,129),np.linspace(0,math.tau,129)[1:]):
        pts=[np.array((1600+r*math.cos(t),150+r*math.sin(t),z)) for r,t in ((10.05,a),(83.65,a),(83.65,b),(10.05,b))]
        m.polygon(paint,pts,normal=np.array((0,0,1.)))

def build_into(liner,water):
    ring(liner,'vr_pool_liner',14.05)
    liner.material_overrides['vr_pool_liner']='materials/veridant/pool-v2/liner.vmat'
    liner.tile_overrides['vr_pool_liner']=38.
    ring(water,'vr_pool',17.5)
