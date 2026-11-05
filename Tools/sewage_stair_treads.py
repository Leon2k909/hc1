"""Open steel grating for Sewage's main west stair flight; render mesh only."""
import math
import numpy as np
import map_kit as K
from sewage_warning_sign import rod

MAIN_FLIGHT=(-925,-765,-100,300,0,160)
MATERIALS={
    'ww_tread_steel':'materials/sewage/crane-blocks-v1/steel.vmat',
    'ww_tread_frame':'materials/sewage/pipe-texture-v1/pipe.vmat',
    'ww_tread_nosing':'materials/sewage/crane-blocks-v1/paint.vmat',
    'ww_tread_bolt':'materials/sewage/rust.vmat',
}


def original_treads(m,e0,e1,n0,n1,z0,z1):
    """Frozen pre-upgrade tread geometry, used to identify precisely what to replace."""
    count=math.ceil(abs(z1-z0)/8)
    for i in range(count):
        a=n0+(n1-n0)*i/count;b=n0+(n1-n0)*(i+1)/count
        h=z0+(z1-z0)*(i+1)/count
        m.box((e0,min(a,b),h-4),(e1,max(a,b)+.1,h),{'default':'steel','+z':'grate'})
        m.box((e0,min(a,b),h),(e1,min(a,b)+2,h+.6),'yellow')
    return m


def nosing(m,e0,e1,n,z):
    # A folded, bevelled anti-slip angle instead of the former flat painted strip.
    profile=[(n,z-.10),(n+.35,z+.42),(n+2.15,z+.42),(n+2.5,z+.08),
             (n+2.5,z-.30),(n+.65,z-.30),(n+.65,z-2.50),(n,z-2.50)]
    left=[(e0,a,b) for a,b in profile];right=[(e1,a,b) for a,b in profile]
    m.polygon('ww_tread_frame',left)
    m.polygon('ww_tread_frame',list(reversed(right)))
    for i in range(len(profile)):
        j=(i+1)%len(profile)
        m.polygon('ww_tread_nosing' if i<4 or i==7 else 'ww_tread_frame',[left[i],right[i],right[j],left[j]])
    # Individual raised serrations catch the light without changing the walk surface.
    for e in np.arange(e0+2,e1-1,5):
        m.box((e,n+.38,z+.42),(min(e+1.25,e1),n+.85,z+.57),'ww_tread_steel')


def emit(m,e0,e1,n0,n1,z0,z1):
    count=math.ceil(abs(z1-z0)/8)
    for i in range(count):
        a=n0+(n1-n0)*i/count;b=n0+(n1-n0)*(i+1)/count
        lo,hi=sorted((a,b));h=z0+(z1-z0)*(i+1)/count
        # 50 mm-spaced, 8 mm-thick bearing bars with real voids between them.
        for e in np.arange(e0+2.0,e1-1.0,2.0):
            m.box((e,lo+2.4,h-1.8),(e+.32,hi-.6,h),'ww_tread_steel')
        for n in np.arange(lo+4,hi-1,4.8):
            m.box((e0+1,n,h-1.1),(e1-1,n+.28,h-.15),'ww_tread_steel')
        # Folded end plates and a rear tie make each tread a separate bolted assembly.
        for e in (e0+.75,e1-1.25):
            m.box((e,lo+.65,h-3.2),(e+.5,hi-.3,h-.1),'ww_tread_frame')
        m.box((e0+.75,hi-.9,h-2.7),(e1-.75,hi-.3,h-.1),'ww_tread_frame')
        nosing(m,e0+.5,e1-.5,lo,h)
        for e,direction in ((e0+.70,-1),(e1-.70,1)):
            for n in (lo+4,hi-3):
                rod(m,(e,n,h-1.9),(e+direction*.30,n,h-1.9),.75,'ww_tread_steel',16)
                rod(m,(e+direction*.30,n,h-1.9),(e+direction*.85,n,h-1.9),.48,'ww_tread_bolt',6)
    # The four-metre-wide flight receives a central support, below the existing ramp.
    mid=(e0+e1)/2
    m.beam((mid,n0,z0-10),(mid,n1,z1-10),(4.5,8),'ww_tread_frame')
    m.material_overrides.update(MATERIALS)
    m.tile_overrides.update({p:48 for p in MATERIALS})
    return m
