"""Continuous cloth UVs and matte woven canvas on the existing draped mesh."""
import map_kit as K
import veridant_parts as P
MATERIAL='materials/veridant/terrace-tarp-v1/canvas.vmat'
def build_into(m,c=(0,0),z0=0):
    source=K.Model();P.tarp_over(source,(c[0],c[1]),(c[0],c[1]+94),z0+42,(-1,0),drop_out=30,drop_in=27,seed=2,rail=1.5)
    faces=source.polygons['vr_tarp'];cols=42;rows=14
    for index,(points,normal) in enumerate(faces):
        cell=index//2;i,k=divmod(cell,rows)
        uv=[(i*94/cols/12,k*60/rows/12),((i+1)*94/cols/12,k*60/rows/12),((i+1)*94/cols/12,(k+1)*60/rows/12),(i*94/cols/12,(k+1)*60/rows/12)]
        if index%2:uv=uv[:1]+uv[:0:-1]
        ns=source.polygon_normals.get(('vr_tarp',index))
        m.polygon('vr_tarp',points,normal=normal,normals=ns,uv=uv)
    m.material_overrides['vr_tarp']=MATERIAL
    m.tile_overrides['vr_tarp']=12.
