"""East terrace lanterns using the approved tapered post and framed head designs."""
from riverdale_parts import lathe,box,v,UP
from veridant_terrace_lantern_frames import build_one as frames

BASES=((1140,-200,192),(1140,300,192),(410,566,192),(1000,700,192),(798,-150,192))

def build_one(m,base,h=96):
    from veridant_parts import lantern_roof
    e,n,z=base
    profile=[(0,0),(4.1,0),(4.5,.4),(4.5,1.1),(4.2,1.5),(3.8,1.8),(3.8,7.8),(3.6,8.4),(3,9),(2.5,10),(2.2,12),(2.2,18),(1.9,110),(1.9,121),(2.4,122),(2.4,124),(0,124)]
    def height(t):
        if h < 34:return t*(h-16)/124
        return t if t<=18 else 18+(t-18)*(h-34)/106
    lathe(m,(e,n),[(r,z+height(t)) for r,t in profile],'vr_steel',64)
    box(m,e-1.05,e+1.05,n-2.24,n-2.12,z+13,z+20,'vr_steel')
    t=z+h-16
    box(m,e-6,e+6,n-6,n+6,t,t+2,'vr_steel')
    for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1)):
        box(m,e+sx*5.2-.6,e+sx*5.2+.6,n+sy*5.2-.6,n+sy*5.2+.6,t+2,t+14,'vr_steel')
    box(m,e-4.6,e+4.6,n-4.6,n+4.6,t+2,t+14,'vr_lamp')
    lantern_roof(m,v(e,n,t))
    frames(m,base,h)

def build_into(m):
    for b in BASES:build_one(m,b)
