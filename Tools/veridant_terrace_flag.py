"""Static breeze-shaped cloth for the terrace flag, retaining its atlas artwork."""
import math
import numpy as np
import veridant_materials as VM
def build_into(m,c=(0,0),z0=0):
    us=np.linspace(0,1,49);vs=np.linspace(0,1,25)
    grid=np.array([[np.array((c[0]-(math.sin(u*math.tau*1.4-v*.8)*5.5+math.sin(u*math.tau*3+v)*1.2)*u,c[1]+2+66*u,z0+196-44+44*v-5*u*u+(1-v)*math.sin(u*math.tau*1.2)*u)) for v in vs] for u in us])
    normals=np.cross(np.gradient(grid,axis=0),np.gradient(grid,axis=1));normals/=np.maximum(np.linalg.norm(normals,axis=2,keepdims=True),1e-9)
    for i in range(len(us)-1):
        for j in range(len(vs)-1):
            ij=[(i,j),(i+1,j),(i+1,j+1),(i,j+1)]
            pts=[grid[a,b] for a,b in ij];ns=[normals[a,b] for a,b in ij]
            uv=[VM.atlas_uv(VM.PRINTS,VM.PRINT_ATLAS,'flag',us[a],vs[b]) for a,b in ij]
            m.polygon('vr_print',pts,normal=sum(ns),normals=ns,uv=uv,both_sides=True)
