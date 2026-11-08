"""Reuse the approved reception housing at kiosk-fixture scale and orientation."""
import numpy as np
import map_kit as K
import veridant_reception_light as R
def build_into(m,c=(0,0),z0=0):
    source=K.Model();R.build_into(source)
    turn=np.array([[0,-1,0],[1,0,0],[0,0,1.]])
    origin=np.array((170,200,108));dest=np.array((*c,z0))
    for paint,faces in source.polygons.items():
        for points,normal in faces:
            m.polygon(paint,[dest+turn@(p-origin)*.8 for p in points],normal=turn@normal)
