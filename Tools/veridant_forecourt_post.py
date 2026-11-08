"""Smooth tapered forecourt lantern post, within the existing base footprint."""
from riverdale_parts import lathe,box
def build_into(m,c=(0,0)):
    lathe(m,c,[(0,0),(4.1,0),(4.5,.4),(4.5,1.1),(4.2,1.5),(3.8,1.8),(3.8,7.8),(3.6,8.4),(3,9),(2.5,10),(2.2,12),(2.2,18),(1.9,110),(1.9,121),(2.4,122),(2.4,124),(0,124)],'vr_steel',64)
    # Discreet service-access cover on the widened lower shaft.
    e,n=c
    box(m,e-1.05,e+1.05,n-2.24,n-2.12,13,20,'vr_steel')
