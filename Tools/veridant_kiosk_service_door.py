"""Closed decorative service door on the solid terrace kiosk."""
from riverdale_parts import box,rod,v
def build_into(m,c=(0,0),z0=0):
    e,n=c
    def b(a,b,c,d,z,w,paint='vr_steel'):box(m,e+a,e+b,n+c,n+d,z0+z,z0+w,paint)
    b(0,1.1,-22,-20,0,76);b(0,1.1,20,22,0,76);b(0,1.1,-20,20,74,76)
    b(.05,.3,-20,20,.1,74,'vr_dark')
    b(.3,.65,-19.5,19.5,.5,73.5,'vr_dark')
    # Raised stiles and rails frame two recessed panels.
    for lo,hi in [(-19.5,-17),(17,19.5)]:b(.65,.95,lo,hi,1,73,'vr_dark')
    for z,w in [(1,3),(29,32),(70.5,73)]:b(.65,.95,-17,17,z,w,'vr_dark')
    b(.95,1.02,-19.5,19.5,.6,10)
    for z in (12,37,63):b(.95,1.4,-20,-18.7,z,z+3.5)
    b(.95,1.2,14,16,34,41)
    rod(m,v(e+1.2,n+15,z0+38),v(e+2.2,n+15,z0+38),.35,'vr_steel',16,caps=True)
    rod(m,v(e+2.2,n+15,z0+38),v(e+2.2,n+10.5,z0+38),.35,'vr_steel',16,caps=True)
    b(1.2,1.25,14.7,15.3,35.1,36.5,'vr_dark')
