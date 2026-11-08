"""Metal glazing bars and stepped lower housings for north terrace lanterns."""
from riverdale_parts import box

def build_one(m, base, h=96):
    e,n,z=base
    t=z+h-16
    for side in (-1,1):
        # Paired horizontal glazing bars and a slim central mullion on each face.
        for dz in (6,10):
            box(m,e-5.25,e+5.25,n+side*4.8-.35,n+side*4.8+.35,t+dz-.3,t+dz+.3,'vr_steel')
            box(m,e+side*4.8-.35,e+side*4.8+.35,n-5.25,n+5.25,t+dz-.3,t+dz+.3,'vr_steel')
        box(m,e-.3,e+.3,n+side*4.8-.35,n+side*4.8+.35,t+2,t+14,'vr_steel')
        box(m,e+side*4.8-.35,e+side*4.8+.35,n-.3,n+.3,t+2,t+14,'vr_steel')
    for r,lo,hi in ((5.5,-1,0),(4.3,-2,-1),(3.1,-3,-2)):
        box(m,e-r,e+r,n-r,n+r,t+lo,t+hi,'vr_steel')

def build_into(m):
    for base in ((-164,240,128),(-92,724,128),(240,580,128)):
        build_one(m,base)
