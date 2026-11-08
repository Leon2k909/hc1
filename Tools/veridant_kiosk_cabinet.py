"""Weatherproof double-door service cabinet replacing the terrace's plain block."""
from riverdale_parts import box,rod,v
def build_into(m,c=(0,0),z0=0):
    e,n=c
    def b(a,b,c,d,z,w,paint='vr_steel'):box(m,e+a,e+b,n+c,n+d,z0+z,z0+w,paint)
    b(-14.5,14,-29.5,29.5,1,4,'vr_dark')
    b(-15,13.7,-30,30,4,59)
    b(-15,15,-30,30,58.8,60)
    # Separate front leaves, framed by the shell with a continuous central seam.
    for lo,hi in [(-29,-.35),(.35,29)]:
        b(13.7,14.55,lo,hi,4.8,58.1)
        # Lower louvred ventilation bank recessed behind protective rain blades.
        b(14.55,14.58,lo+3,hi-3,9,22,'vr_dark')
        for z in (10,12,14,16,18,20):
            b(14.6,14.95,lo+3,hi-3,z,z+.65)
        for z in (14,48):
            nn=lo+.7 if hi<0 else hi-.7
            b(14.55,14.95,nn-.4,nn+.4,z,z+3)
    for nn in (-2.1,2.1):
        for z in (29,36):rod(m,v(e+14.6,n+nn,z0+z),v(e+15,n+nn,z0+z),.28,'vr_steel',12,caps=True)
        rod(m,v(e+15,n+nn,z0+29),v(e+15,n+nn,z0+36),.28,'vr_steel',16,caps=True)
