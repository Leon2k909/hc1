"""Panel-built stone counter with an eased slab and recessed toe plinth."""
from riverdale_parts import box,bevel_box,v
import veridant_parts as P
def build_into(m,c=(0,0),z0=0):
    e,n=c;axes=(v(1,0,0),v(0,1,0),v(0,0,1))
    box(m,e-69.5,e+69.5,n-14.5,n+14.5,z0+3,z0+40,'vr_dark')
    box(m,e-68,e+68,n-13,n+13,z0,z0+3,'vr_steel')
    for i in range(4):
        x=e-70+35*(i+.5)
        bevel_box(m,(x,n+14.8,z0+21),axes,(34.8,.4,35.8),'vr_stone',bevel=.12)
    for side in (-1,1):
        bevel_box(m,(e+side*69.8,n,z0+21),axes,(.4,29.6,35.8),'vr_stone',bevel=.12)
    bevel_box(m,(e,n,z0+41),axes,(144,34,2),'vr_stone_dark',bevel=.18)
    P.led(m,(e-68,n+15.3,z0+39),(e+68,n+15.3,z0+39),v(0,1,0),1)
