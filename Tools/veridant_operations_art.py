"""High-resolution sea painting in the existing west-gallery frame."""
import numpy as np
import map_kit as K
import veridant_parts as P
def build_into(m,c=(0,0),z0=0):
    source=K.Model();P.art(source,'art_4',(*c,z0),(0,1,0),44)
    for paint,faces in source.polygons.items():
        if paint!='vr_print':
            for pts,no in faces:m.polygon(paint,pts,normal=no)
    e,n=c
    pts=[np.array((e+1.02,n+y,z0+z)) for y,z in [(-22,-22),(22,-22),(22,22),(-22,22)]]
    m.polygon('vr_gallery_art',pts,normal=np.array((1,0,0)),uv=[(0,0),(1,0),(1,1),(0,1)])
    m.material_overrides['vr_gallery_art']='materials/veridant/operations-art-v1/still-life.vmat'
    m.tile_overrides['vr_gallery_art']=64
