"""Existing Riverdale railing kit reused on the central Sewage service platform."""
import math
import numpy as np
import riverdale_parts as P

PLACEMENTS=[((-145,95),(580,95)),((-145,264),(0,264)),((390,264),(580,264)),
            ((-700,125),(-145,125)),((-700,255),(-145,255)),
            ((580,125),(840,125)),((580,255),(840,255))]
MATERIALS={'ww_platform_rail':'materials/sewage/yellow.vmat',
           'ww_platform_fastener':'materials/sewage/crane-blocks-v1/steel.vmat'}

def matches(a,b,z,height):return z==160 and height==42 and (tuple(a),tuple(b)) in PLACEMENTS

def emit(m,a,b,z=160,height=42):
    m.material_overrides.update(MATERIALS);m.tile_overrides.update({p:64 for p in MATERIALS})
    P.railing(m,[a,b],z,paint='ww_platform_rail',height=height,post_every=64,kick=True)
    a,b=np.asarray((*a,z),float),np.asarray((*b,z),float)
    count=max(1,math.ceil(np.linalg.norm(b-a)/64))
    along=P.unit(b-a);across=np.cross(along,P.UP)
    # Anchor heads sit on the kit's base plates, clear of the tubular sockets.
    for t in np.linspace(0,1,count+1):
        foot=a+(b-a)*t
        for u in (-1.55,1.55):
            for v in (-1.55,1.55):
                p=foot+along*u+across*v+P.UP*.4
                P.rod(m,p,p+P.UP*.15,.38,'ww_platform_fastener',12,True)
                P.rod(m,p+P.UP*.15,p+P.UP*.49,.27,'ww_platform_fastener',6,True)
    return m
