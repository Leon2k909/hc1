"""Two tower discharge elbows, using existing smooth sweeps and turned hardware."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P
MATERIALS={'ww_outlet_shell':'materials/sewage/pipe-texture-v1/pipe.vmat',
 'ww_outlet_metal':'materials/sewage/crane-blocks-v1/steel.vmat',
 'ww_outlet_inner':'materials/sewage/crane-blocks-v1/dark.vmat'}
PLACEMENTS=(-48,408)

def points(e,steps=32):
    return [(e,490,660),(e,320,660)]+[(e,320-52*math.sin(t),608+52*math.cos(t)) for t in np.linspace(0,math.pi/2,steps+1)[1:]]+[(e,268,580)]

def original(m,e):
    import sewage_map as R
    R.pipe(m,points(e,8),34,open_end=True)
    return m

def ring(m,c,axis,inner,outer,lo,hi,paint,bevel=.5):
    profile=[(inner,lo),(outer-bevel,lo),(outer,lo+bevel),(outer,hi-bevel),(outer-bevel,hi),(inner,hi),(inner,lo)]
    P.lathe_axis(m,c,axis,profile,paint,48)

def emit(m,e):
    m.material_overrides.update(MATERIALS);m.tile_overrides.update({p:64 for p in MATERIALS})
    path=points(e)
    P._sweep(m,path,34,'ww_outlet_shell',48,caps=False)
    interior=K.Model();P._sweep(interior,path,29.6,'ww_outlet_inner',48,caps=False)
    for paint,faces in interior.polygons.items():
        for i,(pts,n) in enumerate(faces):
            ns=interior.polygon_normals.get((paint,i))
            m.polygon(paint,list(reversed(pts)),normal=-n,normals=[-x for x in reversed(ns)] if ns is not None else None)
    # Rolled annular mouth shows real wall thickness without an end cap.
    ring(m,(e,268,580),(0,0,1),29.6,36.4,0,5,'ww_outlet_metal',.7)
    ring(m,(e,268,580),(0,0,1),33.9,35.3,7,10,'ww_outlet_shell',.4)
    # Paired bolted joint on the straight inlet, with a visible gasket seam.
    c=np.array((e,380,660),float);axis=np.array((0,1,0),float)
    for lo,hi in ((-7,-.8),(.8,7)):
        ring(m,c,axis,33.9,44.5,lo,hi,'ww_outlet_metal',.8)
    ring(m,c,axis,34,42.5,-.8,.8,'ww_outlet_inner',.15)
    for angle in np.linspace(0,math.tau,12,endpoint=False):
        q=c+np.array((39.4*math.cos(angle),0,39.4*math.sin(angle)))
        P.rod(m,q-axis*10,q+axis*10,1.0,'ww_outlet_metal',12,True)
        for sign in (-1,1):
            p=q+axis*sign*7.1
            P.rod(m,p,p+axis*sign*.5,2.3,'ww_outlet_inner',16,True)
            P.rod(m,p+axis*sign*.5,p+axis*sign*2.4,1.7,'ww_outlet_metal',6,True)
    # Cast transition collars join the elbow to its straight legs.
    ring(m,(e,320,660),(0,1,0),33.9,35.6,0,4,'ww_outlet_shell',.5)
    return m
