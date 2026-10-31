"""Steel rear closures inside the four existing solid stair wedges.

This is render-only cladding. It closes missing rear faces without adding a
collider or extending into the circulation route behind the stair landing.
"""
import numpy as np
import riverdale_parts as P


def append_rear_closure(model,axis,c0,c1,s0,s1,z0,z1,landing_thickness=16.):
    sign=1. if s1>s0 else -1.;top=z1-landing_thickness
    assert c1>c0 and top>z0+24
    def point(c,depth,z):return np.array((c,s1-sign*depth,z) if axis=='n' else (s1-sign*depth,c,z),float)
    across=np.array((1,0,0) if axis=='n' else (0,1,0),float)
    along=np.array((0,1,0) if axis=='n' else (1,0,0),float)
    up=np.array((0,0,1),float)
    axes=(across,along,up)
    def panel(ca,cb,za,zb,front,back,paint,bevel=.12):
        # An end on c0 or c1 lies exactly on the stair's own wall and z-fights it, so that face is left out.
        skip=(('-x',) if ca<=c0 else ())+(('+x',) if cb>=c1 else ())
        P.bevel_box(model,point((ca+cb)/2,(front+back)/2,(za+zb)/2),axes,
                    (cb-ca,back-front,zb-za),paint,bevel=bevel,skip=skip)
    panel(c0,c1,z0-.35,top,.70,4.2,'ar_gunmetal',.16)
    # Two columns of replaceable steel sheets with shallow, recessed joints.
    middle=(c0+c1)/2
    for ca,cb in ((c0+3,middle-.55),(middle+.55,c1-3)):
        for row in range(3):
            # The bottom row starts above the floor kick, or the two overlap a quarter inch apart.
            za=z0+4.3 if row==0 else z0+3+(top-z0-6)*row/3
            zb=z0+3+(top-z0-6)*(row+1)/3
            panel(ca,cb,za+.35,zb-.35,.25,2.8,'ar_steel',.16)
    # Flush edge angles and a floor kick close the raw ends of the stringers.
    for ca,cb in ((c0,c0+2.6),(c1-2.6,c1)):
        panel(ca,cb,z0-.35,top,.025,1.3,'ar_gunmetal',.10)
    panel(c0,c1,z0-.35,z0+4.5,.025,1.3,'ar_gunmetal',.10)
    panel(c0,c1,top-2.4,top,.025,1.3,'ar_gunmetal',.10)
    return dict(axis=axis,c0=c0,c1=c1,s0=s0,s1=s1,z0=z0,top=top,depth=4.2,
                collision_added=False,inside_existing_solid=True)
