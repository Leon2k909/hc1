"""Reuse approved bench timber members/materials for the south garden pergola."""
import numpy as np
import map_kit as K
import riverdale_parts as P
import veridant_bench as B
def legacy_into(m,c=(0,0)):
    e,n=c
    for x in (-100,100):
        for y in (-60,60):P.box(m,e+x-4,e+x+4,n+y-4,n+y+4,0,110,'vr_timber_dark')
    for y in (-60,60):P.box(m,e-110,e+110,n+y-4,n+y+4,110,118,'vr_timber_dark')
    for x in np.arange(-108,110,16):P.box(m,e+x-1.5,e+x+1.5,n-70,n+70,118,122,'vr_timber_dark')
def build_into(m,c=(0,0)):
    X,Y,Z=B.X,B.Y,B.Z
    def member(centre,size,axes,index):
        local=K.Model();B.rounded_member(local,(0,0,0),size,.15,'vr_bench_teak',index*.73,True,wood_region=index%4)
        axes=np.array(axes);centre=np.array(centre)+np.array((*c,0))
        for paint,faces in local.polygons.items():
            for j,(pts,no) in enumerate(faces):
                ns=local.polygon_normals.get((paint,j))
                m.polygon(paint,[centre+p@axes for p in pts],normal=no@axes,normals=[n@axes for n in ns] if ns else None,uv=local.polygon_uvs.get((paint,j)))
    for x in (-100,100):
        for y in (-60,60):member((x,y,55),(110,8,8),(Z,Y,-X),0)
    for j,y in enumerate((-60,60)):member((0,y,114),(220,8,8),(X,Y,Z),j+1)
    for j,x in enumerate(np.arange(-108,110,16)):member((x,0,120),(140,3,4),(Y,-X,Z),j)
    m.material_overrides.update(B.MATERIALS);m.tile_overrides.update({k:16 for k in B.MATERIALS})
