"""Round tower dials using the unchanged clock artwork and a profiled bronze bezel.

The existing enamel image is mapped in its original square coordinate system,
but the visible mesh ends at the circular dial. No opaque corners or backing tile.
"""
import math
import numpy as np
import belltower_furniture as F

POSES = (((0,715),(1,0)), ((0,935),(-1,0)),
         ((-110,825),(0,-1)), ((110,825),(0,1)))


def build(model):
    first=model.triangle_count()
    segments=96
    for centre,axis in POSES:
        centre=np.array((*centre,690.0))
        out=np.array((axis[1],-axis[0],0.0))
        along=np.array((*axis,0.0))
        up=np.array((0.,0.,1.))
        circle=[(math.cos(k*math.tau/segments)*37.1,
                 math.sin(k*math.tau/segments)*37.1) for k in range(segments)]
        # Preserve the scale and orientation of the original 80-inch dial image.
        # UVs stop inside its gilt ring, retaining all hour and minute marks.
        F.face(model,"clock",[centre+out*2.5+along*x+up*z for x,z in circle],out,
               [(.5+x/80,.5+z/80) for x,z in circle])
        # The closed profile has an outer shoulder, a rounded inner bead and a
        # recessed seat for the enamel. It mounts directly against tower masonry.
        profile=((40.25,.18),(40.6,.65),(40.6,2.35),(39.9,3.1),
                 (38.45,3.1),(38.15,3.45),(37.35,3.45),(37.05,3.1),
                 (37.05,2.45),(37.05,.25),(40.25,.18))
        F.turned(model,centre,out,along,profile,"door_brass",segments,caps=False)
    return model.triangle_count()-first
