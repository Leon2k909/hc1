"""Bolted steel shoes for the café terrace pergola's existing six-inch posts."""
import numpy as np
from riverdale_parts import box,lathe

def build_one(m,e,n,z=128):
    box(m,e-5,e+5,n-5,n+5,z+.02,z+.5,'vr_steel')
    # Four collar strips leave the original post visible and avoid internal faces.
    for a,b,c,d in [(e-3.3,e+3.3,n-3.3,n-3),(e-3.3,e+3.3,n+3,n+3.3),(e-3.3,e-3,n-3,n+3),(e+3,e+3.3,n-3,n+3)]:
        box(m,a,b,c,d,z+.5,z+3,'vr_steel')
    for x in (-4.05,4.05):
        for y in (-4.05,4.05):
            c=(e+x,n+y)
            lathe(m,c,[(.57,z+.5),(.57,z+.64)],'vr_steel',24,cap='vr_steel')
            lathe(m,c,[(.4,z+.64),(.4,z+.96),(.34,z+1.04)],'vr_steel',6,cap='vr_steel')
            lathe(m,c,[(.16,z+1.04),(.16,z+1.13)],'vr_steel',12,cap='vr_steel')

def build_into(m):
    for e in (-680,-520):
        for n in (88,177):build_one(m,e,n)
