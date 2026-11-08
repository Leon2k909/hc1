"""Cafe pergola timber, reusing the approved garden/bench teak members."""
import numpy as np
import map_kit as K
import riverdale_parts as P
import veridant_bench as B

def legacy_into(m,c=(0,0),top=0):
    e,n=c
    for y in (-44.5,44.5):P.box(m,e-88,e+88,n+y-4,n+y+4,top-11,top-2,'vr_timber_dark')
    for x in np.arange(-78,80,14):P.box(m,e+x-2.2,e+x+2.2,n-50.5,n+50.5,top-2,top+4,'vr_timber_dark')

def build_into(m,c=(0,0),top=0):
    X,Y,Z=B.X,B.Y,B.Z
    def member(centre,size,axes,index):
        local=K.Model();B.rounded_member(local,(0,0,0),size,.15,'vr_bench_teak',index*.73,True,wood_region=index%4)
        axes=np.array(axes);centre=np.array(centre)+np.array((*c,top))
        for paint,faces in local.polygons.items():
            for j,(pts,no) in enumerate(faces):
                ns=local.polygon_normals.get((paint,j))
                m.polygon(paint,[centre+p@axes for p in pts],normal=no@axes,normals=[n@axes for n in ns] if ns else None,uv=local.polygon_uvs.get((paint,j)))
    for j,y in enumerate((-44.5,44.5)):member((0,y,-6.5),(176,8,9),(X,Y,Z),j+1)
    for j,x in enumerate(np.arange(-78,80,14)):member((x,0,1),(101,4.4,6),(Y,-X,Z),j)
    m.material_overrides.update(B.MATERIALS);m.tile_overrides.update({k:16 for k in B.MATERIALS})
