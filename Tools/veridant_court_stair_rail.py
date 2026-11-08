"""Courtyard stair handrail: smooth tubes and anchors fitted to the stone risers."""
import math
import numpy as np
from riverdale_parts import box
from veridant_reception_stair_rail import tube,rounded_cap

def build_into(m):
    a=np.array((660.,-255.,48.2));b=np.array((473.,-255.,169.2));d=(b-a)/np.linalg.norm(b-a)
    tube(m,a,b,.85,sides=32);rounded_cap(m,a,-d,.85);rounded_cap(m,b,d,.85)
    ma=np.array((660.,-255.,28.84));mb=np.array((473.,-255.,149.84))
    tube(m,ma,mb,.45,sides=24);rounded_cap(m,ma,-d,.45);rounded_cap(m,mb,d,.45)
    for e in (656.5,613.25,566.5,519.75,476.5):
        f=(660-e)/187;top=48.2+121*f
        step=min(17,int(math.floor((660-e)/(187/17)))+1)
        tread=128/17*step;bottom=max(0,tread-8)
        # The rail is one inch outside the stair edge, so fix to its side instead
        # of placing a foot plate over the void or through a tread nosing.
        box(m,e-2.25,e+2.25,-256.08,-255.55,bottom,tread-.4,'vr_steel')
        tube(m,(e,-255,bottom+.5),(e,-255,top-.4),.7,sides=24)
        for ee in (e-1.45,e+1.45):
            for zz in (bottom+1.1,tread-1.5):
                tube(m,(ee,-255.54,zz),(ee,-255.25,zz),.18,sides=8)
