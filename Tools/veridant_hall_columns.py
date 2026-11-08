"""Smooth stone columns with continuous cylindrical UVs and small eased ends."""
import math
from riverdale_parts import card,v,UP

def build_one(m,c=(0,0)):
    sides=96;r=14;tile=192
    ds=[v(math.cos(math.tau*k/sides-math.radians(50)),math.sin(math.tau*k/sides-math.radians(50)),0) for k in range(sides)]
    profile=((13.75,0),(14,.25),(14,111.75),(13.75,112))
    for (ra,za),(rb,zb) in zip(profile,profile[1:]):
        for k in range(sides):
            q=(k+1)%sides
            pts=[v(*c,0)+ds[k]*ra+UP*za,v(*c,0)+ds[q]*ra+UP*za,v(*c,0)+ds[q]*rb+UP*zb,v(*c,0)+ds[k]*rb+UP*zb]
            # Preserve smooth side normals; the 1/4-inch easing meets the hidden ends.
            ns=[ds[k],ds[q],ds[q],ds[k]]
            u0=.1+math.tau*r*k/sides/tile;u1=.1+math.tau*r*(k+1)/sides/tile
            card(m,'vr_stone',pts,sum(ns),normals=ns,uv=[(u0,za/tile),(u1,za/tile),(u1,zb/tile),(u0,zb/tile)])

def build_into(m):
    for e in (100,340,580):build_one(m,(e,-510))
