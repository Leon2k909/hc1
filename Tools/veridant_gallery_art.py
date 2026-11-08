"""High-resolution coastal painting in the original gallery frame."""
import numpy as np
import map_kit as K
import veridant_parts as P
def build_into(m,c=(0,0),z0=0):
    source=K.Model();P.art(source,'art_1',(*c,z0),(-1,0,0),52)
    for paint,faces in source.polygons.items():
        if paint!='vr_print':
            for pts,no in faces:m.polygon(paint,pts,normal=no)
    e,n=c
    pts=[np.array((e+x,n+1.02,z0+z)) for x,z in [(19.5,-26),(-19.5,-26),(-19.5,26),(19.5,26)]]
    m.polygon('vr_gallery_art',pts,normal=np.array((0,1,0)),uv=[(0,0),(1,0),(1,1),(0,1)])
    m.material_overrides['vr_gallery_art']='materials/veridant/gallery-art-v1/coastal.vmat'
    m.tile_overrides['vr_gallery_art']=64
